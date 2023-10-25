import base64
import json
import os
import uuid
import datetime
import pandas as pd
import awswrangler as wr

print('Loading function')

# Consider overrides for account_id and region

payload_json = {}

SEC_LAKE_BUCKET = os.environ['SEC_LAKE_BUCKET']

sysmon_mapping = { 
    'sysmon_events':
        {
            1: {
                'schema': 'process_activity',
                'mapping': {   
                    'metadata': {
                        'profiles': 'host',
                        'version': 'v1.0.0-rc2',
                        'product' : {
                            'name': 'System Monitor (Sysmon)',
                            'vendor_name': 'Microsoft Sysinternals',
                            'version': 'v15.0'
                        }
                    },
                    'severity': 'Informational',
                    'severity_id': 1,
                    'category_uid': 1,
                    'category_name': 'System Activity',
                    'class_uid': 1007,
                    'class_name': 'Process Activity',
                    'type_uid': 100701,
                    'time': 'Event.Description.UtcTime',
                    'activity_id': {
                        'enum': {
                            'evaluate': 'Event.EventId',
                            'values': {
                                1: 1,
                                5: 2,
                                7: 3,
                                10: 3,
                                19: 3,
                                20: 3,
                                21: 3,
                                25: 4
                            },
                            'other': 99
                        }
                    },
                    'actor': {
                        'process': 'Event.Description.Image'
                    },
                    'device': {
                        'type_id': 6,
                        'instance_uid': 'Event.source_instance_id'
                    },
                    'process': {
                        'pid': 'Event.Description.ProcessId',
                        'uid': 'Event.Description.ProcessGuid',
                        'name': 'Event.Description.Image',
                        'user': 'Event.Description.User',
                        'loaded_modules': 'Event.Description.ImageLoaded'
                    },
                    'unmapped': {
                        'rulename': 'Event.Description.RuleName'
                    }
                    
                }
            },
            5: {
                'schema': 'process_activity',
                'mapping': {   
                    'metadata': {
                        'profiles': 'host',
                        'version': 'v1.0.0-rc2',
                        'product' : {
                            'name': 'System Monitor (Sysmon)',
                            'vendor_name': 'Microsoft Sysinternals',
                            'version': 'v15.0'
                        }
                    },
                    'severity': 'Informational',
                    'severity_id': 1,
                    'category_uid': 1,
                    'category_name': 'System Activity',
                    'class_uid': 1007,
                    'class_name': 'Process Activity',
                    'type_uid': 100701,
                    'time': 'Event.Description.UtcTime',
                    'activity_id': {
                        'enum': {
                            'evaluate': 'Event.EventId',
                            'values': {
                                1: 1,
                                5: 2,
                                7: 3,
                                10: 3,
                                19: 3,
                                20: 3,
                                21: 3,
                                25: 4
                            },
                            'other': 99
                        }
                    },
                    'actor': {
                        'process': 'Event.Description.Image'
                    },
                    'device': {
                        'type_id': 6,
                        'instance_uid': 'Event.source_instance_id'
                    },
                    'process': {
                        'pid': 'Event.Description.ProcessId',
                        'uid': 'Event.Description.ProcessGuid',
                        'name': 'Event.Description.Image',
                        'user': 'Event.Description.User',
                        'loaded_modules': 'Event.Description.ImageLoaded'
                    },
                    'unmapped': {
                        'rulename': 'Event.Description.RuleName'
                    }
                    
                }
            },
            11: {
                'schema': 'file_activity',
                'mapping': {   
                    'metadata': {
                        'profiles': 'host',
                        'version': 'v1.0.0-rc2',
                        'product' : {
                            'name': 'System Monitor (Sysmon)',
                            'vendor_name': 'Microsoft Sysinternals',
                            'version': 'v15.0'
                        }
                    },
                    'severity': 'Informational',
                    'severity_id': 1,
                    'category_uid': 1,
                    'category_name': 'System Activity',
                    'class_uid': 1001,
                    'class_name': 'File Activity',
                    'type_uid': 100101,
                    'time': 'Event.Description.UtcTime',
                    'activity_id': {
                        'enum': {
                            'evaluate': 'Event.EventId',
                            'values': {
                                2: 6,
                                11: 1,
                                15: 1,
                                24: 3,
                                23: 4
                            },
                            'other': 99
                        }
                    },
                    'actor': {
                        'process': 'Event.Description.Image'
                    },
                    'device': {
                        'type_id': 6,
                        'instance_uid': 'Event.source_instance_id'
                    },
                    'unmapped': {
                        'rulename': 'Event.Description.RuleName',
                        'process': {
                            'pid': 'Event.Description.ProcessId',
                            'uid': 'Event.Description.ProcessGuid',
                            'name': 'Event.Description.Image',
                            'user': 'Event.Description.User'
                        }
                    } 
                }
            },
            23: {
                'schema': 'file_activity',
                'mapping': {   
                    'metadata': {
                        'profiles': 'host',
                        'version': 'v1.0.0-rc2',
                        'product' : {
                            'name': 'System Monitor (Sysmon)',
                            'vendor_name': 'Microsoft Sysinternals',
                            'version': 'v15.0'
                        }
                    },
                    'severity': 'Informational',
                    'severity_id': 1,
                    'category_uid': 1,
                    'category_name': 'System Activity',
                    'class_uid': 1001,
                    'class_name': 'File Activity',
                    'type_uid': 100101,
                    'time': 'Event.Description.UtcTime',
                    'activity_id': {
                        'enum': {
                            'evaluate': 'Event.EventId',
                            'values': {
                                2: 6,
                                11: 1,
                                15: 1,
                                24: 3,
                                23: 4
                            },
                            'other': 99
                        }
                    },
                    'actor': {
                        'process': 'Event.Description.Image'
                    },
                    'device': {
                        'type_id': 6,
                        'instance_uid': 'Event.source_instance_id'
                    },
                    'unmapped': {
                        'rulename': 'Event.Description.RuleName',
                        'process': {
                            'pid': 'Event.Description.ProcessId',
                            'uid': 'Event.Description.ProcessGuid',
                            'name': 'Event.Description.Image',
                            'user': 'Event.Description.User'
                        }
                    } 
                }
            }
        }
    }

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
    eventday = str(dt_now.year)+str(dt_now.month)+str(dt_now.day)
    
    output = []
    output_for_df = []

    transformed_records = {}
    
    for record in event['Records']:
        print(record['eventID'])
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        print("Raw Sysmon event: "+str(payload))
        payload_json = json.loads(payload)
        data = {}
        for line in payload_json['Description'].split('\r\n'):
            parts = line.split(': ', 1)  # Splitting by ': '
            key = parts[0]
            # If value is present, assign it to the key, otherwise assign an empty string
            value = parts[1] if len(parts) > 1 else ""
            data[key] = value
        
        payload_json['Description'] = data

        if payload_json['EventId'] in sysmon_mapping['sysmon_events']:
            print("Found event mapping: "+str(sysmon_mapping['sysmon_events'][payload_json['EventId']]))
            new_map = perform_transform(sysmon_mapping['sysmon_events'][payload_json['EventId']]['mapping'], payload_json)
            new_schema = {}
            new_schema['target_schema'] = sysmon_mapping['sysmon_events'][payload_json['EventId']]['schema']
            new_schema['target_mapping'] = new_map
                
            print("Transformed OCSF record: "+str(new_schema))
                
            output_record = {
                'recordId': record['eventID'],
                'result': 'Ok',
                'data': base64.b64encode(str(new_schema['target_mapping']).encode('utf-8')).decode('utf-8')
            }
            output.append(output_record)
            output_for_df.append(new_schema)
                
        else: # we dont have an event Id mapping so drop the record
        
            print("Dropped record - no mapping for event")
        
            output_record = {
                    'recordId': record['eventID'],
                    'result': 'No mapping for event',
                    'data': payload_json
                }
            output.append(output_record)
    
    if output_for_df:
        
        df = pd.DataFrame(output_for_df)
        df_schemas = df['target_schema'].unique()
    
        for ocsf_schema in df_schemas:
            df_map = (df[df['target_schema']==ocsf_schema])
            df_map = pd.json_normalize(df_map['target_mapping'], max_level=0)
            s3_url = f's3://{SEC_LAKE_BUCKET}1.0/{ocsf_schema.upper()}/region={aws_region}/accountId={aws_account_id}/eventDay={eventday}/{uuid.uuid4().hex}.gz.parquet'
            print(s3_url)
            wr.s3.to_parquet(
                df=df_map,
                path=s3_url,
                compression='gzip'
            )
            print("Successfully wrote to: "+s3_url)

    print('Successfully processed {} records.'.format(len(event['Records'])))

    return {'records': output}
