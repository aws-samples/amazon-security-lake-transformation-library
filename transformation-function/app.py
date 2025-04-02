import boto3
import base64
import json
import gzip
import os
import logging
import uuid
import importlib
import pandas as pd
import awswrangler as wr
from io import BytesIO
from datetime import datetime

SEC_LAKE_BUCKET = os.environ['SEC_LAKE_BUCKET']

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if os.environ.get('DEBUG', 'false').lower() == 'true':
    logger.setLevel(logging.DEBUG)

logger.info('Loading function')

# Load source configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
sources_config_path = os.path.join(current_dir, 'sources_config.json')

with open(sources_config_path) as f:
    sources_config = json.load(f)
    logger.info(f"Loaded source configuration with {len(sources_config['sources'])} sources")

# Load mapping configurations
source_mappings = {}
for source in sources_config['sources']:
    mapping_path = os.path.join(current_dir, 'mappings', source['mapping_file'])
    if os.path.exists(mapping_path):
        with open(mapping_path) as f:
            source_mappings[source['name']] = json.load(f)
            logger.info(f"Loaded mapping for source: {source['name']}")
    else:
        logger.warning(f"Mapping file not found for source: {source['name']}")

# Check which sources have multiple schemas
MULTISCHEMA_SOURCES = {}
for source_name, mapping in source_mappings.items():
    schemas = []
    for k in mapping['custom_source_events']['ocsf_mapping'].keys():
        schemas.append(mapping['custom_source_events']['ocsf_mapping'][k]['schema'])
    MULTISCHEMA_SOURCES[source_name] = len(set(schemas)) > 1

# Load all preprocessors at initialization time
preprocessors = {}
for source in sources_config['sources']:
    try:
        module_name = source['preprocessor_module']
        # Import the specific module mentioned in the config
        module = importlib.import_module(f'preprocessors.{module_name}')
        
        if hasattr(module, 'preprocess_event'):
            preprocessors[source['name']] = module.preprocess_event
            logger.info(f"Loaded preprocessor for source: {source['name']}")
        else:
            logger.warning(f"Preprocessor module {module_name} does not have preprocess_event function")
    except ImportError as e:
        logger.warning(f"Could not import preprocessor for {source['name']}: {e}")

# function to return eventday format from user-specified timestamp found in logs
def timestamp_transform(timestamp, format):
    if format == 'epoch':
        dt_event = datetime.fromtimestamp(int(timestamp))
        eventday = str(dt_event.year)+f'{dt_event.month:02d}'+f'{dt_event.day:02d}'
        return eventday
    else:
        dt_event = datetime.strptime(timestamp, format)
        eventday = str(dt_event.year)+f'{dt_event.month:02d}'+f'{dt_event.day:02d}'
        return eventday

# function to return value from '$.' reference in config line
def get_dot_locator_value(dot_locator, event):
    if dot_locator.startswith('$.'):
        json_path = dot_locator.split('.')
        if json_path[1] == 'UserDefined':
            return event[json_path[2]]
        json_path.pop(0)
        result = {}
        result = event
        for k in json_path:
            if result.get(k) is not None:
                result = result.get(k)
            else: # if we get None then reference doesnt exist and we need to break out
                result = None
                break
        return str(result) if result is not None else None
    else:
        logger.info("Unable to process matched field -"+dot_locator)
        return None

# function to map original log record to mapping defined in config file
def perform_transform(event_mapping, event):
    new_record = {}
    for key in event_mapping.keys():
        try:
            # if we have a dict as the value we need to keep traversing until we reach a leaf
            if type(event_mapping[key]) is dict:
                if 'enum' in event_mapping[key]:
                    if isinstance(event_mapping[key]['enum']['evaluate'], str) and (event_mapping[key]['enum']['evaluate'].startswith('$.')):
                        value = get_dot_locator_value(event_mapping[key]['enum']['evaluate'], event)
                        if value in event_mapping[key]['enum']['values']:
                            new_record[key] = event_mapping[key]['enum']['values'][value]
                        else:
                            new_record[key] = event_mapping[key]['enum']['other']
                else:
                    new_record[key] = perform_transform(event_mapping[key], event)
            else: # we have reached a leaf node
                # get the field if dot locator
                if isinstance(event_mapping[key], str) and (event_mapping[key].startswith('$.')):
                    locator_value = get_dot_locator_value(event_mapping[key], event)
                    if locator_value is not None:
                        new_record[key] = locator_value
                    else:
                        # Field not found but continue processing
                        logger.warning(f"Field {event_mapping[key]} not found in event, setting to null")
                        new_record[key] = None
                else:
                    # otherwise just map it
                    new_record[key] = event_mapping[key]
        except Exception as e:
            # Catch any errors during transformation of this field and continue
            logger.warning(f"Error transforming field {key}: {str(e)}, setting to null")
            new_record[key] = None
                
    return new_record

