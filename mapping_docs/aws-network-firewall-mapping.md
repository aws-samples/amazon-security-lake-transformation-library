# AWS Network Firewall

**OCSF Classes**: NETWORK_ACTIVITY

## Mapping

**Sample Network Activity event mapping for Netflow logs**

1. `Netflow` type log event.

    ```json
    {
        "firewall_name":"firewall",
        "availability_zone":"us-east-1b",
        "event_timestamp":"1601587565",
        "event":{
            "timestamp":"2020-10-01T21:26:05.007515+0000",
            "flow_id":1770453319291727,
            "event_type":"netflow",
            "src_ip":"45.129.33.153",
            "src_port":47047,
            "dest_ip":"172.31.16.139",
            "dest_port":16463,
            "proto":"TCP",
            "netflow":{
                "pkts":1,
                "bytes":60,
                "start":"2020-10-01T21:25:04.070479+0000",
                "end":"2020-10-01T21:25:04.070479+0000",
                "age":0,
                "min_ttl":241,
                "max_ttl":241
            },
            "tcp":{
                "tcp_flags":"02",
                "syn":true
            }
        }
    }
    ```

2. Attribute mapping for Network Activity class

    |OCSF|Raw|
    |-|-|
    | app_name | `<firewall_name>` |
    | cloud.provider | AWS |
    | metadata.profiles | [cloud, firewall] |
    | metadata.product.name | AWS Network Firewall |
    | metadata.product.feature.name | Firewall |
    | metadata.product.vendor_name | AWS |
    | severity | Informational |
    | severity_id | 1 |
    | activity_id | 6 |
    | activity_name | Traffic |
    | category_uid | 4 |
    | category_name | Network Activity |
    | class_uid | 4001 |
    | type_uid | 400106 |
    | class_name | Network Activity |
    | dst_endpoint | {ip: `<event.dest_ip>`, port: `<event.dest_port>`} |
    | src_endpoint | {ip: `<event.src_ip>`, port: `<event.src_port>`} |
    | time | `<event.timestamp>` |
    | connection_info | {uid: `<event.flow_id>`, protocol_name: `<event.proto>`, tcp_flags: `<event.tcp.tcp_flags>`} |
    | start_time | `<event.netflow.start>` |
    | end_time | `<event.netflow.end>` |
    | traffic | {bytes: `<event.netflow.bytes>`, packets: `<event.netflow.packets>`} |
    | unmapped | {availability_zone: `availability_zone`, event_type: `<event.event_type>`, netflow: {age: `<event.netflow.age>`, min_ttl: `<event.netflow.min_ttl>`, max_ttl: `<event.netflow.max_ttl>`}, tcp: {syn: `<event.tcp.syn>`, fin: `<event.tcp.fin>`, ack: `<event.tcp.ack>`, psh: `<event.tcp.psh>`}} |
