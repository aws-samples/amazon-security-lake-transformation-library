# Tanium Device Inventory

**OCSF Classes**: DEVICE_INVENTORY_INFO

## Mapping

**Sample Device Inventory Info event mapping**

1. CSV log event from Tanium device inventory scan.

    ```csv
    computer_name,mac_address,ip_address,chassis_type,operating_system,risk_score,domain_name,last_logged_in_user,manufacturer,computer_id,id,custom_tags,computer_serial_number,tanium_report,timestamp
    win-server01,00:1A:2B:3C:4D:5E,"10.10.1.45
    fe80::215:5dff:fe00:1234",Virtual,Windows Server 2019 Standard,326,EXAMPLE,EXAMPLE\Administrator,VMware,1234567890,WIN001,"Production,Critical",VM123456789,Tanium Platform Inventory,2025-04-07T14:23:45+00:00
    ```

2. Attribute mapping for Device Inventory Info class

    |OCSF|Raw|
    |-|-|
    | metadata.profiles | [host] |
    | metadata.version | v1.1.0 |
    | metadata.product.name | Tanium |
    | metadata.product.vendor_name | Tanium Inc. |
    | metadata.product.feature.name | Platform Inventory / Core Inventory |
    | metadata.product.uid | `<tanium_report>` |
    | severity | Informational |
    | severity_id | 1 |
    | category_uid | 5 |
    | category_name | Discovery |
    | class_uid | 5001 |
    | class_name | Device Inventory Info |
    | type_uid | 500101 |
    | activity_id | 1 |
    | activity_name | Collect |
    | time | `<timestamp>` |
    | device.name | `<computer_name>` |
    | device.hostname | `<computer_name>` |
    | device.uid | `<computer_id>` |
    | device.type | Mapped from `<chassis_type>` |
    | device.type_id | Mapped from `<chassis_type>` |
    | device.os.name | Extracted from `<operating_system>` |
    | device.os.version | Extracted from `<operating_system>` |
    | device.os.type | Mapped from `<operating_system>` |
    | device.os.type_id | Mapped from `<operating_system>` |
    | device.network_interfaces | Array built from `<mac_address>` and `<ip_address>` |
    | device.hw_info.serial_number | `<computer_serial_number>` |
    | device.hw_info.manufacturer | `<manufacturer>` |
    | device.domain | `<domain_name>` |
    | device.groups | Array from `<custom_tags>` |
    | device.risk_score | `<risk_score>` (numeric) |
    | device.risk_level | Mapped from `<risk_score>` |
    | device.risk_level_id | Mapped from `<risk_score>` |
    | user.name | Extracted from `<last_logged_in_user>` |
    | user.domain | Extracted from `<last_logged_in_user>` |

## Network Interface Array Processing

The Tanium preprocessor implements specialized logic for handling network interface data:

### Input Format
- **MAC Addresses**: Newline-separated values in `mac_address` field
- **IP Addresses**: Newline-separated values in `ip_address` field

### Processing Logic
1. **First MAC + First IP**: Creates one interface with both MAC and IP
2. **Remaining MACs**: Individual interfaces with MAC only
3. **Remaining IPs**: Individual interfaces with IP only

### Examples

**Example 1: Equal MACs and IPs**
```
Input:
mac_address: "00:1A:2B:3C:4D:5E\n00:25:90:45:72:BC"
ip_address: "10.10.1.45\n192.168.1.100"

Output: 3 network interfaces
- Interface 1: MAC+IP (00:1A:2B:3C:4D:5E + 10.10.1.45)
- Interface 2: MAC only (00:25:90:45:72:BC)
- Interface 3: IP only (192.168.1.100)
```

**Example 2: More IPs than MACs**
```
Input:
mac_address: "00:1A:2B:3C:4D:5E"
ip_address: "10.10.1.45\n192.168.1.100\nfe80::215:5dff:fe00:1234"

Output: 3 network interfaces
- Interface 1: MAC+IP (00:1A:2B:3C:4D:5E + 10.10.1.45)
- Interface 2: IP only (192.168.1.100)
- Interface 3: IP only (fe80::215:5dff:fe00:1234)
```

## Field Mappings

### Device Type Mapping
| Tanium Chassis Type | OCSF Device Type | OCSF Type ID |
|-|-|-|
| Desktop | Desktop | 1 |
| Laptop | Laptop | 3 |
| Rack Mount Chassis | Server | 4 |
| Virtual | Virtual Machine | 6 |

### Operating System Type Mapping
| OS String Contains | OCSF OS Type | OCSF Type ID |
|-|-|-|
| windows | Windows | 100 |
| ubuntu, linux | Linux | 200 |
| macos, darwin | macOS | 300 |
| cisco ios | Other | 99 |

### Risk Level Mapping
| Risk Score Range | OCSF Risk Level | OCSF Risk Level ID |
|-|-|-|
| 0-100 | Low | 1 |
| 101-200 | Medium | 2 |
| 201-300 | High | 3 |
| 301+ | Critical | 4 |

