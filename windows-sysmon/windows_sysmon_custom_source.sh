aws securitylake create-custom-log-source  \
   --source-name windows-sysmon \
   --configuration crawlerConfiguration={"roleArn=<GLUE_IAM_ROLE_ARN>"},providerIdentity={"externalId=CustomSourceExternalId123,principal=<AWS_IDENTITY_PRINCIPAL>"} \
   --event-classes FILE_ACTIVITY PROCESS_ACTIVITY \
   --region <SECURITY_LAKE_REGION>