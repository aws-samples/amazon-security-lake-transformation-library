#!/usr/bin/env python3
import os
import aws_cdk as cdk
from ocsf_transformation.ocsf_transformation_stack import OcsfTransformationStack

app = cdk.App()

# Get parameters from context or environment variables
log_event_source = app.node.try_get_context("log_event_source") or os.environ.get("LOG_EVENT_SOURCE", "Both")
asl_custom_log_source_location = app.node.try_get_context("asl_custom_log_source_location") or os.environ.get("ASL_CUSTOM_LOG_SOURCE_LOCATION")
raw_log_s3_bucket_name = app.node.try_get_context("raw_log_s3_bucket_name") or os.environ.get("RAW_LOG_S3_BUCKET_NAME", "")

# Parse list parameters (comma-separated strings)
kinesis_user_arns_str = app.node.try_get_context("kinesis_user_arns") or os.environ.get("KINESIS_USER_ARNS", "")
kinesis_user_arns = [arn.strip() for arn in kinesis_user_arns_str.split(",")] if kinesis_user_arns_str else []

kinesis_encryption_key_admin_arns_str = app.node.try_get_context("kinesis_encryption_key_admin_arns") or os.environ.get("KINESIS_ENCRYPTION_KEY_ADMIN_ARNS", "")
kinesis_encryption_key_admin_arns = [arn.strip() for arn in kinesis_encryption_key_admin_arns_str.split(",")] if kinesis_encryption_key_admin_arns_str else []

# Get the stack name from context or use default
# This allows updating an existing stack by providing its name
stack_name = (
    app.node.try_get_context("stack-name") or 
    app.node.try_get_context("stack_name") or 
    "OcsfTransformationStack"
)

# Create stack with parameters
OcsfTransformationStack(
    app, 
    "OcsfTransformationStack",  # This is just the construct ID, not the actual stack name
    stack_name=stack_name,     # This is the actual CloudFormation stack name
    log_event_source=log_event_source,
    asl_custom_log_source_location=asl_custom_log_source_location,
    raw_log_s3_bucket_name=raw_log_s3_bucket_name,
    kinesis_user_arns=kinesis_user_arns,
    kinesis_encryption_key_admin_arns=kinesis_encryption_key_admin_arns,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"), 
        region=os.environ.get("CDK_DEFAULT_REGION")
    ),
    description="CDK deployment for OCSF transformation library"
)

app.synth()
