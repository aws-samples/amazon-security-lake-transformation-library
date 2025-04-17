from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_kinesis as kinesis,
    aws_kms as kms,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as lambda_event_sources,
    Duration,
    RemovalPolicy,
    CfnOutput,
    CfnResource,
)
from constructs import Construct
from aws_cdk import CfnDeletionPolicy


class OcsfTransformationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        # Extract our custom properties from kwargs
        log_event_source = kwargs.pop("log_event_source", "All")
        asl_bucket_location = kwargs.pop("asl_bucket_location")
        raw_log_s3_bucket_name = kwargs.pop("raw_log_s3_bucket_name", None)
        kinesis_user_arns = kwargs.pop("kinesis_user_arns", [])
        kinesis_encryption_key_admin_arns = kwargs.pop("kinesis_encryption_key_admin_arns", [])
        add_s3_event_notification = kwargs.pop("add_s3_event_notification", False)

        super().__init__(scope, construct_id, **kwargs)

        # Define conditions like in the SAM template
        is_s3_backed = log_event_source in ["S3Bucket", "All"]
        is_kinesis_backed = log_event_source in ["KinesisDataStream", "All"]
        create_kinesis_agent_role = is_kinesis_backed and len(kinesis_user_arns) > 0
        create_staging_s3_bucket = is_s3_backed and not raw_log_s3_bucket_name

        # Create a single transformation Lambda execution role with all permissions
        # Always use the unified role ID regardless of deployment type
        transformation_lambda_role = iam.Role(
            self, "TransformationLambdaExecutionRole",
            role_name=f"{self.stack_name.lower()}-LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        # Always use the unified role logical ID
        (transformation_lambda_role.node.default_child).override_logical_id("TransformationLambdaExecutionRole")

        # Add policies for both S3 and Kinesis permissions, regardless of deployment type
        # This ensures the role has all necessary permissions for any combination
        
        # Common policies
        transformation_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="LogGroupCreate",
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogGroup"],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:*"]
            )
        )

        transformation_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="LogsWrite",
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/*:*"]
            )
        )
        
        transformation_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3Write",
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject", "s3:PutObjectAcl"],
                resources=[f"arn:aws:s3:::{asl_bucket_location}/*"]
            )
        )
        
        transformation_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="TracingWithXRay",
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                    "xray:GetSamplingStatisticSummaries"
                ],
                resources=["*"]
            )
        )
        
        # Add Kinesis permissions always
        transformation_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="KinesisReadWrite",
                effect=iam.Effect.ALLOW,
                actions=[
                    "kinesis:PutRecord",
                    "kinesis:PutRecords",
                    "kinesis:DescribeStream",
                    "kinesis:DescribeStreamSummary",
                    "kinesis:GetRecords",
                    "kinesis:GetShardIterator",
                    "kinesis:ListShards",
                    "kinesis:ListStreams",
                    "kinesis:SubscribeToShard"
                ],
                resources=["*"]
            )
        )
        
        transformation_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="KMSAccess",
                effect=iam.Effect.ALLOW,
                actions=["kms:Decrypt"],
                resources=["*"]
            )
        )

        # S3-specific resources
        if is_s3_backed:
            # Create SQS queue
            sqs_queue = sqs.Queue(
                self, "SqsQueue",
                visibility_timeout=Duration.seconds(1200)
            )
            
            # Ensure SQS queue has the same logical ID as in the SAM template
            (sqs_queue.node.default_child).override_logical_id("SqsQueue")
            
            # Create or use existing S3 bucket
            if create_staging_s3_bucket:
                # Create a new bucket
                staging_log_bucket = s3.Bucket(
                    self, "StagingLogBucket",
                    bucket_name=f"{self.stack_name.lower()}-staging-log-bucket",
                    removal_policy=RemovalPolicy.RETAIN,
                    enforce_ssl=True
                )
                # Ensure S3 bucket has the same logical ID as in the SAM template
                (staging_log_bucket.node.default_child).override_logical_id("StagingLogBucket")
                
                log_bucket = staging_log_bucket
                
                # Add bucket policy for AWS Logs Delivery
                bucket_policy = staging_log_bucket.add_to_resource_policy(
                    iam.PolicyStatement(
                        sid="AWSLogDeliveryWrite",
                        effect=iam.Effect.ALLOW,
                        actions=["s3:PutObject"],
                        resources=[staging_log_bucket.arn_for_objects("*")],
                        principals=[iam.ServicePrincipal("delivery.logs.amazonaws.com")],
                        conditions={"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
                    )
                )

                staging_log_bucket.add_to_resource_policy(
                    iam.PolicyStatement(
                        sid="AWSLogDeliveryAclCheck",
                        effect=iam.Effect.ALLOW,
                        actions=["s3:GetBucketAcl"],
                        resources=[staging_log_bucket.bucket_arn],
                        principals=[iam.ServicePrincipal("delivery.logs.amazonaws.com")]
                    )
                )

                # Get the CFN representation of the bucket policy
                bucket_policy_cfn = staging_log_bucket.policy.node.default_child
                # Override logical ID to match SAM template
                bucket_policy_cfn.override_logical_id("StagingLogBucketPolicy")

                # Add S3 notification for SQS
                staging_log_bucket.add_event_notification(
                    s3.EventType.OBJECT_CREATED_PUT,
                    s3n.SqsDestination(sqs_queue),
                    s3.NotificationKeyFilter(suffix=".log.gz")
                )
            else:
                # Use existing bucket
                log_bucket = s3.Bucket.from_bucket_name(
                    self, "ExistingRawLogBucket", 
                    bucket_name=raw_log_s3_bucket_name
                )
                if add_s3_event_notification:
                    # Add S3 notification for SQS
                    log_bucket.add_event_notification(
                        s3.EventType.OBJECT_CREATED_PUT,
                        s3n.SqsDestination(sqs_queue),
                        s3.NotificationKeyFilter(suffix=".log.gz")
                    )

            # Add S3-specific policies to the Lambda role
            transformation_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    sid="S3Read",
                    effect=iam.Effect.ALLOW,
                    actions=["s3:GetObject*"],
                    resources=[f"{log_bucket.bucket_arn}/*"]
                )
            )

            transformation_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    sid="SQSTrigger",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sqs:DeleteMessage",
                        "sqs:GetQueueAttributes",
                        "sqs:ReceiveMessage"
                    ],
                    resources=[sqs_queue.queue_arn]
                )
            )

        # Kinesis-specific resources
        if is_kinesis_backed:
            # Create Kinesis Agent IAM role if needed
            if create_kinesis_agent_role:
                kinesis_agent_role = iam.Role(
                    self, "KinesisAgentIAMRole",
                    role_name=f"{self.stack_name.lower()}-KinesisAgentRole",
                    assumed_by=iam.CompositePrincipal(
                        *[iam.ArnPrincipal(arn) for arn in kinesis_user_arns]
                    )
                )
                # Use the same logical ID as in the SAM template
                (kinesis_agent_role.node.default_child).override_logical_id("KinesisAgentIAMRole")
                
                kinesis_agent_role.add_to_policy(
                    iam.PolicyStatement(
                        sid="KinesisWrite",
                        effect=iam.Effect.ALLOW,
                        actions=["kinesis:PutRecord", "kinesis:PutRecords"],
                        resources=["*"]
                    )
                )

                kinesis_agent_role.add_to_policy(
                    iam.PolicyStatement(
                        sid="KMSAccess",
                        effect=iam.Effect.ALLOW,
                        actions=["kms:GenerateDataKey"],
                        resources=["*"]
                    )
                )

            # Determine which key to use for Kinesis Stream
            # If no admin ARNs provided, use AWS managed key (like in SAM template)
            use_aws_managed_key = len(kinesis_encryption_key_admin_arns) == 0

            if use_aws_managed_key:
                # Create Kinesis stream with AWS managed key
                log_collection_stream = kinesis.Stream(
                    self, "LogCollectionStream",
                    shard_count=1,
                    encryption=kinesis.StreamEncryption.MANAGED
                )
                # Use the same logical ID as in the SAM template
                (log_collection_stream.node.default_child).override_logical_id("LogCollectionStream")
            else:
                # Create initial policy statements
                policy_statements = [
                    iam.PolicyStatement(
                        sid="Allow IAM access delegation",
                        effect=iam.Effect.ALLOW,
                        principals=[iam.ArnPrincipal(f"arn:aws:iam::{self.account}:root")],
                        actions=["kms:*"],
                        resources=["*"]
                    ),
                    iam.PolicyStatement(
                        sid="Allow access to key administrators",
                        effect=iam.Effect.ALLOW,
                        principals=[iam.ArnPrincipal(arn) for arn in kinesis_encryption_key_admin_arns],
                        actions=[
                            "kms:Create*", "kms:Describe*", "kms:Enable*", "kms:List*",
                            "kms:Put*", "kms:Update*", "kms:Revoke*", "kms:Disable*",
                            "kms:Get*", "kms:Delete*", "kms:TagResource", "kms:UntagResource",
                            "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion"
                        ],
                        resources=["*"]
                    ),
                ]
                
                # Create the KMS key to represent the existing resource in the stack
                kinesis_stream_key = kms.Key(
                    self, "KinesisStreamKey",
                    enable_key_rotation=True,
                    policy=iam.PolicyDocument(statements=policy_statements)
                )

                # Use the same logical ID as in the SAM template
                (kinesis_stream_key.node.default_child).override_logical_id("KinesisStreamKey")

                kinesis_stream_key.grant_decrypt(transformation_lambda_role)
                
                # Add Kinesis agent access to key policy if role was created
                if create_kinesis_agent_role:
                    kinesis_stream_key.add_to_resource_policy(
                        iam.PolicyStatement(
                            sid="Allow access to generate data key",
                            effect=iam.Effect.ALLOW,
                            principals=[iam.ArnPrincipal(f"arn:aws:iam::{self.account}:role/{self.stack_name.lower()}-KinesisAgentRole")],
                            actions=["kms:GenerateDataKey"],
                            resources=["*"]
                        )
                    )

                # Create encrypted Kinesis stream with custom key
                log_collection_stream = kinesis.Stream(
                    self, "CMKEncryptedLogCollectionStream",
                    shard_count=1,
                    encryption=kinesis.StreamEncryption.KMS,
                    encryption_key=kinesis_stream_key
                )
                # Use the same logical ID as in the SAM template
                (log_collection_stream.node.default_child).override_logical_id("CMKEncryptedLogCollectionStream")


        # Create the unified transformation Lambda function with a unified logical ID
        lambda_function = lambda_.Function(
            self, "TransformationLambdaFunction",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="app.lambda_handler",
            code=lambda_.Code.from_asset("../transformation_function/"),
            role=transformation_lambda_role,
            tracing=lambda_.Tracing.ACTIVE,
            reserved_concurrent_executions=10,
            timeout=Duration.seconds(10),
            environment={
                "SEC_LAKE_BUCKET": asl_bucket_location,
                "DEBUG": "false"
            },
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "AWSSDKPandasLayer",
                    f"arn:aws:lambda:{self.region}:336392948345:layer:AWSSDKPandas-Python310:5"
                )
            ]
        )

        # Always use "TransformationLambdaFunction" as the logical ID for the Lambda function
        (lambda_function.node.default_child).override_logical_id("TransformationLambdaFunction")

        # Add event sources to Lambda based on selected approach
        if is_s3_backed:
            lambda_event_source = lambda_event_sources.SqsEventSource(
                sqs_queue,
                batch_size=10
            )
            lambda_function.add_event_source(lambda_event_source)

        if is_kinesis_backed:
            lambda_event_source = lambda_event_sources.KinesisEventSource(
                log_collection_stream,
                batch_size=100,
                starting_position=lambda_.StartingPosition.LATEST
            )
            lambda_function.add_event_source(lambda_event_source)

        # Define outputs - use a unified output name for the Lambda function
        CfnOutput(
            self, "TransformationLambdaFunctionARN",
            description="OCSF Transformation Lambda Function ARN",
            value=lambda_function.function_arn
        )

        # Additional outputs for created resources
        if is_s3_backed and create_staging_s3_bucket:
            CfnOutput(
                self, "StagingLogBucketARN",
                description="Name of the bucket for temporary log storage",
                value=staging_log_bucket.bucket_arn
            )

        if is_kinesis_backed:
            if use_aws_managed_key:
                CfnOutput(
                    self, "LogCollectionStreamName",
                    description="Name of the log collection Kinesis Stream",
                    value=log_collection_stream.stream_name
                )
            else:
                CfnOutput(
                    self, "CMKEncryptedLogCollectionStreamName",
                    description="Name of the log collection Kinesis Stream",
                    value=log_collection_stream.stream_name
                )

            if create_kinesis_agent_role:
                CfnOutput(
                    self, "KinesisAgentIAMRoleARN",
                    description="ARN of the IAM role created for Kinesis agent to assume for log streaming",
                    value=kinesis_agent_role.role_arn
                )