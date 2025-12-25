# infrastructure/stacks/security_stack.py
"""Security stack for Wumbo - VPC, Secrets, IAM"""

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class SecurityStack(Stack):
    """Stack for security resources - VPC, Secrets, IAM roles"""

    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = env_name

        # Create VPC with optimized NAT configuration
        self.vpc = self._create_vpc()

        # OPTIMIZATION: VPC Flow Logs only for staging/production
        if self.env_name in ["staging", "production"]:
            self._create_vpc_flow_logs()

        # VPC Endpoints - essential for all environments to access AWS services
        # Without these, services in private subnets can't reach Secrets Manager, ECR, etc.
        self._create_vpc_endpoints()

        # Create KMS key for secrets (production only to avoid circular dependencies)
        self.secrets_key = self._create_secrets_kms_key() if self.env_name == "production" else None

        # Look up existing secrets (created via scripts)
        self.plaid_secret = self._lookup_plaid_secret()
        self.aws_secret = self._lookup_aws_secret()
        self.app_secret = self._lookup_app_secret()

        # Create outputs
        self._create_outputs()

    def _get_nat_config(self) -> dict:
        """Get NAT Gateway configuration based on environment

        Returns dict with 'nat_gateways' and 'nat_gateway_provider'
        """
        configs = {
            "development": {
                "nat_gateways": 1,  # Use NAT Gateway (more reliable than NAT Instance)
                "nat_gateway_provider": None,
            },
            "staging": {
                "nat_gateways": 1,  # One NAT Gateway (not HA, but acceptable)
                "nat_gateway_provider": None,
            },
            "production": {
                "nat_gateways": 2,  # Two NAT Gateways for HA
                "nat_gateway_provider": None,
            },
        }
        return configs.get(self.env_name, configs["development"])

    def _create_vpc(self) -> ec2.Vpc:
        """Create VPC with optimized NAT configuration"""

        nat_config = self._get_nat_config()

        vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name=f"{self.env_name}-wumbo-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,  # Two AZs for redundancy
            # OPTIMIZATION: NAT configuration based on environment
            nat_gateways=nat_config["nat_gateways"],
            nat_gateway_provider=nat_config["nat_gateway_provider"],
            # Subnet configuration
            subnet_configuration=[
                # Public subnets (for ALB, NAT Gateway/Instance)
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,  # 256 IPs per subnet
                ),
                # Private subnets with egress (for ECS tasks)
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=20,  # 4096 IPs per subnet (room for scaling)
                ),
                # Isolated subnets (for RDS - no internet access)
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,  # 256 IPs per subnet
                ),
            ],
            # OPTIMIZATION: Disable default security group rules
            restrict_default_security_group=True,
        )

        return vpc

    def _create_vpc_flow_logs(self) -> None:
        """Create VPC Flow Logs for network monitoring"""

        # OPTIMIZATION: Log to CloudWatch with shorter retention
        log_group = logs.LogGroup(
            self,
            "VpcFlowLogGroup",
            log_group_name=f"/aws/vpc/{self.env_name}-wumbo-vpc",
            retention=(
                logs.RetentionDays.ONE_WEEK
                if self.env_name == "staging"
                else logs.RetentionDays.TWO_WEEKS  # Production
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # OPTIMIZATION: Only log rejected traffic (reduces costs)
        self.vpc.add_flow_log(
            "FlowLog",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(log_group),
            traffic_type=ec2.FlowLogTrafficType.REJECT,  # Only rejected traffic
        )

    def _create_vpc_endpoints(self) -> None:
        """Create VPC endpoints for AWS services"""

        # S3 Gateway Endpoint (free)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # ECR API Endpoint (for Docker pulls)
        self.vpc.add_interface_endpoint(
            "EcrApiEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
        )

        # ECR Docker Endpoint (for Docker layers)
        self.vpc.add_interface_endpoint(
            "EcrDockerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
        )

        # CloudWatch Logs Endpoint
        self.vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
        )

        # Secrets Manager Endpoint
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
        )

        # SES Endpoint (for sending emails)
        self.vpc.add_interface_endpoint(
            "SesEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SES,
        )

    def _create_secrets_kms_key(self) -> kms.Key:
        """Create KMS key for encrypting secrets"""

        key = kms.Key(
            self,
            "SecretsKey",
            description=f"KMS key for {self.env_name} Wumbo secrets",
            enable_key_rotation=True,
            # OPTIMIZATION: Destroy key in dev/staging for easier cleanup
            removal_policy=(
                RemovalPolicy.DESTROY if self.env_name != "production" else RemovalPolicy.RETAIN
            ),
            # OPTIMIZATION: Shorter pending window for dev/staging
            pending_window=Duration.days(7) if self.env_name != "production" else Duration.days(30),
        )

        # Add alias for easier identification
        kms.Alias(
            self,
            "SecretsKeyAlias",
            alias_name=f"alias/{self.env_name}-wumbo-secrets",
            target_key=key,
        )

        return key

    def _lookup_plaid_secret(self) -> secretsmanager.ISecret:
        """Look up existing Plaid credentials secret

        Expected structure:
        {
            "client_id": "plaid_client_id",
            "secret": "plaid_secret",
            "environment": "sandbox"  # or "development", "production"
        }

        Create with: ./scripts/populate-secrets.py <environment>
        """

        secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "PlaidSecret",
            secret_name=f"{self.env_name}/wumbo/plaid",
        )

        return secret

    def _lookup_aws_secret(self) -> secretsmanager.ISecret:
        """Look up existing AWS credentials secret

        Expected structure:
        {
            "access_key_id": "aws_access_key",
            "secret_access_key": "aws_secret_key",
            "region": "us-east-1"
        }

        Create with: ./scripts/populate-secrets.py <environment>
        """

        secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "AwsSecret",
            secret_name=f"{self.env_name}/wumbo/aws",
        )

        return secret

    def _lookup_app_secret(self) -> secretsmanager.ISecret:
        """Look up existing app security settings secret

        Expected structure:
        {
            "jwt_secret_key": "random_64_char_string",
            "encryption_key": "base64_fernet_key",
            "algorithm": "HS256"
        }

        Create with: ./scripts/populate-secrets.py <environment> --generate-keys
        Note: encryption_key is used for Fernet encryption of sensitive data (Plaid tokens, etc.)
        """

        secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "AppSecret",
            secret_name=f"{self.env_name}/wumbo/app-security",
        )

        return secret

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""

        # VPC outputs
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{self.env_name}-VpcId",
        )

        CfnOutput(
            self,
            "VpcCidr",
            value=self.vpc.vpc_cidr_block,
            description="VPC CIDR block",
            export_name=f"{self.env_name}-VpcCidr",
        )

        # Secret ARN outputs
        CfnOutput(
            self,
            "PlaidSecretArn",
            value=self.plaid_secret.secret_arn,
            description="Plaid secret ARN",
            export_name=f"{self.env_name}-PlaidSecretArn",
        )

        CfnOutput(
            self,
            "PlaidSecretName",
            value=self.plaid_secret.secret_name,
            description="Plaid secret name",
            export_name=f"{self.env_name}-PlaidSecretName",
        )

        CfnOutput(
            self,
            "AwsSecretArn",
            value=self.aws_secret.secret_arn,
            description="AWS credentials secret ARN",
            export_name=f"{self.env_name}-AwsSecretArn",
        )

        CfnOutput(
            self,
            "AwsSecretName",
            value=self.aws_secret.secret_name,
            description="AWS credentials secret name",
            export_name=f"{self.env_name}-AwsSecretName",
        )

        CfnOutput(
            self,
            "AppSecretArn",
            value=self.app_secret.secret_arn,
            description="App security secret ARN",
            export_name=f"{self.env_name}-AppSecretArn",
        )

        CfnOutput(
            self,
            "AppSecretName",
            value=self.app_secret.secret_name,
            description="App security secret name",
            export_name=f"{self.env_name}-AppSecretName",
        )

        # KMS key outputs (production only)
        if self.secrets_key:
            CfnOutput(
                self,
                "SecretsKmsKeyArn",
                value=self.secrets_key.key_arn,
                description="KMS key ARN for secrets",
                export_name=f"{self.env_name}-SecretsKmsKeyArn",
            )

            CfnOutput(
                self,
                "SecretsKmsKeyId",
                value=self.secrets_key.key_id,
                description="KMS key ID for secrets",
                export_name=f"{self.env_name}-SecretsKmsKeyId",
            )
