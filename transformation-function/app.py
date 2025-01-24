import boto3
import base64
import json
import gzip
import os
import logging
import uuid
import pandas as pd
import awswrangler as wr
from io import BytesIO
from datetime import datetime

SEC_LAKE_BUCKET = os.environ['SEC_LAKE_BUCKET']

# configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if os.environ['DEBUG'].lower() == 'true':
    logger.setLevel(logging.DEBUG)

logger.info('Loading function')

# get config for mapping
mapping_config = open('OCSFmapping.json')
custom_source_mapping = json.load(mapping_config)
# check if multiple schema matches in mapping
schemas = []
for k in custom_source_mapping['custom_source_events']['ocsf_mapping'].keys():
    schemas.append(custom_source_mapping['custom_source_events']['ocsf_mapping'][k]['schema'])

MULTISCHEMA = True if (len(set(schemas)) > 1) else False

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
        return str(result)
    else:
        logger.info("Unable to process matched field -"+dot_locator)

# function to map original log record to mapping defined in config file
def perform_transform(event_mapping, event):
    new_record = {}
    for key in event_mapping.keys():
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
                # otherwise just map it
                new_record[key] = event_mapping[key]
                
    return new_record

# function to process data coming from cloudwatch (using subscription filters)
def process_cloudwatch_events(cwevent):
    logger.info('Processing Cloudwatch event')
    mapped_events = []
    unmapped_events = []
    payload_json = {}
    for event in cwevent["logEvents"]:
        logger.debug("Raw log: "+str(event["message"]))
        payload_json = json.loads(event["message"])

        # save timestamp information
        partition = {}
        partition['timestamp'] = get_dot_locator_value(custom_source_mapping['custom_source_events']['timestamp']['field'], payload_json)
        partition['format'] = custom_source_mapping['custom_source_events']['timestamp']['format']
        partition['eventday'] = timestamp_transform(partition['timestamp'], partition['format'])
        
        logger.debug("Eventday: "+str(partition['eventday']))
        matched_value = get_dot_locator_value(custom_source_mapping['custom_source_events']['matched_field'], payload_json)

        logger.debug("Matched value: "+str(matched_value))

        if matched_value in custom_source_mapping['custom_source_events']['ocsf_mapping']:
            new_map = perform_transform(custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema_mapping'], payload_json)
            new_schema = {}
            new_schema['target_schema'] = custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema']
            new_schema['target_mapping'] = new_map
            new_schema['eventday'] = partition['eventday']

            logger.debug("Transformed OCSF record: "+str(new_schema))

            mapped_events.append(new_schema)

        else:
            logger.info("Found unmapped event: " + matched_value)
            unmapped_events.append(payload_json)

    return mapped_events, unmapped_events

# function to process event if received from S3
def process_s3_event(record):

    logger.info('Processing S3 event')
    mapped_events = []
    unmapped_events = []
    payload_json = {}

    message = json.loads(record['body'])
    s3_details = message['Records'][0]['s3']

    bucket_name = s3_details['bucket']['name']
    object_key = s3_details['object']['key']

    s3_client = boto3.client('s3')

    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=object_key
    )

    log_file=gzip.GzipFile(
        None,
        'rb',
        fileobj=BytesIO(response['Body'].read()))

    for line in log_file:
        
        logger.debug("Raw log: "+str(line.decode("utf-8")))
        payload_json = json.loads(line.decode("utf-8"))
        
        # save timestamp information
        partition = {}
        partition['timestamp'] = get_dot_locator_value(custom_source_mapping['custom_source_events']['timestamp']['field'], payload_json)
        partition['format'] = custom_source_mapping['custom_source_events']['timestamp']['format']
        partition['eventday'] = timestamp_transform(partition['timestamp'], partition['format'])
        
        logger.debug("Eventday: "+str(partition['eventday']))
        
        matched_value = get_dot_locator_value(custom_source_mapping['custom_source_events']['matched_field'], payload_json)

        logger.debug("Matched value: "+str(matched_value))

        if matched_value in custom_source_mapping['custom_source_events']['ocsf_mapping']:
            logger.debug("Found event mapping: "+str(custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]))
            new_map = perform_transform(custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema_mapping'], payload_json)
            new_schema = {}
            new_schema['target_schema'] = custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema']
            new_schema['target_mapping'] = new_map
            new_schema['eventday'] = partition['eventday']

            logger.debug("Transformed OCSF record: "+str(new_schema))

            mapped_events.append(new_schema)

        else:
            logger.info("Found unmapped event: "+matched_value)
            unmapped_events.append(payload_json)

    return mapped_events, unmapped_events

# function to process event if received from Kinesis
def process_kinesis_event(record):

    logger.info('Processing Kinesis event')

    mapped_events = []
    unmapped_events = []
    payload_json = {}

    payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
    logger.debug("Raw log: "+str(payload))
    payload_json = json.loads(payload)

    matched_value = get_dot_locator_value(custom_source_mapping['custom_source_events']['matched_field'], payload_json)
    logger.debug("Matched value: "+str(matched_value))

    # if its a windows-sysmon event then we need to tweak it to get it into json format
    if custom_source_mapping['custom_source_events']['source_name'] == 'windows-sysmon':
        data = {}
        for line in payload_json['Description'].split('\r\n'):
            parts = line.split(': ', 1)  # Splitting by ': '
            key = parts[0]
            # If value is present, assign it to the key, otherwise assign an empty string
            value = parts[1] if len(parts) > 1 else ""
            data[key] = value
        payload_json['Description'] = data

    logger.debug(payload_json)
    
    # save timestamp information
    partition = {}
    partition['timestamp'] = get_dot_locator_value(custom_source_mapping['custom_source_events']['timestamp']['field'], payload_json)
    partition['format'] = custom_source_mapping['custom_source_events']['timestamp']['format']
    partition['eventday'] = timestamp_transform(partition['timestamp'], partition['format'])
        
    logger.debug("Eventday: "+str(partition['eventday']))

    if matched_value in custom_source_mapping['custom_source_events']['ocsf_mapping']:
        logger.debug("Found event mapping: "+str(custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]))
        new_map = perform_transform(custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema_mapping'], payload_json)
        new_schema = {}
        new_schema['target_schema'] = custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema']
        new_schema['target_mapping'] = new_map
        new_schema['eventday'] = partition['eventday']

        logger.debug("Transformed OCSF record: "+str(new_schema))

        mapped_events.append(new_schema)

    else:
        logger.info("Found unmapped event: "+matched_value)
        unmapped_events.append(payload_json)

    return mapped_events, unmapped_events

def lambda_handler(event, context):
    
    aws_account_id = context.invoked_function_arn.split(":")[4]
    aws_region = context.invoked_function_arn.split(":")[3]

    mapped_events = []
    unmapped_events = []

    if "Records" in event:
        for record in event['Records']:
            logger.info('Record eventSource: '+record['eventSource'])
            if record['eventSource'] == 'aws:kinesis':
                logger.info('Record eventID: '+record['eventID'])
                mapped, unmapped = process_kinesis_event(record)
                logger.debug(mapped)
                logger.debug(unmapped)
                mapped_events.extend(mapped)
                unmapped_events.extend(unmapped)
            elif record['eventSource'] == 'aws:sqs':
                logger.info('Record messageId: '+record['messageId'])
                mapped, unmapped = process_s3_event(record)
                logger.debug(mapped)
                logger.debug(unmapped)
                mapped_events.extend(mapped)
                unmapped_events.extend(unmapped)
            else:
                logger.info("Event source not supported.")
    elif "logEvents" in event:
        '''ADDING Cloudwatch capabilities'''
        logger.info('Cloudwatch logGroup' + event['logGroup'] + ' logStream'+event['logStream'])
        mapped, unmapped = process_cloudwatch_events(event)
        logger.debug(mapped)
        logger.debug(unmapped)
        mapped_events.extend(mapped)   
        unmapped_events.extend(unmapped)         

    if mapped_events:
        df = pd.DataFrame(mapped_events)
        # we may have records that cut across partitions
        df_eventdays = df['eventday'].unique()
        # so for each eventday, get the schemas for that day only and write them to the partition
        for eventday in df_eventdays:
            df_filtered = (df[df['eventday']==eventday])
            df_schemas = df_filtered['target_schema'].unique()
        
            for ocsf_schema in df_schemas:
                df_map = (df[df['target_schema']==ocsf_schema])
                df_map = pd.json_normalize(df_map['target_mapping'], max_level=0)
                if MULTISCHEMA:
                    s3_url = f's3://{SEC_LAKE_BUCKET}/{ocsf_schema.upper()}/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
                else:
                    s3_url = f's3://{SEC_LAKE_BUCKET}/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
                
                logger.info("Writing transformed events to: "+s3_url)
                wr.s3.to_parquet(
                    df=df_map,
                    path=s3_url,
                    compression='gzip'
                )
                logger.info("Successfully wrote to: "+s3_url)

    if unmapped_events:
        
        logger.info('Dropping {} unmapped records.'.format(len(unmapped_events)))

    logger.info('Successfully processed {} records.'.format(len(mapped_events)))

    return