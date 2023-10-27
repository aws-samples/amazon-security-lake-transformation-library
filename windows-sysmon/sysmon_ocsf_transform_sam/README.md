# Sysmon OCSF Transformation Lambda

This project contains source code and supporting files for a serverless application that transforms Sysmon events into applicable Open Cybersecurity Schema Framework (OSCF) schemas.

The application will deploy:
- a Kinesis Stream that Kinesis agents for Windows can send Sysmon events to
- an IAM role Kinesis agents can use to interact with the Kinesis Stream
- a Lambda function that reads Sysmon events from the Kinesis Stream, converts them

## Configuration
The lambda uses a `sysmon_mapping.json` file that specifies the OCSF schema each Sysmon event type should be transformed to as well as the the mapping of Sysmon to OCSF fields. The config currently support events `1`, `5`, `11` & `23` but can easily be extended to handle addition types.

## Deploy the application

To build and deploy the application, run the following in your shell:

```bash
sam build
sam deploy --guided
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
sam delete --stack-name "sysmon-ocsf-transform-lambda"
```
