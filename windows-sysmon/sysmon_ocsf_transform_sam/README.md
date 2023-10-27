# Sysmon OCSF Transformation Infrastructure

This project contains source code and supporting files for a serverless application that transforms Sysmon events into applicable Open Cybersecurity Schema Framework (OSCF) schemas. This section uses [AWS Serverless Application Model](https://aws.amazon.com/serverless/sam/) Command Line Interface (SAM CLI) which is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. 

To use the SAM CLI, you need the following tools:

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)


This project contains the following files and folders:

* `lambda`: This folder has the OCSF transformation Lambda function and its dependency list. The folder also contains the OCSF mapping configuration that the lambda function uses to perform the transformation.
* `template.yaml`: The CloudFormation template that defines the AWS resources deployed to set up the log streaming and transformation infrastructure. The application uses several AWS resources, including Lambda functions and Kinesis Data Streams. You can update the template to add AWS resources through the same deployment process that updates your application code.
* `samconfig.toml`: This file contains project level attributes for the SAM CLI.

This project deploys the following resources:

* `OCSFTransformationLambdaFunction`: The OCSF transformation lambda function and layers.
* `LogCollectionStream`: Kinesis Data Stream to collect logs from the Kinesis Agents configured in the log generating Microsoft Windows Servers.
* `KinesisAgentIAMRole`: AWS IAM role to be used by the Kinesis Agent to stream logs to the Kinesis Data Stream.

The template produces the following outputs which you will use in the next steps:

* `OCSFTransformationLambdaFunctionARN`: ARN of the OCSF Transformation Lambda Function.
* `LogCollectionStreamName`: Name of the log collection Kinesis Data Stream.
* `KinesisAgentIAMRoleARN`: ARN of the IAM role created for Kinesis agent to assume for log streaming.

## Mapping configuration

The OCSF transformation lambda function uses a [sysmon_mapping.json](./lambda/sysmon_mapping.json) file that specifies the OCSF schema each Sysmon event type should be transformed to and the mapping of Sysmon to OCSF attributes. The configuration is a sample and currently support events `1`, `5`, `11` & `23` but can easily be extended to handle additional types.

## Deployment

To build and deploy the application, run the following in your shell:

```bash
sam build
sam deploy --guided
```
The application requires the following parameters as part of the deployment:

* `ASLCustomLogSourceLocation`: The S3 location of the Amazon Security Lake custom log source used for outputting files in Parquet format (eg. my-bucket/ext/my-custom-log-source/).
* `SourceKinesisUserARNs`: A list of ARNs of the users or roles that should be able to assume the IAM Role used by the Kinesis Agent to stream logs to Kinesis Data Streams.

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
sam delete --stack-name "sysmon-ocsf-transformation-lambda"
```