### Network Interface Fields
Each network interface object includes:
| OCSF Field | Description | Example |
|-|-|-|
| mac | Normalized MAC address | "00:1A:2B:3C:4D:5E" |
| ip | IP address | "10.10.1.45" |
| type | IP type string | "IPv4" or "IPv6" |
| type_id | IP type identifier | 1 (IPv4) or 2 (IPv6) |
| subnet_prefix | Subnet prefix for private IPs | 8, 16, 24, 64 |

## Enrichments vs Unmapped Data

### Enrichments
Structured, actionable data for security analysis:

```json
"enrichments": [
  {
    "name": "Tanium Asset Management",
    "type": "device_inventory",
    "data": {
      "tanium_computer_id": "1234567890",
      "tanium_endpoint_id": "WIN001",
      "scan_report_type": "Platform Inventory",
      "hardware_classification": "Virtual",
      "vulnerability_score": 326.0,
      "last_scan_time": "2025-04-07T14:23:45+00:00"
    }
  },
  {
    "name": "Business Context",
    "type": "asset_classification",
    "data": {
      "asset_tags": ["Production", "Critical"],
      "custom_attributes": "Production,Critical"
    }
  }
]
```

### Unmapped Data
Raw source data for forensic analysis:

```json
"unmapped": {
  "source_data": {
    "csv_mac_addresses": "00:1A:2B:3C:4D:5E",
    "csv_ip_addresses": "10.10.1.45\nfe80::215:5dff:fe00:1234",
    "full_os_string": "Windows Server 2019 Standard",
    "raw_user_string": "EXAMPLE\\Administrator",
    "source_timestamp": "2025-04-07T14:23:45+00:00",
    "tanium_raw_record": "Tanium Platform Inventory"
  }
}
```

## Sample OCSF Output

```json
{
  "metadata": {
    "profiles": ["host"],
    "version": "v1.1.0",
    "product": {
      "name": "Tanium",
      "vendor_name": "Tanium Inc.",
      "feature": {
        "name": "Platform Inventory"
      }
    }
  },
  "severity": "Informational",
  "severity_id": 1,
  "category_uid": 5,
  "category_name": "Discovery",
  "class_uid": 5001,
  "class_name": "Device Inventory Info",
  "type_uid": 500101,
  "activity_id": 1,
  "activity_name": "Collect",
  "time": "2025-04-07T14:23:45+00:00",
  "device": {
    "name": "win-server01",
    "hostname": "win-server01",
    "uid": "1234567890",
    "type": "Virtual Machine",
    "type_id": 6,
    "os": {
      "name": "Windows Server",
      "version": "2019",
      "type": "Windows",
      "type_id": 100
    },
    "network_interfaces": [
      {
        "mac": "00:1A:2B:3C:4D:5E",
        "ip": "10.10.1.45",
        "type": "IPv4",
        "type_id": 1,
        "subnet_prefix": 8
      },
      {
        "ip": "fe80::215:5dff:fe00:1234",
        "type": "IPv6",
        "type_id": 2,
        "subnet_prefix": 64
      }
    ],
    "hw_info": {
      "serial_number": "VM123456789",
      "manufacturer": "VMware"
    },
    "domain": "EXAMPLE",
    "risk_score": 326.0,
    "risk_level": "Critical",
    "risk_level_id": 4
  },
  "user": {
    "name": "Administrator",
    "domain": "EXAMPLE"
  },
  "enrichments": [
    {
      "name": "Tanium Asset Management",
      "type": "device_inventory",
      "data": {
        "tanium_computer_id": "1234567890",
        "tanium_endpoint_id": "WIN001",
        "scan_report_type": "Tanium Platform Inventory",
        "hardware_classification": "Virtual",
        "vulnerability_score": 326.0,
        "last_scan_time": "2025-04-07T14:23:45+00:00"
      }
    },
    {
      "name": "Business Context",
      "type": "asset_classification",
      "data": {
        "asset_tags": ["Production", "Critical"],
        "custom_attributes": "Production,Critical"
      }
    }
  ],
  "unmapped": {
    "source_data": {
      "csv_mac_addresses": "00:1A:2B:3C:4D:5E",
      "csv_ip_addresses": "10.10.1.45\nfe80::215:5dff:fe00:1234",
      "full_os_string": "Windows Server 2019 Standard",
      "raw_user_string": "EXAMPLE\\Administrator",
      "source_timestamp": "2025-04-07T14:23:45+00:00",
      "tanium_raw_record": "Tanium Platform Inventory"
    }
  }
}
```

## Implementation Files

- **Preprocessor**: `transformation_function/preprocessors/tanium_preprocessor.py`
- **Mapping Configuration**: `transformation_function/mappings/tanium_device_inventory_mapping.json`
- **Sources Configuration**: Add Tanium source to `transformation_function/sources_config.json`

## Key Features

1. **OCSF v1.1.0 Compliance**: Full compliance with Device Inventory Info class specification
2. **Network Interface Processing**: Intelligent handling of newline-separated MAC/IP addresses
3. **Risk Assessment**: Automatic risk level calculation from numeric scores
4. **Data Preservation**: Raw data preserved in unmapped section for forensic analysis
5. **Business Context**: Asset tags and classifications in structured enrichments
6. **Error Handling**: Robust processing of malformed or missing data
