"""Compute stack for Wumbo - Backend API and Celery services"""

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_servicediscovery as servicediscovery
from constructs import Construct


class ComputeStack(Stack):
    """Stack for ECS services (Backend API, Celery Worker, Celery Beat)"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        database_secret: secretsmanager.ISecret,
        plaid_secret: secretsmanager.ISecret,
        aws_secret: secretsmanager.ISecret,
        app_secret: secretsmanager.ISecret,
        database_security_group: ec2.ISecurityGroup,
        cache_security_group: ec2.ISecurityGroup,
        redis_endpoint: str,
        redis_port: str,
        env_name: str,
        certificate: acm.ICertificate = None,
        hosted_zone: route53.IHostedZone = None,
        api_subdomain: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = vpc
        self.database_secret = database_secret
        self.plaid_secret = plaid_secret
        self.aws_secret = aws_secret
        self.app_secret = app_secret
        self.database_security_group = database_security_group
        self.cache_security_group = cache_security_group
        self.redis_endpoint = redis_endpoint
        self.redis_port = redis_port
        self.env_name = env_name
        self.certificate = certificate
        self.hosted_zone = hosted_zone
        self.api_subdomain = api_subdomain

        # Create ECS cluster
        self.cluster = self._create_ecs_cluster()

        # Create Cloud Map namespace for service discovery
        self.namespace = servicediscovery.PrivateDnsNamespace(
            self,
            "ServiceDiscoveryNamespace",
            name=f"{self.env_name}.wumbo.local",
            vpc=self.vpc,
            description=f"Service discovery namespace for {self.env_name} environment",
        )

        # Create security groups
        self.backend_security_group = self._create_backend_security_group()
        self.worker_security_group = self._create_worker_security_group()
        self.beat_security_group = self._create_beat_security_group()
        self.migration_security_group = self._create_migration_security_group()
        self.alb_security_group = self._create_alb_security_group()

        # Create ALB for backend API
        self.alb = self._create_application_load_balancer()

        # Create target group for backend
        self.backend_target_group = self._create_backend_target_group()

        # Create ALB listener
        self._create_alb_listener()

        # Create Backend API service
        self.backend_service = self._create_backend_service()

        # Create Celery Worker service
        self.worker_service = self._create_worker_service()

        # Create Celery Beat service
        self.beat_service = self._create_beat_service()

        # Create migration task definition (not a service - run on demand)
        self.migration_task_definition = self._create_migration_task_definition()

        # Configure security group connections
        self._configure_security_group_connections()

        # Create Route53 A records (if DNS is enabled)
        self._create_route53_records()

        # Create outputs
        self._create_outputs()

    def _create_ecs_cluster(self) -> ecs.Cluster:
        """Create ECS cluster for services"""
        cluster = ecs.Cluster(
            self,
            "FamilyBudgetCluster",
            cluster_name=f"{self.env_name}-wumbo-cluster",
            vpc=self.vpc,
            # OPTIMIZATION: Only enable Container Insights for production
            container_insights=self.env_name == "production",
        )

        return cluster

    def _create_backend_security_group(self) -> ec2.SecurityGroup:
        """Create security group for Backend API ECS service"""
        security_group = ec2.SecurityGroup(
            self,
            "BackendSecurityGroup",
            vpc=self.vpc,
            description="Security group for Backend API ECS service",
            allow_all_outbound=True,
        )

        # Allow connection to database
        security_group.connections.allow_to(
            self.database_security_group, ec2.Port.tcp(5432), "Backend to database"
        )

        # Allow connection to Redis
        security_group.connections.allow_to(
            self.cache_security_group, ec2.Port.tcp(6379), "Backend to Redis"
        )

        # Allow metrics scraping from VPC (for Prometheus)
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(8000),
            description="Allow metrics scraping from VPC",
        )

        return security_group

    def _create_worker_security_group(self) -> ec2.SecurityGroup:
        """Create security group for Celery Worker ECS service"""
        security_group = ec2.SecurityGroup(
            self,
            "WorkerSecurityGroup",
            vpc=self.vpc,
            description="Security group for Celery Worker ECS service",
            allow_all_outbound=True,
        )

        # Allow connection to database
        security_group.connections.allow_to(
            self.database_security_group, ec2.Port.tcp(5432), "Worker to database"
        )

        # Allow connection to Redis
        security_group.connections.allow_to(
            self.cache_security_group, ec2.Port.tcp(6379), "Worker to Redis"
        )

        return security_group

    def _create_beat_security_group(self) -> ec2.SecurityGroup:
        """Create security group for Celery Beat ECS service"""
        security_group = ec2.SecurityGroup(
            self,
            "BeatSecurityGroup",
            vpc=self.vpc,
            description="Security group for Celery Beat ECS service",
            allow_all_outbound=True,
        )

        # Allow connection to Redis (to schedule tasks)
        security_group.connections.allow_to(
            self.cache_security_group, ec2.Port.tcp(6379), "Beat to Redis"
        )

        return security_group

    def _create_migration_security_group(self) -> ec2.SecurityGroup:
        """Create security group for database migration ECS tasks"""
        security_group = ec2.SecurityGroup(
            self,
            "MigrationSecurityGroup",
            vpc=self.vpc,
            description="Security group for database migration ECS tasks",
            allow_all_outbound=True,
        )

        # Allow connection to database
        security_group.connections.allow_to(
            self.database_security_group, ec2.Port.tcp(5432), "Migration to database"
        )

        return security_group

    def _create_alb_security_group(self) -> ec2.SecurityGroup:
        """Create security group for Application Load Balancer"""
        security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self.vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True,
        )

        # Allow HTTPS from anywhere
        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from anywhere",
        )

        # Allow HTTP from anywhere (will redirect to HTTPS)
        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere",
        )

        return security_group

    def _create_application_load_balancer(self) -> elbv2.ApplicationLoadBalancer:
        """Create Application Load Balancer for backend API"""
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "BackendAlb",
            vpc=self.vpc,
            internet_facing=True,
            load_balancer_name=f"{self.env_name}-wumbo-alb",
            security_group=self.alb_security_group,
            # Use public subnets for ALB
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            # OPTIMIZATION: Enable deletion protection for production
            deletion_protection=self.env_name == "production",
        )

        return alb

    def _create_backend_target_group(self) -> elbv2.ApplicationTargetGroup:
        """Create target group for backend API"""
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "BackendTargetGroup",
            vpc=self.vpc,
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
        )

        return target_group

    def _create_alb_listener(self) -> None:
        """Create ALB listener with HTTP to HTTPS redirect"""
        # HTTP listener - redirect to HTTPS
        http_listener = self.alb.add_listener(
            "HttpListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_action=elbv2.ListenerAction.redirect(
                protocol="HTTPS",
                port="443",
                permanent=True,
            ),
        )

        # HTTPS listener - use certificate if available, otherwise HTTP on 443
        if self.certificate:
            # Production: HTTPS with ACM certificate
            https_listener = self.alb.add_listener(
                "HttpsListener",
                port=443,
                protocol=elbv2.ApplicationProtocol.HTTPS,
                certificates=[self.certificate],
                default_action=elbv2.ListenerAction.forward([self.backend_target_group]),
            )
        else:
            # Development/Staging: HTTP on port 443 (for testing without certificate)
            https_listener = self.alb.add_listener(
                "HttpsListener",
                port=443,
                protocol=elbv2.ApplicationProtocol.HTTP,
                default_action=elbv2.ListenerAction.forward([self.backend_target_group]),
            )

    def _create_route53_records(self) -> None:
        """Create Route53 A record pointing to ALB"""
        if self.hosted_zone and self.api_subdomain:
            route53.ARecord(
                self,
                "ApiARecord",
                zone=self.hosted_zone,
                record_name=self.api_subdomain,
                target=route53.RecordTarget.from_alias(
                    targets.LoadBalancerTarget(self.alb)
                ),
                comment=f"A record for {self.api_subdomain} pointing to ALB",
            )

    def _create_backend_service(self) -> ecs.FargateService:
        """Create Backend API Fargate service"""
        # Create task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "BackendTaskDefinition",
            family=f"{self.env_name}-wumbo-backend",
            cpu=256 if self.env_name == "development" else 512,
            memory_limit_mib=512 if self.env_name == "development" else 1024,
        )

        # Grant permissions to access secrets
        self.database_secret.grant_read(task_definition.task_role)
        self.plaid_secret.grant_read(task_definition.task_role)
        self.aws_secret.grant_read(task_definition.task_role)
        self.app_secret.grant_read(task_definition.task_role)

        # Add container
        container = task_definition.add_container(
            "BackendContainer",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/docker/library/python:3.11-slim"),  # Placeholder
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="backend",
                log_retention=logs.RetentionDays.ONE_WEEK if self.env_name == "development" else logs.RetentionDays.TWO_WEEKS,
            ),
            environment={
                "ENVIRONMENT": self.env_name,
                "REDIS_HOST": self.redis_endpoint,
                "REDIS_PORT": self.redis_port,
            },
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(self.database_secret, "url"),
                "PLAID_CLIENT_ID": ecs.Secret.from_secrets_manager(self.plaid_secret, "client_id"),
                "PLAID_SECRET": ecs.Secret.from_secrets_manager(self.plaid_secret, "secret"),
                "AWS_ACCESS_KEY_ID": ecs.Secret.from_secrets_manager(self.aws_secret, "access_key_id"),
                "AWS_SECRET_ACCESS_KEY": ecs.Secret.from_secrets_manager(self.aws_secret, "secret_access_key"),
                "SECRET_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "jwt_secret_key"),
                "ENCRYPTION_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "encryption_key"),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
            ),
        )

        # Add port mapping
        container.add_port_mappings(
            ecs.PortMapping(container_port=8000, protocol=ecs.Protocol.TCP)
        )

        # Create service
        service = ecs.FargateService(
            self,
            "BackendService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=1 if self.env_name == "development" else 2,
            service_name=f"{self.env_name}-wumbo-backend",
            security_groups=[self.backend_security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            # Enable service discovery
            cloud_map_options=ecs.CloudMapOptions(
                name="backend",
                cloud_map_namespace=self.namespace,
            ),
        )

        # Attach to target group
        service.attach_to_application_target_group(self.backend_target_group)

        return service

    def _create_worker_service(self) -> ecs.FargateService:
        """Create Celery Worker Fargate service"""
        # Create task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "WorkerTaskDefinition",
            family=f"{self.env_name}-wumbo-worker",
            cpu=256,
            memory_limit_mib=512,
        )

        # Grant permissions to access secrets
        self.database_secret.grant_read(task_definition.task_role)
        self.plaid_secret.grant_read(task_definition.task_role)
        self.aws_secret.grant_read(task_definition.task_role)
        self.app_secret.grant_read(task_definition.task_role)

        # Add container
        container = task_definition.add_container(
            "WorkerContainer",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/docker/library/python:3.11-slim"),  # Placeholder
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="worker",
                log_retention=logs.RetentionDays.ONE_WEEK if self.env_name == "development" else logs.RetentionDays.TWO_WEEKS,
            ),
            environment={
                "ENVIRONMENT": self.env_name,
                "REDIS_HOST": self.redis_endpoint,
                "REDIS_PORT": self.redis_port,
            },
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(self.database_secret, "url"),
                "PLAID_CLIENT_ID": ecs.Secret.from_secrets_manager(self.plaid_secret, "client_id"),
                "PLAID_SECRET": ecs.Secret.from_secrets_manager(self.plaid_secret, "secret"),
                "AWS_ACCESS_KEY_ID": ecs.Secret.from_secrets_manager(self.aws_secret, "access_key_id"),
                "AWS_SECRET_ACCESS_KEY": ecs.Secret.from_secrets_manager(self.aws_secret, "secret_access_key"),
                "SECRET_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "jwt_secret_key"),
                "ENCRYPTION_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "encryption_key"),
            },
            command=["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "--concurrency=4"],
        )

        # Create service
        service = ecs.FargateService(
            self,
            "WorkerService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=1,
            service_name=f"{self.env_name}-wumbo-worker",
            security_groups=[self.worker_security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            # Enable service discovery
            cloud_map_options=ecs.CloudMapOptions(
                name="worker",
                cloud_map_namespace=self.namespace,
            ),
        )

        return service

    def _create_beat_service(self) -> ecs.FargateService:
        """Create Celery Beat Fargate service"""
        # Create task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "BeatTaskDefinition",
            family=f"{self.env_name}-wumbo-beat",
            cpu=256,
            memory_limit_mib=512,
        )

        # Grant permissions to access secrets
        self.app_secret.grant_read(task_definition.task_role)

        # Add container
        container = task_definition.add_container(
            "BeatContainer",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/docker/library/python:3.11-slim"),  # Placeholder
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="beat",
                log_retention=logs.RetentionDays.ONE_WEEK if self.env_name == "development" else logs.RetentionDays.TWO_WEEKS,
            ),
            environment={
                "ENVIRONMENT": self.env_name,
                "REDIS_HOST": self.redis_endpoint,
                "REDIS_PORT": self.redis_port,
            },
            secrets={
                "SECRET_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "jwt_secret_key"),
                "ENCRYPTION_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "encryption_key"),
            },
            command=["celery", "-A", "app.core.celery_app", "beat", "--loglevel=info"],
        )

        # Create service
        service = ecs.FargateService(
            self,
            "BeatService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=1,  # Always 1 beat scheduler
            service_name=f"{self.env_name}-wumbo-beat",
            security_groups=[self.beat_security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            # Enable service discovery
            cloud_map_options=ecs.CloudMapOptions(
                name="beat",
                cloud_map_namespace=self.namespace,
            ),
        )

        return service

    def _create_migration_task_definition(self) -> ecs.FargateTaskDefinition:
        """Create migration task definition for running database migrations"""
        # Create task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "MigrationTaskDefinition",
            family=f"{self.env_name}-wumbo-migration",
            cpu=256,  # Migrations don't need much CPU
            memory_limit_mib=512,
        )

        # Grant permissions to access secrets
        self.database_secret.grant_read(task_definition.task_role)
        self.app_secret.grant_read(task_definition.task_role)

        # Add container
        container = task_definition.add_container(
            "MigrationContainer",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/docker/library/python:3.11-slim"),  # Placeholder
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="migration",
                log_retention=logs.RetentionDays.ONE_MONTH,  # Keep migration logs longer
            ),
            environment={
                "ENVIRONMENT": self.env_name,
            },
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(self.database_secret, "url"),
                "SECRET_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "jwt_secret_key"),
                "ENCRYPTION_KEY": ecs.Secret.from_secrets_manager(self.app_secret, "encryption_key"),
            },
            command=["python", "scripts/run_migrations.py"],
        )

        return task_definition

    def _configure_security_group_connections(self) -> None:
        """Configure security group connections between services"""
        # Allow ALB to connect to backend
        self.backend_security_group.connections.allow_from(
            self.alb_security_group,
            ec2.Port.tcp(8000),
            "Allow traffic from ALB to backend",
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        CfnOutput(
            self,
            "AlbDnsName",
            value=self.alb.load_balancer_dns_name,
            description="ALB DNS name",
            export_name=f"{self.env_name}-AlbDnsName",
        )

        # Output custom domain URL if available, otherwise ALB DNS
        if self.api_subdomain and self.certificate:
            # Production: Use custom domain with HTTPS
            api_url = f"https://{self.api_subdomain}"
            url_description = "Backend API URL (HTTPS with custom domain)"
        else:
            # Development/Staging: Use ALB DNS with HTTP
            api_url = f"http://{self.alb.load_balancer_dns_name}"
            url_description = "Backend API URL (HTTP via ALB)"

        CfnOutput(
            self,
            "BackendApiUrl",
            value=api_url,
            description=url_description,
            export_name=f"{self.env_name}-BackendUrl",
        )

        # Output custom domain if configured
        if self.api_subdomain:
            CfnOutput(
                self,
                "ApiDomain",
                value=self.api_subdomain,
                description="Custom API domain name",
                export_name=f"{self.env_name}-ApiDomain",
            )

        # Migration task outputs
        CfnOutput(
            self,
            "MigrationTaskDefinitionArn",
            value=self.migration_task_definition.task_definition_arn,
            description="Migration task definition ARN",
            export_name=f"{self.env_name}-MigrationTaskDefArn",
        )

        CfnOutput(
            self,
            "MigrationTaskFamily",
            value=self.migration_task_definition.family,
            description="Migration task family name",
            export_name=f"{self.env_name}-MigrationTaskFamily",
        )

        CfnOutput(
            self,
            "ClusterName",
            value=self.cluster.cluster_name,
            description="ECS cluster name",
            export_name=f"{self.env_name}-ClusterName",
        )
