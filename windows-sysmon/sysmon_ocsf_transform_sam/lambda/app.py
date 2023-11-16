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
sysmon_mapping = json.load(f)

def perform_transform(event_mapping, sysmon_event):
    
    new_record = {}
    
    for key in event_mapping.keys():
        # if we have a dict as the value we need to keep traversing until we reach a leaf
        if type(event_mapping[key]) is dict:
            if 'enum' in event_mapping[key]:
                if isinstance(event_mapping[key]['enum']['evaluate'], str) and (event_mapping[key]['enum']['evaluate'].startswith('Event.')):
                    json_path = event_mapping[key]['enum']['evaluate'].split('.')
                    json_path.pop(0)
                    results_dict = {}
                    results_dict = sysmon_event
                    # iterater through nested values in the payload until we get the final value
                    for sysmon_key in json_path:
                        results_dict = results_dict.get(sysmon_key)
                    if results_dict in event_mapping[key]['enum']['values']:
                        new_record[key] = event_mapping[key]['enum']['values'][results_dict]
                    else:
                        new_record[key] = event_mapping[key]['enum']['values']['other']
            else:
                new_record[key] = perform_transform(event_mapping[key], sysmon_event)
        else: # we have reached a leaf node
            # if its a string and its using Event. dot notation
            if isinstance(event_mapping[key], str) and (event_mapping[key].startswith('Event.')):
                json_path = event_mapping[key].split('.')
                json_path.pop(0)
                results_dict = {}
                results_dict = sysmon_event
                # iterater through nested values in the payload until we get the final value
                for sysmon_key in json_path:
                    results_dict = results_dict.get(sysmon_key)
                new_record[key] = str(results_dict)
            # if its a string and its using Metadata. dot notation
            elif isinstance(event_mapping[key], str) and (event_mapping[key].startswith('Metadata.')):
                metadata_attribute = event_mapping[key].split('.')
                metadata_attribute.pop(0)
                new_record[key] = sysmon_event[metadata_attribute[0]]
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
        payload_json['EventId'] = str(payload_json['EventId'])

        data = {}
        for line in payload_json['Description'].split('\r\n'):
            parts = line.split(': ', 1)  # Splitting by ': '
            key = parts[0]
            # If value is present, assign it to the key, otherwise assign an empty string
            value = parts[1] if len(parts) > 1 else ""
            data[key] = value
        
        payload_json['Description'] = data

        if payload_json['EventId'] in sysmon_mapping['sysmon_events']:
            logger.debug("Found event mapping: "+str(sysmon_mapping['sysmon_events'][payload_json['EventId']]))
            new_map = perform_transform(sysmon_mapping['sysmon_events'][payload_json['EventId']]['mapping'], payload_json)
            new_schema = {}
            new_schema['target_schema'] = sysmon_mapping['sysmon_events'][payload_json['EventId']]['schema']
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
            s3_url = f's3://{SEC_LAKE_BUCKET}1.0/{ocsf_schema.upper()}/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
            logger.info("Writing transformed events to: "+s3_url)
            wr.s3.to_parquet(
                df=df_map,
                path=s3_url,
                compression='gzip'
            )
            logger.info("Successfully wrote to: "+s3_url)

    if unmapped_events:

        unmapped_events_df = pd.DataFrame(unmapped_events)

        s3_url = f's3://{SEC_LAKE_BUCKET}UNMAPPED_EVENTS/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
        logger.info("Writing unmapped events to: "+s3_url)
        wr.s3.to_parquet(
            df=unmapped_events_df,
            path=s3_url,
            compression='gzip'
            )
        logger.info("Successfully wrote unmapped events to: "+s3_url)

    logger.info('Successfully processed {} records.'.format(len(event['Records'])))

    return