"""
Windows Sysmon event preprocessor module.
This module handles the preprocessing of Windows Sysmon events.
"""
import logging

logger = logging.getLogger()

def preprocess_event(payload_json):
    """
    Preprocess Windows Sysmon events
    
    Transforms the Description field from string format to structured JSON
    
    Args:
        payload_json (dict): The raw Sysmon event JSON
        
    Returns:
        dict: The processed Sysmon event with Description field parsed
    """
    if 'Description' in payload_json and isinstance(payload_json['Description'], str):
        data = {}
        for line in payload_json['Description'].split('\r\n'):
            parts = line.split(': ', 1)  # Splitting by ': '
            if len(parts) > 1:
                key = parts[0]
                value = parts[1]
                data[key] = value
            elif len(parts) == 1 and parts[0]:
                # Handle lines without delimiter but with content
                data[f"Line{len(data)+1}"] = parts[0]
        
        # Replace the original Description string with the structured data
        payload_json['Description'] = data
        logger.debug("Preprocessed Sysmon Description field successfully")
    else:
        logger.debug("No Description field to preprocess or already in structured format")
        
    return payload_json