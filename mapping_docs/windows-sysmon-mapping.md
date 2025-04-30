# Microsoft Sysinternals System Monitor (Sysmon)

**OCSF Classes**: FILE_ACTIVITY, PROCESS_ACTIVITY, DNS_ACTIVITY, NETWORK_ACTIVITY

## Mapping

**Overall event mapping**

|Sysmon EventId	| Event Detail | OCSF Class |
|-|-|-|
| 1 | Process creation | PROCESS_ACTIVITY |
| 2 | A process changed a file creation time | FILE_ACTIVITY |
| 3 | Network connection | NETWORK_ACTIVITY |
| 4 | Sysmon service state changed | PROCESS_ACTIVITY |
| 5 | Process terminated | PROCESS_ACTIVITY |
| 6 | Driver loaded | KERNEL_ACTIVITY |
| 7 | Image loaded | PROCESS_ACTIVITY |
| 8 | CreateRemoteThread | NETWORK_ACTIVITY |
| 9 | RawAccessRead | MEMORY_ACTIVITY |
| 10 | ProcessAccess | PROCESS_ACTIVITY |
| 11 | FileCreate | FILE_ACTIVITY |
| 12 | RegistryEvent (Object create and delete) | FILE_ACTIVITY |
| 13 | RegistryEvent (Value Set) | FILE_ACTIVITY |
| 14 | RegistryEvent (Key and Value Rename) | FILE_ACTIVITY |
| 15 | FileCreateStreamHash | FILE_ACTIVITY |
| 16 | ServiceConfigurationChange | PROCESS_ACTIVITY |
| 17 | PipeEvent (Pipe Created) | FILE_ACTIVITY |
| 18 | PipeEvent (Pipe Connected) | FILE_ACTIVITY |
| 19 | WmiEvent (WmiEventFilter activity detected) | PROCESS_ACTIVITY |
| 20 | WmiEvent (WmiEventConsumer activity detected) | PROCESS_ACTIVITY |
| 21 | WmiEvent (WmiEventConsumerToFilter activity detected) | PROCESS_ACTIVITY |
| 22 | DNSEvent (DNS query) | DNS_ACTIVITY |
| 23 | FileDelete (File Delete archived) | FILE_ACTIVITY |
| 24 | ClipboardChange (New content in the clipboard) | FILE_ACTIVITY |
| 25 | ProcessTampering (Process image change) | PROCESS_ACTIVITY |
| 26 | FileDeleteDetected (File Delete logged) | FILE_ACTIVITY |
| 27 | FileBlockExecutable | FILE_ACTIVITY |
| 28 | FileBlockShredding | FILE_ACTIVITY |
| 29 | FileExecutableDetected | FILE_ACTIVITY |
| 255 | Sysmon Error | PROCESS_ACTIVITY |

**Sample File System Activity event mapping**

1. Event streamed using Kinesis Data Streams

    ```
    {"EventId":"1",
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

    |OCSF|Raw|
    |-|-|
    | metadata.profiles | [host] |
    | metadata.version | v1.1.0 |
    | metadata.product.name | System Monitor (Sysmon) |
    | metadata.product.vendor_name | Microsoft Sysinternals |
    | metadata.product.version | v15.0 |
    | severity | Informational |
    | severity_id | 1 |
    | category_uid | 1 |
    | category_name | System Activity |
    | class_uid | 1001 |
    | class_name | File System Activity |
    | time | `<UtcTime>` |
    | activity_id | 1 |
    | actor | {'process': {'name': `<Image>`}} |
    | device | {'type_id': 6} |
    | unmapped | {'pid': `<ProcessId>`, 'uid': `<ProcessGuid>`,  'name': `<Image>`, 'user': `<User>`, 'rulename': `<RuleName>`} |
    | file | { 'name': `<TargetFilename>`, type_id: 1 } |
    | type_uid | 100101 |

    You can follow the same process to map the remaining classes. The [windows_sysmon.json](./transformation_function/mappings/windows_sysmon.json) defined in this documentation maps four events across two OCSF classes (FILE_ACTIVITY and PROCESS_ACTIVITY). You can use the same method to configure mapping for NETWORK_ACTIVITY and DNS_ACTIVITY sysmon events.
