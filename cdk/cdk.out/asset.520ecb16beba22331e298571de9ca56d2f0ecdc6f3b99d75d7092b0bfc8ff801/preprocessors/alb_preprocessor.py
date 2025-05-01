"""
AWS Application Load Balancer (ALB) logs preprocessor module.
This module handles the preprocessing of ALB logs into structured format.
"""
import logging
import re
import json

logger = logging.getLogger()

def preprocess_event(raw_log):
    """
    Preprocess a raw ALB log string
    
    Args:
        raw_log (str): Raw ALB log entry string
        
    Returns:
        dict: Structured data extracted from the log
    """
    return preprocess_alb_log_entry(raw_log)

def preprocess_alb_log_entry(log_entry):
    """
    Preprocess a single ALB log entry string into structured data
    
    Args:
        log_entry (str): Raw ALB log entry string
        
    Returns:
        dict: Parsed fields from the ALB log
    """
    logger.debug(f"Preprocessing ALB log entry type: {type(log_entry)}")
    fields = [
        "type", "time", "elb", "client:port", "target:port",
        "request_processing_time", "target_processing_time",
        "response_processing_time", "elb_status_code", "target_status_code",
        "received_bytes", "sent_bytes", "request", "user_agent", "ssl_cipher",
        "ssl_protocol", "target_group_arn", "trace_id", "domain_name",
        "chosen_cert_arn", "matched_rule_priority", "request_creation_time",
        "actions_executed", "redirect_url", "error_reason", "target:port_list",
        "target_status_code_list", "classification", "classification_reason",
        "conn_trace_id"
    ]
    
    # Use regex to split the log entry, preserving quoted strings
    values = re.findall(r'(?:[^\s"]+|"[^"]*")+', log_entry)
    
    # Debug log for parsing results
    logger.debug(f"Parsed {len(values)} values from ALB log")
    
    result = {}
    
    for i, field in enumerate(fields):
        if i < len(values):
            value = values[i].strip('"')
            
            # Special debug for time field
            if field == "time":
                logger.debug(f"Extracted time value: {value}")
            
            if field in ["client:port", "target:port"]:
                if value == '-':
                    result[field.replace(":port", "_ip")] = '-'
                    result[field.replace(":port", "_port")] = '-'
                else:
                    try:
                        ip, port = value.rsplit(':', 1)
                        result[field.replace(":port", "_ip")] = ip
                        result[field.replace(":port", "_port")] = port
                    except ValueError:
                        result[field.replace(":port", "_ip")] = '-'
                        result[field.replace(":port", "_port")] = '-'
            
            elif field == "target:port_list":
                if value == '-':
                    result["target_ip_list"] = '-'
                    result["target_port_list"] = '-'
                else:
                    try:
                        ip_port_list = value.split(' ')
                        result["target_ip_list"] = ' '.join([ip_port.rsplit(':', 1)[0] for ip_port in ip_port_list])
                        result["target_port_list"] = ' '.join([ip_port.rsplit(':', 1)[1] for ip_port in ip_port_list])
                    except (ValueError, IndexError):
                        result["target_ip_list"] = '-'
                        result["target_port_list"] = '-'
            
            elif field == "request":
                if value != '-':
                    request_parts = value.split(' ')
                    if len(request_parts) == 3:
                        result["request_method"] = request_parts[0]
                        result["request_url"] = request_parts[1]
                        result["request_protocol"] = request_parts[2]
                    else:
                        # If the request doesn't have the expected format, keep it as is
                        result["request"] = value
                else:
                    result["request_method"] = '-'
                    result["request_url"] = '-'
                    result["request_protocol"] = '-'
            
            else:
                result[field] = value if value != '-' else '-'
        else:
            result[field] = '-'
    
    # Remove the original "request" field if it was successfully split
    if "request_method" in result:
        result.pop("request", None)
    
    # Debug log for extracted fields
    logger.debug(f"Extracted fields: {list(result.keys())}")
    if 'time' in result:
        logger.debug(f"Time field value: {result['time']}")
    else:
        logger.warning("No time field extracted from ALB log")
    
    return result