# Application Load Balancer

**OCSF Classes**: HTTP_ACTIVITY

## Mapping

**Sample HTTP Activity event mapping for http/https/h2 type logs**

1. `HTTPS` type log event.

    ```
        
    https 2018-07-02T22:23:00.186641Z app/my-loadbalancer/50dc6c495c0c9188 192.168.131.39:2817 10.0.0.1:80 0.086 0.048 0.037 200 200 0 57 "GET https://www.example.com:443/ HTTP/1.1" "curl/7.46.0" ECDHE-RSA-AES128-GCM-SHA256 TLSv1.2 arn:aws:elasticloadbalancing:us-east-2:XXXXXXXXXXXX:targetgroup/my-targets/73e2d6bc24d8a067 "Root=1-58337281-1d84f3d73c47ec4e58577259" "www.example.com" "arn:aws:acm:us-east-2:XXXXXXXXXXXX:certificate/XXXXXXXX-1234-1234-1234-XXXXXXXXXXXX" 1 2018-07-02T22:22:48.364000Z "authenticate,forward" "-" "-" "10.0.0.1:80" "200" "-" "-" TID_123456

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
