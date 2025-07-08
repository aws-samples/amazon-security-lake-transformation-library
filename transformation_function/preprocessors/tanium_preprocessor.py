"""
Tanium device inventory logs preprocessor module.
This module handles the preprocessing of Tanium CSV logs into structured format
with proper network interface array mapping.
"""
import logging
import json
import ipaddress
import csv
from io import StringIO
from typing import Dict, List, Any, Optional

logger = logging.getLogger()

def preprocess_event(raw_log):
    """
    Preprocess a raw Tanium CSV log line
    
    Args:
        raw_log (str): Raw CSV line from Tanium
        
    Returns:
        dict: Structured data with network interfaces properly mapped
    """
    # Parse CSV string to dictionary
    record = parse_csv_line(raw_log.strip())
    
    # Skip header lines or invalid records
    if record is None:
        return None
    
    # Process with existing logic
    return preprocess_tanium_device_record(record)

def parse_csv_line(csv_line: str) -> Optional[Dict[str, str]]:
    """
    Parse a single CSV line into a dictionary using the known field order
    
    Args:
        csv_line (str): Raw CSV line
        
    Returns:
        Dict[str, str]: Parsed CSV fields as dictionary, or None if header/invalid
    """
    # Skip empty lines
    if not csv_line.strip():
        return None
    
    # Skip header line
    if csv_line.startswith('computer_name,'):
        logger.debug("Skipping CSV header line")
        return None
    
    # Define the expected field order based on the CSV structure
    fieldnames = [
        'computer_name', 'mac_address', 'ip_address', 'chassis_type',
        'operating_system', 'risk_score', 'domain_name', 'last_logged_in_user',
        'manufacturer', 'computer_id', 'id', 'custom_tags',
        'computer_serial_number', 'tanium_report', 'timestamp'
    ]
    
    try:
        # Use Python's CSV parser to handle quoted fields properly
        reader = csv.DictReader(StringIO(csv_line), fieldnames=fieldnames)
        record = next(reader)
        
        logger.debug(f"Parsed CSV record for computer: {record.get('computer_name', 'unknown')}")
        return record
        
    except Exception as e:
        logger.error(f"Error parsing CSV line: {e}")
        logger.debug(f"Problematic CSV line: {csv_line}")
        return None

def preprocess_tanium_device_record(record):
    """
    Preprocess a single Tanium device record into structured data
    with network interfaces as an array
    
    Args:
        record (dict): Raw Tanium device record from CSV
        
    Returns:
        dict: Processed record with network_interfaces array
    """
    logger.debug(f"Preprocessing Tanium device record: {record.get('computer_name', 'unknown')}")
    
    # Start with the original record
    processed_record = record.copy()
    
    # Process network interfaces - split comma-separated values and create array
    network_interfaces = build_network_interfaces_array(
        record.get('mac_address', ''),
        record.get('ip_address', '')
    )
    
    # Add the network interfaces array to the record
    processed_record['network_interfaces'] = network_interfaces
    
    # Process OS information
    os_info = extract_os_information(record.get('operating_system', ''))
    processed_record.update(os_info)
    
    # Process user information
    user_info = extract_user_information(record.get('last_logged_in_user', ''))
    processed_record.update(user_info)
    
    # Process custom tags
    if record.get('custom_tags'):
        processed_record['tags_array'] = [tag.strip() for tag in record.get('custom_tags', '').split(',')]
    else:
        processed_record['tags_array'] = []
    
    # Process risk score
    try:
        processed_record['risk_score_numeric'] = float(record.get('risk_score', 0))
    except (ValueError, TypeError):
        processed_record['risk_score_numeric'] = 0.0
    
    # Map device type
    processed_record['device_type_mapped'] = map_device_type(record.get('chassis_type', ''))
    processed_record['device_type_id'] = map_device_type_id(record.get('chassis_type', ''))
    
    logger.debug(f"Processed {len(network_interfaces)} network interfaces for device {record.get('computer_name', 'unknown')}")
    
    return processed_record

