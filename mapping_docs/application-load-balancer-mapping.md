# Application Load Balancer

**OCSF Classes**: HTTP_ACTIVITY

## Mapping

**Sample HTTP Activity event mapping for http/https/h2 type logs**

1. `HTTPS` type log event.

    ```
        
    https 2018-07-02T22:23:00.186641Z app/my-loadbalancer/50dc6c495c0c9188 192.168.131.39:2817 10.0.0.1:80
    0.086 0.048 0.037 200 200 0 57 "GET https://www.example.com:443/ HTTP/1.1" "curl/7.46.0"
    ECDHE-RSA-AES128-GCM-SHA256 TLSv1.2
    arn:aws:elasticloadbalancing:us-east-2:XXXXXXXXXXXX:targetgroup/my-targets/73e2d6bc24d8a067 
    "Root=1-58337281-1d84f3d73c47ec4e58577259" "www.example.com" 
    "arn:aws:acm:us-east-2:XXXXXXXXXXXX:certificate/XXXXXXXX-1234-1234-1234-XXXXXXXXXXXX" 1 
    2018-07-02T22:22:48.364000Z "authenticate,forward" "-" "-" "10.0.0.1:80" "200" "-" "-" TID_123456

    ```

2. Attribute mapping for HTTP Activity class

    |OCSF|Raw|
    |-|-|
    | app_name | `<elb_name>` |
    | cloud.provider | AWS |
    | metadata.profiles | [cloud, loadbalancing] |
    | metadata.product.name | AWS ELB |
    | metadata.product.feature.name | Application Load Balancer |
    | metadata.product.vendor_name | AWS |
    | metadata.product.uid | `<elb>` |
    | severity | Informational |
    | severity_id | 1 |
    | category_uid | 4 |
    | category_name | Network Activity |
    | class_uid | 4002 |
    | class_name | HTTP Activity |
    | activity_id | `enum` evaluated on `<request_method` |
    | activity_name | `<request_method>` |
    | http_request.http_method | `<request_method>` |
    | http_request.user_agent | `<user_agent>`|
    | http_request.url.hostname | `<domain_name>` |
    | http_request.url.url_string | `<request_url>` |
    | http_request.url.scheme | `<type>` |
    | http_response.code | `<elb_status_code>` |
    | connection_info | {direction_id: 1, protocol_ver_id: 4, protocol_name: "tcp", protocol_num: 6} |
    | dst_endpoint | {hostname: `<target_group_arn>`, ip: `<target_ip>`, port: `<target_port>`, type: "Virtual", type_id: 6} |
    | src_endpoint | {ip: `<client_ip>`, port: `<client_port>`} |
    | duration | `<request_processing_time>` |
    | time | `<time>` |
    | start_time | `<request_creation_time>` |
    | traffic | {bytes_in: `<received_bytes>`, bytes_out: `<sent_bytes>`} |
    | tls | certificate: `<chosen_cert_arn>`, cipher: `<ssl_cipher>`, sni: `<domain_name>`, version: `<ssl_protocol>` |
    | unmapped | {target_processing_time: `<target_processing_time>`, response_processing_time: `<response_processing_time>`, target_status_code: `<target_status_code>` matched_rule_priority": `<matched_rule_priority>`, actions_executed: `<actions_executed>`, redirect_url: `<redirect_url>`, error_reason: `<error_reason>`, target_ip_list: `<target_ip_list>`, target_port_list: `<target_port_list>`, target_status_code_list: `<target_status_code_list>`, classification: `<classification>`, classification_reason: `<classification_reason>`, trace_id: `<trace_id>`, conn_trace_id: `<conn_trace_id>`, request_protocol: `<request_protocol>`} |
