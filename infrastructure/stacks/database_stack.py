"""Database stack for Wumbo - RDS PostgreSQL"""

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class DatabaseStack(Stack):
    """Stack for RDS PostgreSQL database"""

    def __init__(
        self, scope: Construct, construct_id: str, vpc: ec2.IVpc, env_name: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = env_name
        self.vpc = vpc

        # Create database credentials secret
        self.database_secret = self._create_database_secret()

        # Create database security group
        self.security_group = self._create_security_group()

        # Create parameter group
        self.parameter_group = self._create_parameter_group()

        # Create subnet group
        self.subnet_group = self._create_subnet_group()

        # Create database instance
        self.database = self._create_database()

        # Create outputs
        self._create_outputs()

    def _create_database_secret(self) -> secretsmanager.Secret:
        """Create Secrets Manager secret for database credentials"""
        secret = secretsmanager.Secret(
            self,
            "DatabaseSecret",
            secret_name=f"{self.env_name}/wumbo/database",
            description="Database credentials for Wumbo",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "wumbo_admin"}',
                generate_string_key="password",
                exclude_punctuation=True,
                include_space=False,
                password_length=32,
            ),
            # OPTIMIZATION: Remove secret after 7 days in dev/staging
            removal_policy=(
                RemovalPolicy.DESTROY if self.env_name != "production" else RemovalPolicy.RETAIN
            ),
        )

        return secret

    def _create_security_group(self) -> ec2.SecurityGroup:
        """Create security group for RDS instance"""
        security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS PostgreSQL instance",
            allow_all_outbound=False,  # OPTIMIZATION: Restrict outbound traffic
        )

        # Inbound rules will be added by compute stack

        return security_group

    def _get_instance_type(self) -> ec2.InstanceType:
        """Get optimized instance type based on environment

        Uses Graviton (ARM) instances for 20% cost savings
        """
        instance_map = {
            "development": ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO  # t4g.micro
            ),
            "staging": ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL  # t4g.small
            ),
            "production": ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,  # t4g.small (start small)
                ec2.InstanceSize.SMALL,  # Can scale to MEDIUM if needed
            ),
        }
        return instance_map.get(self.env_name, instance_map["development"])

    def _get_allocated_storage(self) -> int:
        """Get allocated storage in GB based on environment"""
        storage_map = {
            "development": 20,  # Minimum GP3
            "staging": 30,
            "production": 50,  # Start smaller, can scale up
        }
        return storage_map.get(self.env_name, 20)

    def _get_max_allocated_storage(self) -> int:
        """Get maximum storage for auto-scaling in GB"""
        max_storage_map = {
            "development": 30,  # Limited growth in dev
            "staging": 100,
            "production": 500,  # Can auto-scale to 500GB
        }
        return max_storage_map.get(self.env_name, 30)

    def _get_backup_retention(self) -> Duration:
        """Get backup retention period based on environment"""
        retention_map = {
            "development": Duration.days(1),  # Minimal for dev
            "staging": Duration.days(3),
            "production": Duration.days(7),
        }
        return retention_map.get(self.env_name, Duration.days(1))

    def _get_preferred_backup_window(self) -> str:
        """Get preferred backup window (UTC)"""
        # 3-4 AM UTC = 10-11 PM EST (low traffic time)
        return "03:00-04:00"

    def _get_preferred_maintenance_window(self) -> str:
        """Get preferred maintenance window (UTC)"""
        # Sunday 4-5 AM UTC = Saturday 11 PM - 12 AM EST
        return "sun:04:00-sun:05:00"

    def _create_parameter_group(self) -> rds.ParameterGroup:
        """Create RDS parameter group with optimized settings"""
        parameter_group = rds.ParameterGroup(
            self,
            "DatabaseParameterGroup",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            description=f"Parameter group for {self.env_name} Wumbo",
            parameters={
                # OPTIMIZATION: Memory and connection settings
                "shared_buffers": "{DBInstanceClassMemory/32768}",  # ~25% of RAM
                "effective_cache_size": "{DBInstanceClassMemory/16384}",  # ~50% of RAM
                # Memory parameters must be in kB (kilobytes)
                "maintenance_work_mem": (
                    "65536" if self.env_name == "development" else "262144"
                ),  # 64MB or 256MB
                "work_mem": "4096" if self.env_name == "development" else "16384",  # 4MB or 16MB
                # OPTIMIZATION: Connection limits based on instance size
                "max_connections": "50" if self.env_name == "development" else "100",
                # OPTIMIZATION: Reduce checkpoint frequency for dev
                "checkpoint_timeout": "900" if self.env_name == "development" else "600",
                "checkpoint_completion_target": "0.9",
                # Query optimization
                "random_page_cost": "1.1",  # Optimized for SSD
                "effective_io_concurrency": "200",
                # OPTIMIZATION: Logging - minimal in dev, detailed in prod
                "log_min_duration_statement": "1000" if self.env_name == "development" else "500",
                "log_connections": "0" if self.env_name == "development" else "1",
                "log_disconnections": "0" if self.env_name == "development" else "1",
                # Auto-vacuum tuning
                "autovacuum_max_workers": "2" if self.env_name == "development" else "3",
                "autovacuum_naptime": "60",
            },
        )

        return parameter_group

    def _create_subnet_group(self) -> rds.SubnetGroup:
        """Create RDS subnet group"""
        subnet_group = rds.SubnetGroup(
            self,
            "DatabaseSubnetGroup",
            description=f"Subnet group for {self.env_name} Wumbo database",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED  # OPTIMIZATION: Use isolated subnets
            ),
            removal_policy=(
                RemovalPolicy.DESTROY if self.env_name != "production" else RemovalPolicy.RETAIN
            ),
        )

        return subnet_group

    def _create_database(self) -> rds.DatabaseInstance:
        """Create RDS PostgreSQL instance with optimized configuration"""

        # OPTIMIZATION: CloudWatch log exports only for production
        cloudwatch_logs_exports = (
            ["postgresql", "upgrade"]
            if self.env_name == "production"
            else []  # Save on log storage for dev/staging
        )

        database = rds.DatabaseInstance(
            self,
            "Database",
            instance_identifier=f"{self.env_name}-wumbo-db",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            instance_type=self._get_instance_type(),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.security_group],
            credentials=rds.Credentials.from_secret(self.database_secret),
            database_name="wumbo",
            parameter_group=self.parameter_group,
            subnet_group=self.subnet_group,
            # OPTIMIZATION: Storage configuration with GP3
            allocated_storage=self._get_allocated_storage(),
            max_allocated_storage=self._get_max_allocated_storage(),  # Enable storage auto-scaling
            storage_type=rds.StorageType.GP3,
            # Note: IOPS and throughput cannot be customized for storage < 400 GB
            # GP3 defaults: 3000 IOPS, 125 MB/s throughput (included free)
            storage_encrypted=True,
            # OPTIMIZATION: Backup configuration
            backup_retention=self._get_backup_retention(),
            preferred_backup_window=self._get_preferred_backup_window(),
            copy_tags_to_snapshot=True,
            delete_automated_backups=self.env_name != "production",
            # OPTIMIZATION: Maintenance window
            preferred_maintenance_window=self._get_preferred_maintenance_window(),
            auto_minor_version_upgrade=True,
            # OPTIMIZATION: Multi-AZ only for production
            multi_az=self.env_name == "production",
            # OPTIMIZATION: Public access - never allow
            publicly_accessible=False,
            # OPTIMIZATION: Performance Insights - only for production
            enable_performance_insights=self.env_name == "production",
            performance_insight_retention=(
                rds.PerformanceInsightRetention.DEFAULT  # 7 days
                if self.env_name == "production"
                else None
            ),
            # OPTIMIZATION: Monitoring interval
            monitoring_interval=(
                Duration.seconds(60)
                if self.env_name == "production"
                else Duration.seconds(0)  # Disable enhanced monitoring for dev/staging
            ),
            # OPTIMIZATION: CloudWatch logs
            cloudwatch_logs_exports=cloudwatch_logs_exports,
            cloudwatch_logs_retention=(
                logs.RetentionDays.TWO_WEEKS
                if self.env_name == "production"
                else logs.RetentionDays.THREE_DAYS
            ),
            # OPTIMIZATION: Deletion protection only for production
            deletion_protection=self.env_name == "production",
            removal_policy=(
                RemovalPolicy.SNAPSHOT
                if self.env_name == "production"
                else RemovalPolicy.DESTROY  # Allow easy cleanup in dev/staging
            ),
        )

        return database

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=self.database.db_instance_endpoint_address,
            description="Database endpoint address",
            export_name=f"{self.env_name}-DatabaseEndpoint",
        )

        CfnOutput(
            self,
            "DatabasePort",
            value=self.database.db_instance_endpoint_port,
            description="Database port",
            export_name=f"{self.env_name}-DatabasePort",
        )

        CfnOutput(
            self,
            "DatabaseSecretArn",
            value=self.database_secret.secret_arn,
            description="Database credentials secret ARN",
            export_name=f"{self.env_name}-DatabaseSecretArn",
        )

        CfnOutput(
            self,
            "DatabaseName",
            value="wumbo",
            description="Database name",
            export_name=f"{self.env_name}-DatabaseName",
        )