def build_network_interfaces_array(mac_string: str, ip_string: str) -> List[Dict[str, Any]]:
    """
    Build network interfaces array from comma-separated MAC and IP strings.
    Customer requirements:
    - If 1 MAC: map that MAC to ALL IP addresses
    - If multiple MACs: only map FIRST MAC to FIRST IP address
    
    Args:
        mac_string (str): Comma-separated MAC addresses
        ip_string (str): Comma-separated IP addresses
        
    Returns:
        List[Dict]: Array of network interface objects
    """
    interfaces = []
    
    # Split and clean MAC addresses
    macs = []
    if mac_string and mac_string.strip() != '-':
        macs = [normalize_mac_address(mac.strip()) for mac in mac_string.split(',')]
        macs = [mac for mac in macs if mac]  # Remove empty strings
    
    # Split and validate IP addresses
    ips = []
    if ip_string and ip_string.strip() != '-':
        for ip in ip_string.split(','):
            ip = ip.strip()
            if is_valid_ip(ip):
                ips.append(ip)
    
    # Apply customer-specific mapping logic
    if len(macs) == 1:
        # Single MAC: map to ALL IP addresses
        single_mac = macs[0]
        for ip in ips:
            interface = {'mac': single_mac, 'ip': ip}
            
            # Add IP type information
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.version == 4:
                    interface['type'] = 'IPv4'
                    interface['type_id'] = 1
                else:
                    interface['type'] = 'IPv6'
                    interface['type_id'] = 2
                
                # Add subnet prefix for private IPs
                if ip_obj.is_private:
                    interface['subnet_prefix'] = get_subnet_prefix(ip, ip_obj.version)
            except ValueError:
                logger.warning(f"Invalid IP address format: {ip}")
            
            interfaces.append(interface)
            
    elif len(macs) > 1:
        # Multiple MACs: only map FIRST MAC to FIRST IP
        if len(ips) > 0:
            interface = {'mac': macs[0], 'ip': ips[0]}
            
            # Add IP type information
            try:
                ip_obj = ipaddress.ip_address(ips[0])
                if ip_obj.version == 4:
                    interface['type'] = 'IPv4'
                    interface['type_id'] = 1
                else:
                    interface['type'] = 'IPv6'
                    interface['type_id'] = 2
                
                # Add subnet prefix for private IPs
                if ip_obj.is_private:
                    interface['subnet_prefix'] = get_subnet_prefix(ips[0], ip_obj.version)
            except ValueError:
                logger.warning(f"Invalid IP address format: {ips[0]}")
            
            interfaces.append(interface)
        else:
            # No IPs available, just add MAC
            interfaces.append({'mac': macs[0]})
    
    else:
        # No MACs, but might have IPs - add first IP only
        if len(ips) > 0:
            interface = {'ip': ips[0]}
            
            # Add IP type information
            try:
                ip_obj = ipaddress.ip_address(ips[0])
                if ip_obj.version == 4:
                    interface['type'] = 'IPv4'
                    interface['type_id'] = 1
                else:
                    interface['type'] = 'IPv6'
                    interface['type_id'] = 2
                
                # Add subnet prefix for private IPs
                if ip_obj.is_private:
                    interface['subnet_prefix'] = get_subnet_prefix(ips[0], ip_obj.version)
            except ValueError:
                logger.warning(f"Invalid IP address format: {ips[0]}")
            
            interfaces.append(interface)
    
    return interfaces

def normalize_mac_address(mac: str) -> str:
    """
    Normalize MAC address format to uppercase with colons
    
    Args:
        mac (str): MAC address in various formats
        
    Returns:
        str: Normalized MAC address or empty string if invalid
    """
    if not mac or mac.strip() == '-':
        return ''
    
    # Remove common separators and spaces
    clean_mac = mac.replace(':', '').replace('-', '').replace('.', '').replace(' ', '').upper()
    
    # Check if we have 12 hex characters
    if len(clean_mac) == 12 and all(c in '0123456789ABCDEF' for c in clean_mac):
        # Format as XX:XX:XX:XX:XX:XX
        return ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))
    
    logger.warning(f"Invalid MAC address format: {mac}")
    return ''

