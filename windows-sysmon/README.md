# windows-sysmon

[Microsoft Sysinternals System Monitor (Sysmon)](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon) is a service that monitors and logs system activity to the Windows event log. It is one of the more commonly used log collection tools used by customers in a Windows Operating System environment as it provides detailed information about process creations, network connections, and changes to file creation time. This host level information can prove crucial during threat hunting scenarios and security analytics.

## Solution overview

The solution for this pattern uses [Amazon Kinesis Data Firehose](https://aws.amazon.com/kinesis/data-firehose/) and [AWS Lambda](https://aws.amazon.com/lambda/) to implement the schema transformation. Kinesis Data Firehose is an extract, transform, and load (ETL) service that reliably captures, transforms, and delivers streaming data to data lakes, data stores, and analytics services. You can stream data into S3 and convert data into required formats like OCSF for analysis without building processing pipelines. Lambda is a serverless, event-driven compute service that lets you run code for virtually any type of application or backend service without provisioning or managing servers. You can integrate Lambda with Kinesis Data Firehose to trigger transformation tasks on events streaming in the Data Firehose.
To stream sysmon logs from the host, you can use [Amazon Kinesis Agent for Microsoft Windows](https://docs.aws.amazon.com/kinesis-agent-windows/latest/userguide/what-is-kinesis-agent-windows.html). You can run this agent on fleets of Windows servers either hosted on-premises or in your AWS environment. 

![Sysmon Custom Source Architecture](./images/sysmon_arch.png)

The above illustration shows the interaction of services involved in building the custom source. We will cover the solution implementation a bit later in this post, first let us understand how you can map sysmon events streaming through Kinesis Data Firehose into the relevant OCSF classes.


## Mapping

**Overall event mapping**

|Sysmon EventId	| Event Detail | OCSF Class |
|-|-|-|
| 1 | Process creation | Process Activity |
| 2 | A process changed a file creation time | File System Activity |
| 3 | Network connection | Network Activity |
| 4 | Sysmon service state changed | Process Activity |
| 5 | Process terminated | Process Activity |
| 6 | Driver loaded | Kernel Activity |
| 7 | Image loaded | Process Activity |
| 8 | CreateRemoteThread | Network Activity |
| 9 | RawAccessRead | Memory Activity |
| 10 | ProcessAccess | Process Activity |
| 11 | FileCreate | File System Activity |
| 12 | RegistryEvent (Object create and delete) | File System Activity |
| 13 | RegistryEvent (Value Set) | File System Activity |
| 14 | RegistryEvent (Key and Value Rename) | File System Activity |
| 15 | FileCreateStreamHash | File System Activity |
| 16 | ServiceConfigurationChange | Process Activity |
| 17 | PipeEvent (Pipe Created) | File System Activity |
| 18 | PipeEvent (Pipe Connected) | File System Activity |
| 19 | WmiEvent (WmiEventFilter activity detected) | Process Activity |
| 20 | WmiEvent (WmiEventConsumer activity detected) | Process Activity |
| 21 | WmiEvent (WmiEventConsumerToFilter activity detected) | Process Activity |
| 22 | DNSEvent (DNS query) | DNS Activity |
| 23 | FileDelete (File Delete archived) | File System Activity |
| 24 | ClipboardChange (New content in the clipboard) | File System Activity |
| 25 | ProcessTampering (Process image change) | Process Activity |
| 26 | FileDeleteDetected (File Delete logged) | File System Activity |
| 27 | FileBlockExecutable | File System Activity |
| 28 | FileBlockShredding | File System Activity |
| 29 | FileExecutableDetected | File System Activity |
| 255 | Sysmon Error | Process Activity |

**Sample File System Activity event mapping**

1. Event streamed using Kinesis Data Firehose

    ```json
    {"EventId":1,
    "source_instance_id": "i-1234example56789",
    "Description":"File created:
    RuleName: technique_id=T1574.010,technique_name=Services File Permissions Weakness
    UtcTime: 2023-10-03 23:50:22.438
    ProcessGuid: {78c8aea6-5a34-651b-1900-000000005f01}
    ProcessId: 1128
    Image: C:\Windows\System32\svchost.exe
    TargetFilename: C:\Windows\ServiceState\EventLog\Data\lastalive1.dat
    CreationUtcTime: 2023-10-03 00:04:00.984
    User: NT AUTHORITY\LOCAL SERVICE"}
    ```

2. Attribute mapping for File System Activity class

    |OCSF| Raw |
    |-|-|
    | metadata.profiles| [host] |
    | metadata.version| v1.0.0-rc2 |
    | metadata.product.name| System Monitor (Sysmon) |
    | metadata.product.vendor_name| Microsoft Sysinternals |
    | metadata.product.version| v15.0 |
    | severity| Informational |
    | severity_id| 1 |
    | category_uid| 1 |
    | category_name| System Activity |
    | class_uid| 1001 |
    | class_name| File System Activity |
    | time| `<UtcTime>` |
    | activity_id| 1 |
    | actor| {'process': {'name': `<Image>`}} |
    | device| {'type_id': 6} |
    | unmapped| {'pid': `<ProcessId>`, 'uid': `<ProcessGuid>`,  'name': `<Image>`, 'user': `<User>`, 'rulename': `<RuleName>`} |
    | file| {'name': , 'type_id': '1'} |
    | type_uid| 100101 |

## Pre-requisites

1. **[AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_tutorials_basic.html) is configured your AWS environment**. AWS Organizations is an AWS account management service that provides account management and consolidated billing capabilities so you can consolidate multiple AWS accounts and manage them centrally.

2. Security Lake is activated and [delegated administrator is configured](https://docs.aws.amazon.com/security-lake/latest/userguide/multi-account-management.html).

    1. Navigate to the AWS Organizations console, and set up an organization with a [Log Archive account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/log-archive.html). The Log Archive account should be used as the delegated Security Lake administrator account where you will configure Security Lake. For more information on deploying the full complement of AWS security services in a multi-account environment, see [AWS Prescriptive Guidance | AWS Security Reference Architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html).
    2. Configure permissions for the Security Lake administrator access by using an [AWS Identity and Access Management (IAM) role](https://aws.amazon.com/iam/). This role should be used by security teams to administer Security Lake configuration, including managing custom sources.
    3. Enable Security Lake in the Region of your choice in the Log Archive account. When you configure Security Lake, you can define your collection objectives, which include log sources, the Regions that you want to collect the log sources from and the lifecycle policy you want to assign to the log sources. Security Lake uses [Amazon Simple Storage Service (Amazon S3)](https://aws.amazon.com/s3/) as the underlying storage for the log data. S3 is an object storage service offering industry-leading scalability, data availability, security, and performance. S3 is built to store and retrieve any amount of data from anywhere. Security Lake creates and configures individual S3 buckets in each Region identified in the collection objectives, in the Log Archive account.

3. Install [Kinesis Agent for Microsoft Windows](https://docs.aws.amazon.com/kinesis-agent-windows/latest/userguide/getting-started.html#getting-started-installation). There are three ways you can install the agent on Windows Operating Systems. Using [AWS Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/), helps automate the deployment and upgrade process. You can also install using a Windows installer package or using PowerShell scripts.

## Deployment

1. Sign in to the Amazon Security Lake delegated administrator account.

2. Deploy the lambda function in the `lambda` folder. ##### TODO SAM-ify

3. Navigate to AWS CloudFormation and deploy the streaming infrastructure using the CloudFormation template titled `LogIngestionInfrastructure.yaml`. The CloudFormation template produces three outputs:

    * `CustomSourceKDFStreamName`: Name of the Amazon Kinesis Data Firehose delivery stream
    * `KinesisMonitoringPutRecordAlarm`: Name of the Amazon CloudWatch alarm that monitors healthy Kinesis operation.
    * `WindowsSysmonGlueRoleARN`: Name of the IAM role created for Glue to use with custom sources.

4. Capture the outputs of the CloudFormation stack on a scratchpad.

5. In the following command, replace the placeholders as below:

    * `<GLUE_IAM_ROLE_ARN>` with the value of the CloudFormation output named `WindowsSysmonGlueRoleARN` captured in the previous step.
    * `<EXTERNAL_ID>` is an alphanumeric value you can assign to configure fine grained access control. For the windows-sysmon custom source, you can assign it any value you like. In some cases, where you are using an external product, the vendor will supply the [External ID](https://aws.amazon.com/blogs/security/how-to-use-external-id-when-granting-access-to-your-aws-resources/) to you.
    * `<AWS_IDENTITY_PRINCIPAL>` with the Security Lake delegated administrator AWS Account ID.
    * `<SECURITY_LAKE_REGION>` with the region where Security Lake is configured.

    ```bash
        aws securitylake create-custom-log-source  \
            --source-name windows-sysmon \
            --configuration crawlerConfiguration={"roleArn=<GLUE_IAM_ROLE_ARN>"},providerIdentity={"externalId=<EXTERNAL_ID>,principal=<AWS_IDENTITY_PRINCIPAL>"} \
            --event-classes FILE_ACTIVITY PROCESS_ACTIVITY \
            --region <SECURITY_LAKE_REGION>
    ```

6. Use AWS CloudShell, a browser based shell, in the Security Lake delegated administrator account to run the above command after you have replaced the placeholders.

7. Access the remote host running Microsoft Windows Operating System. This solution uses [sysmonconfig.xml](https://github.com/olafhartong/sysmon-modular/blob/master/sysmonconfig.xml) published in the [sysmon-modular](https://github.com/olafhartong/sysmon-modular) project. The project provides a modular configuration along with publishing Tactics, Techniques and Procedures (TTPs) with sysmon events to help in [TTP-based threat hunting](https://www.mitre.org/news-insights/publication/ttp-based-hunting) use cases. If you have your own curated sysmon configuration, you can also choose to use your own configuration.

8. On the remote host, update the Kinesis agent configuration file contents with the contents of `kinesis_agent_configuration.json` file from this repository. Make sure you replace `<CustomSourceKDFStreamName>` placeholder with the value of the CloudFormation output `CustomSourceKDFStreamName` from Step 3.

    ```json
    {
        "Sources": [
            {
            "Id": "Sysmon",
            "SourceType": "WindowsEventLogSource",
            "LogName": "Microsoft-Windows-Sysmon/Operational"
            }
        ],
        "Sinks": [
            {
            "Id": "SysmonLogStream",
            "SinkType": "KinesisFirehose",
            "StreamName": "<CustomSourceKDFStreamName>",
            "Region": "{env:Region}",
            "ObjectDecoration": "source_instance_id={ec2:instance-id};",
            "Format": "json"
            }
        ],
        "Pipes": [
            {
            "Id": "JsonLogSourceToFirehoseLogStream",
            "SourceRef": "Sysmon",
            "SinkRef": "SysmonLogStream"
            }
        ],
        "SelfUpdate": 0,
        "Telemetrics": { "off": "true" }
    }
    ```