import base64
import json
import os
import logging
import uuid
import datetime
import pandas as pd
import awswrangler as wr

# Consider overrides for account_id and region
SEC_LAKE_BUCKET = os.environ['SEC_LAKE_BUCKET']

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if os.environ['DEBUG'].lower() == 'true':
    logger.setLevel(logging.DEBUG)

logger.info('Loading function')
payload_json = {}

# Get config for mapping
f = open('sysmon_mapping.json')
custom_source_mapping = json.load(f)

def get_dot_locator_value(dot_locator, event):
    # todo: validate locator
    if dot_locator.startswith('$.'):
        json_path = dot_locator.split('.')
        if json_path[1] == 'UserDefined':
            return event[json_path[2]]
        json_path.pop(0)
        result = {}
        result = event
        # iterater through nested values in the payload until we get the final value
        for k in json_path:
            result = result.get(k)
        return str(result)
    else:
        logger.info("Unable to process matched field -"+dot_locator)

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
            # if its a string and we find a dot locator, get the field
            if isinstance(event_mapping[key], str) and (event_mapping[key].startswith('$.')):
                new_record[key] = get_dot_locator_value(event_mapping[key], event)
            else:
                # otherwise just map it
                new_record[key] = event_mapping[key]
           
    return new_record
            
def lambda_handler(event, context):
    # get the account id and region of this lambda
    aws_account_id = context.invoked_function_arn.split(":")[4]
    aws_region = context.invoked_function_arn.split(":")[3]
    
    dt_now = datetime.datetime.now()
    eventday = str(dt_now.year)+f'{dt_now.month:02d}'+f'{dt_now.day:02d}'
    
    output_for_df = []
    unmapped_events =[]
    
    for record in event['Records']:
        logger.info('Kinesis Data Streams event: '+record['eventID'])
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')

        logger.debug("Raw Sysmon event: "+str(payload))

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

        if matched_value in custom_source_mapping['custom_source_events']['ocsf_mapping']:
            logger.debug("Found event mapping: "+str(custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]))
            new_map = perform_transform(custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema_mapping'], payload_json)
            new_schema = {}
            new_schema['target_schema'] = custom_source_mapping['custom_source_events']['ocsf_mapping'][matched_value]['schema']
            new_schema['target_mapping'] = new_map

            logger.debug("Transformed OCSF record: "+str(new_schema))

            output_for_df.append(new_schema)

        else:
            logger.info("Found unmapped event")
            unmapped_events.append(payload_json)
    
    if output_for_df:
        
        df = pd.DataFrame(output_for_df)
        df_schemas = df['target_schema'].unique()
    
        for ocsf_schema in df_schemas:
            df_map = (df[df['target_schema']==ocsf_schema])
            df_map = pd.json_normalize(df_map['target_mapping'], max_level=0)
            s3_url = f's3://{SEC_LAKE_BUCKET}/1.0/{ocsf_schema.upper()}/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
            logger.info("Writing transformed events to: "+s3_url)
            wr.s3.to_parquet(
                df=df_map,
                path=s3_url,
                compression='gzip'
            )
            logger.info("Successfully wrote to: "+s3_url)

    if unmapped_events:

        unmapped_events_df = pd.DataFrame(unmapped_events)

        s3_url = f's3://{SEC_LAKE_BUCKET}/UNMAPPED_EVENTS/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
        logger.info("Writing unmapped events to: "+s3_url)
        wr.s3.to_parquet(
            df=unmapped_events_df,
            path=s3_url,
            compression='gzip'
            )
        logger.info("Successfully wrote unmapped events to: "+s3_url)

    logger.info('Successfully processed {} records.'.format(len(event['Records'])))

    return