def is_valid_ip(ip: str) -> bool:
    """
    Check if string is a valid IP address
    
    Args:
        ip (str): IP address string
        
    Returns:
        bool: True if valid IP address
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def get_subnet_prefix(ip: str, version: int) -> int:
    """
    Get common subnet prefix for private IPs
    
    Args:
        ip (str): IP address
        version (int): IP version (4 or 6)
        
    Returns:
        int: Subnet prefix length
    """
    if version == 4:
        if ip.startswith('10.'):
            return 8
        elif ip.startswith('172.'):
            return 12
        elif ip.startswith('192.168.'):
            return 16
        else:
            return 24  # Default for IPv4
    else:
        return 64  # Default for IPv6

def extract_os_information(os_string: str) -> Dict[str, Any]:
    """
    Extract OS name, version, and type from OS string
    
    Args:
        os_string (str): Full OS string
        
    Returns:
        Dict: OS information fields
    """
    if not os_string:
        return {
            'os_name': None,
            'os_version': None,
            'os_type': 'Unknown',
            'os_type_id': 99
        }
    
    os_lower = os_string.lower()
    
    # Extract OS name (everything before first number)
    import re
    name_match = re.match(r'^([^\d]+)', os_string.strip())
    os_name = name_match.group(1).strip() if name_match else os_string
    
    # Extract version (first sequence of numbers and dots)
    version_match = re.search(r'([\d\.]+)', os_string)
    os_version = version_match.group(1) if version_match else None
    
    # Determine OS type
    if 'windows' in os_lower:
        os_type = 'Windows'
        os_type_id = 100
    elif 'ubuntu' in os_lower or 'linux' in os_lower:
        os_type = 'Linux'
        os_type_id = 200
    elif 'macos' in os_lower or 'darwin' in os_lower:
        os_type = 'macOS'
        os_type_id = 300
    elif 'ios' in os_lower and 'cisco' in os_lower:
        os_type = 'Other'
        os_type_id = 99
    else:
        os_type = 'Unknown'
        os_type_id = 99
    
    return {
        'os_name': os_name,
        'os_version': os_version,
        'os_type': os_type,
        'os_type_id': os_type_id
    }

def extract_user_information(user_string: str) -> Dict[str, Any]:
    """
    Extract username and domain from user string
    
    Args:
        user_string (str): User string in format DOMAIN\\username or username
        
    Returns:
        Dict: User information fields
    """
    if not user_string or user_string.strip() == '-':
        return {
            'username': None,
            'user_domain': None
        }
    
    if '\\' in user_string:
        parts = user_string.split('\\', 1)
        return {
            'username': parts[1] if len(parts) > 1 else user_string,
            'user_domain': parts[0] if len(parts) > 1 else None
        }
    else:
        return {
            'username': user_string,
            'user_domain': None
        }

def map_device_type(chassis_type: str) -> str:
    """
    Map chassis type to OCSF device type
    
    Args:
        chassis_type (str): Chassis type from Tanium
        
    Returns:
        str: OCSF device type
    """
    mapping = {
        'Desktop': 'Desktop',
        'Laptop': 'Laptop',
        'Rack Mount Chassis': 'Server',
        'Virtual': 'Virtual Machine'
    }
    return mapping.get(chassis_type, 'Unknown')

def map_device_type_id(chassis_type: str) -> int:
    """
    Map chassis type to OCSF device type ID
    
    Args:
        chassis_type (str): Chassis type from Tanium
        
    Returns:
        int: OCSF device type ID
    """
    mapping = {
        'Desktop': 1,
        'Laptop': 3,
        'Rack Mount Chassis': 4,
        'Virtual': 6
    }
    return mapping.get(chassis_type, 99)  # Unknown
