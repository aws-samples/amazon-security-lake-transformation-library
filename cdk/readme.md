# OCSF Transformation CDK

This CDK project converts the SAM template for OCSF transformation into a CDK application. It provides the flexibility to choose between S3 bucket approach, Kinesis approach, or both, while being compatible with existing SAM deployments.

## Features

- **Unified Lambda Function**: Single Lambda function with all permissions for both S3 and Kinesis approaches
- **Encrypted Kinesis Stream**: Secure stream with KMS encryption
- **Flexible Deployment**: Choose between S3 bucket, Kinesis stream, or both
- **SAM Compatibility**: Compatible with existing SAM deployments

## Getting Started

### Prerequisites

- AWS CDK v2 installed
- Python 3.8 or higher
- AWS CLI configured with appropriate credentials

### Installation

1. Clone this repository
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
pip install -r requirements.txt
```

3. Make sure the transformation-function directory is present in the parent directory

### Directory Structure

```
amazon-security-lake-transformation-library/
├── transformation-function/         # Lambda function code directory
│   ├── app.py                       # Lambda handler
│   └── ...                          # Other Lambda function files
└── cdk/                             # CDK application directory
    ├── app.py                       # CDK application entry point
    ├── ocsf_transformation/
    │   ├── __init__.py
    │   └── ocsf_transformation_stack.py # Main stack definition
    ├── requirements.txt
    ├── setup.py
    └── README.md
```

## Deployment

You can provide parameters in different ways:

### Using CDK Context Parameters

```bash
cdk deploy \
  --context log_event_source=Both \
  --context asl_bucket_location=my_bucket/ext/my_custom_source \
  --context raw_log_s3_bucket_name=my-existing-bucket \
  --context add_s3_event_notification=true \
  --context kinesis_user_arns="arn:aws:iam::123456789012:user/kinesis-user1,arn:aws:iam::123456789012:user/kinesis-user2" \
  --context kinesis_encryption_key_admin_arns="arn:aws:iam::123456789012:user/key-admin" \
  --context stack_name="my-ocsf-stack-name"
```

### Using Environment Variables

```bash
export LOG_EVENT_SOURCE=Both
export ASL_BUCKET_LOCATION=my_bucket/ext/my_custom_source
export RAW_LOG_S3_BUCKET_NAME=my-existing-bucket
export ADD_S3_EVENT_NOTIFICATION=true
export KINESIS_USER_ARNS="arn:aws:iam::123456789012:user/kinesis-user1,arn:aws:iam::123456789012:user/kinesis-user2"
export KINESIS_ENCRYPTION_KEY_ADMIN_ARNS="arn:aws:iam::123456789012:user/key-admin"

cdk deploy
```

## Parameters

| Parameter | Description | Allowed Values | Default |
|-----------|-------------|----------------|---------|
| `log_event_source` | Source of raw logs for the custom source | `S3Bucket`, `KinesisDataStream`, `Both` | `Both` |
| `asl_bucket_location` | Amazon Security Lake custom source S3 location | String (required) | - |
| `raw_log_s3_bucket_name` | Name of the existing S3 bucket for raw logs (if empty, creates new bucket) | String | `""` |
| `add_s3_event_notification` | Add S3 event notification to existing bucket when using an existing bucket | `true`, `false` | `false` |
| `kinesis_user_arns` | ARNs of IAM identities for Kinesis Agent (comma-separated list) | List of ARNs | `[]` |
| `kinesis_encryption_key_admin_arns` | ARNs of IAM identities to administer the CMK (comma-separated list) | List of ARNs | `[]` |
| `stack_name` | Name of the CloudFormation stack | String | `OcsfTransformationStack` |

## Working with Existing S3 Buckets

When using an existing S3 bucket with the `raw_log_s3_bucket_name` parameter, you can choose whether to add the S3 event notification for SQS:

- **With notifications (new)**: Set `add_s3_event_notification=true` to automatically configure the bucket to send notifications to the SQS queue for *.log.gz objects
- **Without notifications**: Set `add_s3_event_notification=false` (default) if you already have notifications set up or want to configure them manually

## Updating Existing SAM Deployments

If you have an existing SAM deployment, you can update it using this CDK by:

1. Extract the parameters from your existing CloudFormation stack:
   ```bash
   aws cloudformation describe-stacks --stack-name YourExistingSAMStack
   ```

2. Use the same parameters with the CDK deployment
3. Use the same stack name to update the existing stack:
   ```bash
   cdk deploy --context stack_name=YourExistingSAMStack
   ```

## Additional Configuration

### For S3 Only

To use only the S3 bucket approach:

```bash
cdk deploy --context log_event_source=S3Bucket
```

### For Kinesis Only

To use only the Kinesis approach:

```bash
cdk deploy --context log_event_source=KinesisDataStream
```

## Contributing

Contributions are welcome. Please feel free to submit a Pull Request.