# Detect source from Kinesis event
def detect_source_from_kinesis(payload_json):
    """
    Detect the source of a Kinesis event based on configuration
    Returns None if source cannot be determined
    """
    for source in sources_config['sources']:
        kinesis_config = source['input_paths'].get('kinesis', {})
        
        if kinesis_config.get('enabled', False):
            metadata_field = kinesis_config.get('metadata_field', 'source')
            
            # Check if the metadata field exists and matches the source name
            if metadata_field in payload_json and payload_json[metadata_field] == source['name']:
                logger.debug(f"Detected source from Kinesis metadata: {source['name']}")
                return source['name']
            
            # Check nested metadata
            if 'metadata' in payload_json and metadata_field in payload_json['metadata']:
                if payload_json['metadata'][metadata_field] == source['name']:
                    logger.debug(f"Detected source from Kinesis nested metadata: {source['name']}")
                    return source['name']
    
    # If no source detected, return None
    logger.warning("No source detected for Kinesis event")
    return None

# Detect source from S3 object key
def detect_source_from_s3_key(bucket_name, object_key):
    """
    Detect the source based on S3 object key prefix or bucket/prefix combination
    Returns None if source cannot be determined
    """
    for source in sources_config['sources']:
        s3_config = source['input_paths'].get('s3', {})
        
        if s3_config.get('enabled', False):
            # Check if the object key starts with any of the configured prefixes
            path_prefixes = s3_config.get('path_prefixes', [])
            for prefix in path_prefixes:
                if object_key.startswith(prefix):
                    logger.debug(f"Detected source from S3 key prefix: {source['name']}")
                    return source['name']
            
            # Check if it matches any source bucket configuration
            source_buckets = s3_config.get('source_buckets', [])
            for source_bucket in source_buckets:
                if source_bucket.get('bucket_name') == bucket_name:
                    bucket_prefix = source_bucket.get('prefix', '')
                    # Empty prefix means match any object in this bucket
                    if not bucket_prefix or object_key.startswith(bucket_prefix):
                        logger.debug(f"Detected source from bucket/prefix match: {source['name']}")
                        return source['name']
    
    # If no source detected, return None
    logger.warning(f"No source detected for bucket: {bucket_name}, key: {object_key}")
    return None

# Process a single event
def process_event(processed_json, source_name):
    """
    Process an event for a specific source
    """ 
    # Check if we have a mapping for this source
    if source_name not in source_mappings:
        logger.warning(f"No mapping configuration found for source: {source_name}")
        return None, processed_json
        
    mapping = source_mappings[source_name]
    
    # Extract timestamp
    timestamp_field = mapping['custom_source_events']['timestamp']['field']
    timestamp_format = mapping['custom_source_events']['timestamp']['format']
    
    timestamp = get_dot_locator_value(timestamp_field, processed_json)
    if not timestamp:
        logger.warning(f"Could not extract timestamp from field {timestamp_field}")
        return None, processed_json
    
    eventday = timestamp_transform(timestamp, timestamp_format)
    logger.debug(f"Eventday: {eventday}")
    # Extract matched field for event type
    matched_field = mapping['custom_source_events']['matched_field']
    matched_value = get_dot_locator_value(matched_field, processed_json)
    
    if not matched_value:
        logger.warning(f"Could not extract matched value from field {matched_field}")
        return None, processed_json
    
    # Check if we have a mapping for this event type
    if matched_value in mapping['custom_source_events']['ocsf_mapping']:
        event_mapping = mapping['custom_source_events']['ocsf_mapping'][matched_value]
        transformed_data = perform_transform(event_mapping['schema_mapping'], processed_json)
        
        result = {
            'source': source_name,
            'target_schema': event_mapping['schema'],
            'target_mapping': transformed_data,
            'eventday': eventday
        }

        logger.debug("Transformed OCSF record: "+str(result))
        
        return result, None
    else:
        logger.info(f"No mapping found for {source_name} event with matched value: {matched_value}")
        return None, processed_json

