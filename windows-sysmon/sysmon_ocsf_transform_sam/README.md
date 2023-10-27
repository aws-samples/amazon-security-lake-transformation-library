# Sysmon OCSF Transformation Lambda

This project contains source code and supporting files for a serverless application that transforms Sysmon events into applicable Open Cybersecurity Schema Framework (OSCF) schemas.

The application will deploy:
- a Kinesis Data Stream that Kinesis agents for Windows can send Sysmon events to
- an IAM role Kinesis agents can use to interact with the Kinesis Data Stream
- a Lambda function that reads Sysmon events from the Kinesis Data Stream, transforms them based on the [sysmon_mapping.json](./lambda/sysmon_mapping.json) configuration file and then outputs the events in Parquet format into an S3 bucket set up as a custom log source for Amazon Security Lake.

## Configuration
The lambda uses a [sysmon_mapping.json](./lambda/sysmon_mapping.json) file that specifies the OCSF schema each Sysmon event type should be transformed to as well as the the mapping of Sysmon to OCSF fields. The config currently support events `1`, `5`, `11` & `23` but can easily be extended to handle addition types.

## Deploy the application

To build and deploy the application, run the following in your shell:

```bash
sam build
sam deploy --guided
```
The application requires the following parameters as part of the deploy step:
- **ASLCustomLogSourceLocation** - the S3 location of the Amazon Security Lake custom log source used for outputting files in Parquet format (eg. my-bucket/ext/my-custom-log-source/)
- **SourceKinesisUserARNs** - a list of ARNs of the users or roles that should be able to assume the IAM Role used to interact with Kinesis

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
sam delete --stack-name "sysmon-ocsf-transform-lambda"
```