# Process a single event
def process_s3_event(record):
    logger.info('Processing S3 event')
    mapped_events = []
    unmapped_events = []

    message = json.loads(record['body'])
    s3_details = message['Records'][0]['s3']

    bucket_name = s3_details['bucket']['name']
    object_key = s3_details['object']['key']
    
    # Detect source from S3 bucket and key
    source_name = detect_source_from_s3_key(bucket_name, object_key)
    if source_name is None:
        logger.error(f"Cannot determine source for S3 object: {bucket_name}/{object_key}")
        return [], []
        
    logger.info(f"Processing S3 object from source: {source_name}, key: {object_key}")

    s3_client = boto3.client('s3')
    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=object_key
    )

    log_file = gzip.GzipFile(
        None,
        'rb',
        fileobj=BytesIO(response['Body'].read())
    )

    for line in log_file:
        raw_line = line.decode("utf-8")
        logger.debug("Raw log: " + raw_line)

        try:
            # Process the raw line
            if source_name in preprocessors:
                processed_json = preprocessors[source_name](raw_line)
            else:
                # If no preprocessor, try to parse as JSON, fallback to raw text
                try:
                    processed_json = json.loads(raw_line)
                except json.JSONDecodeError:
                    processed_json = {"rawData": raw_line}
            
            # Process the event
            mapped_event, unmapped_event = process_event(processed_json, source_name)
            
            if mapped_event:
                mapped_events.append(mapped_event)
            elif unmapped_event:
                unmapped_events.append(unmapped_event)
                
        except Exception as e:
            logger.error(f"Error processing line: {str(e)}")
            unmapped_events.append({"raw": raw_line, "error": str(e)})

    return mapped_events, unmapped_events

# function to process event if received from Kinesis
def process_kinesis_event(record):
    logger.info('Processing Kinesis event')
    mapped_events = []
    unmapped_events = []

    try:
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        logger.debug("Raw log: " + str(payload))
        
        try:
            payload_json = json.loads(payload)
            
            # Detect source from Kinesis event
            source_name = detect_source_from_kinesis(payload_json)
            if source_name is None:
                logger.error("Cannot determine source for Kinesis event, skipping processing")
                unmapped_events.append({"raw": payload, "error": "Source could not be determined"})
                return mapped_events, unmapped_events
                
            logger.info(f"Processing Kinesis event from source: {source_name}")
            
            # Extract the actual log data from the message field
            log_data = payload_json.get('message', payload_json)
            
            # Process the log data
            if source_name in preprocessors:
                processed_json = preprocessors[source_name](log_data)
            else:
                processed_json = log_data
            
            # Process the event
            mapped_event, unmapped_event = process_event(processed_json, source_name)
            
            if mapped_event:
                mapped_events.append(mapped_event)
            elif unmapped_event:
                unmapped_events.append(unmapped_event)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
            unmapped_events.append({"raw": payload, "error": "JSON decode error"})
    except Exception as outer_e:
        logger.error(f"Fatal error processing Kinesis record: {str(outer_e)}")
        unmapped_events.append({"error": f"Fatal Kinesis processing error: {str(outer_e)}"})
    
    return mapped_events, unmapped_events

def lambda_handler(event, context):
    aws_account_id = context.invoked_function_arn.split(":")[4]
    aws_region = context.invoked_function_arn.split(":")[3]

    mapped_events = []
    unmapped_events = []

    for record in event['Records']:
        logger.info('Record eventSource: '+record['eventSource'])
        if record['eventSource'] == 'aws:kinesis':
            logger.info('Record eventID: '+record['eventID'])
            mapped, unmapped = process_kinesis_event(record)
            mapped_events.extend(mapped)
            unmapped_events.extend(unmapped)
        elif record['eventSource'] == 'aws:sqs':
            logger.info('Record messageId: '+record['messageId'])
            mapped, unmapped = process_s3_event(record)
            mapped_events.extend(mapped)
            unmapped_events.extend(unmapped)
        else:
            logger.info("Event source not supported.")

    if mapped_events:
        df = pd.DataFrame(mapped_events)
        # Group by source, schema, and eventday for proper partitioning
        source_groups = df.groupby(['source', 'target_schema', 'eventday'])
        
        for (source, schema, eventday), group in source_groups:
            # Extract just the target_mapping column
            df_map = pd.json_normalize(group['target_mapping'], max_level=0)
            
            # Create appropriate S3 path based on multi-schema setting
            if MULTISCHEMA_SOURCES.get(source, False):
                s3_url = f's3://{SEC_LAKE_BUCKET}/{source}/{schema.upper()}/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
            else:
                s3_url = f's3://{SEC_LAKE_BUCKET}/{source}/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
            
            logger.info(f"Writing {len(df_map)} transformed events to: {s3_url}")
            wr.s3.to_parquet(
                df=df_map,
                path=s3_url,
                compression='gzip'
            )
            logger.info(f"Successfully wrote to: {s3_url}")

    if unmapped_events:
        logger.info(f'Dropping {len(unmapped_events)} unmapped records.')

    logger.info(f'Successfully processed {len(event["Records"])} records.')

    return