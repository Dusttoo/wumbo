# infrastructure/stacks/monitoring_stack.py
"""Monitoring and alerting stack for Wumbo

Complete monitoring stack with Prometheus for metrics collection and
Grafana for visualization and dashboarding.
"""

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_elasticache as elasticache
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_servicediscovery as servicediscovery
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from constructs import Construct


class MonitoringStack(Stack):
    """Stack for monitoring, alarms, and dashboards"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        cluster: ecs.ICluster,
        backend_service: ecs.IService,
        worker_service: ecs.IService,
        beat_service: ecs.IService,
        database: rds.IDatabaseInstance,
        cache_cluster,  # elasticache.CfnCacheCluster or CfnReplicationGroup
        env_name: str,
        namespace: servicediscovery.IPrivateDnsNamespace,
        alarm_email: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = vpc
        self.cluster = cluster
        self.backend_service = backend_service
        self.worker_service = worker_service
        self.beat_service = beat_service
        self.database = database
        self.cache_cluster = cache_cluster
        self.env_name = env_name
        self.namespace = namespace

        # Create SNS topic for alarms
        self.alarm_topic = self._create_alarm_topic(alarm_email)

        # Create EFS file system for persistent storage
        self.file_system = self._create_efs_file_system()

        # Create security groups
        self.monitoring_security_group = self._create_monitoring_security_group()
        self.grafana_alb_security_group = self._create_grafana_alb_security_group()

        # Create Prometheus service
        self.prometheus_service = self._create_prometheus_service()

        # Create Grafana ALB and service
        self.grafana_alb = self._create_grafana_alb()
        self.grafana_target_group = self._create_grafana_target_group()
        self._create_grafana_alb_listener()
        self.grafana_service = self._create_grafana_service()

        # Create CloudWatch alarms
        self._create_cloudwatch_alarms()

        # Create outputs
        self._create_outputs()

    def _create_alarm_topic(self, email: str = None) -> sns.Topic:
        """Create SNS topic for CloudWatch alarms"""
        topic = sns.Topic(
            self,
            "AlarmTopic",
            display_name=f"Wumbo Alarms ({self.env_name})",
        )

        # OPTIMIZATION: Only add email subscription if provided
        if email:
            topic.add_subscription(subscriptions.EmailSubscription(email))

        return topic

    def _create_efs_file_system(self) -> efs.FileSystem:
        """Create EFS file system for Prometheus and Grafana data"""
        file_system = efs.FileSystem(
            self,
            "MonitoringFileSystem",
            vpc=self.vpc,
            file_system_name=f"{self.env_name}-wumbo-monitoring",
            # OPTIMIZATION: Different removal policies per environment
            removal_policy=(
                RemovalPolicy.DESTROY if self.env_name == "development" else RemovalPolicy.RETAIN
            ),
            # OPTIMIZATION: Bursting mode for cost efficiency
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            # Enable encryption at rest
            encrypted=True,
        )

        return file_system

    def _create_monitoring_security_group(self) -> ec2.SecurityGroup:
        """Create security group for Prometheus and Grafana"""
        security_group = ec2.SecurityGroup(
            self,
            "MonitoringSecurityGroup",
            vpc=self.vpc,
            description="Security group for monitoring services (Prometheus & Grafana)",
            allow_all_outbound=True,
        )

        # Allow Prometheus to scrape metrics from services in VPC
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(9090),
            description="Allow Prometheus UI access from VPC",
        )

        # Allow Grafana access
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(3000),
            description="Allow Grafana UI access from VPC",
        )

        # Allow EFS access
        security_group.connections.allow_to(
            self.file_system,
            ec2.Port.tcp(2049),
            "Monitoring services to EFS",
        )

        return security_group

    def _create_grafana_alb_security_group(self) -> ec2.SecurityGroup:
        """Create security group for Grafana ALB"""
        security_group = ec2.SecurityGroup(
            self,
            "GrafanaAlbSecurityGroup",
            vpc=self.vpc,
            description="Security group for Grafana ALB",
            allow_all_outbound=True,
        )

        # Allow HTTP from anywhere (will redirect to HTTPS in production)
        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere",
        )

        # Allow HTTPS from anywhere (for production with certificate)
        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from anywhere",
        )

        return security_group

    def _create_prometheus_service(self) -> ecs.FargateService:
        """Create Prometheus ECS service"""
        # Create task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "PrometheusTaskDefinition",
            family=f"{self.env_name}-wumbo-prometheus",
            cpu=512,
            memory_limit_mib=1024,
        )

        # Add EFS volume
        prometheus_volume = task_definition.add_volume(
            name="prometheus-data",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=self.file_system.file_system_id,
                transit_encryption="ENABLED",
            ),
        )

        # Add container
        container = task_definition.add_container(
            "PrometheusContainer",
            image=ecs.ContainerImage.from_registry("prom/prometheus:latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="prometheus",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "ENVIRONMENT": self.env_name,
            },
            command=[
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.path=/prometheus",
                "--storage.tsdb.retention.time=15d",
                "--web.console.libraries=/usr/share/prometheus/console_libraries",
                "--web.console.templates=/usr/share/prometheus/consoles",
            ],
        )

        # Mount EFS volume
        container.add_mount_points(
            ecs.MountPoint(
                source_volume=prometheus_volume.name,
                container_path="/prometheus",
                read_only=False,
            )
        )

        # Add port mapping
        container.add_port_mappings(
            ecs.PortMapping(container_port=9090, protocol=ecs.Protocol.TCP)
        )

        # Create service
        service = ecs.FargateService(
            self,
            "PrometheusService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=1,
            service_name=f"{self.env_name}-wumbo-prometheus",
            security_groups=[self.monitoring_security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            # Enable service discovery
            cloud_map_options=ecs.CloudMapOptions(
                name="prometheus",
                cloud_map_namespace=self.namespace,
            ),
        )

        return service

    def _create_grafana_alb(self) -> elbv2.ApplicationLoadBalancer:
        """Create ALB for Grafana UI"""
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "GrafanaAlb",
            vpc=self.vpc,
            internet_facing=True,
            load_balancer_name=f"{self.env_name}-grafana-alb",
            security_group=self.grafana_alb_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            # OPTIMIZATION: Enable deletion protection for production
            deletion_protection=self.env_name == "production",
        )

        return alb

    def _create_grafana_target_group(self) -> elbv2.ApplicationTargetGroup:
        """Create target group for Grafana"""
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "GrafanaTargetGroup",
            vpc=self.vpc,
            port=3000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/api/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
        )

        return target_group

    def _create_grafana_alb_listener(self) -> None:
        """Create ALB listener for Grafana"""
        # HTTP listener - forward to Grafana (use HTTPS with certificate in production)
        self.grafana_alb.add_listener(
            "GrafanaHttpListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_action=elbv2.ListenerAction.forward([self.grafana_target_group]),
        )

    def _create_grafana_service(self) -> ecs.FargateService:
        """Create Grafana ECS service"""
        # Create task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "GrafanaTaskDefinition",
            family=f"{self.env_name}-wumbo-grafana",
            cpu=512,
            memory_limit_mib=1024,
        )

        # Add EFS volume
        grafana_volume = task_definition.add_volume(
            name="grafana-data",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=self.file_system.file_system_id,
                transit_encryption="ENABLED",
            ),
        )

        # Add container
        container = task_definition.add_container(
            "GrafanaContainer",
            image=ecs.ContainerImage.from_registry("grafana/grafana:latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="grafana",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "GF_SECURITY_ADMIN_PASSWORD": "changeme",  # Change in production via secrets
                "GF_INSTALL_PLUGINS": "",
                "GF_SERVER_ROOT_URL": f"http://{self.grafana_alb.load_balancer_dns_name}",
                "GF_ANALYTICS_REPORTING_ENABLED": "false",
                "GF_ANALYTICS_CHECK_FOR_UPDATES": "false",
            },
        )

        # Mount EFS volume
        container.add_mount_points(
            ecs.MountPoint(
                source_volume=grafana_volume.name,
                container_path="/var/lib/grafana",
                read_only=False,
            )
        )

        # Add port mapping
        container.add_port_mappings(
            ecs.PortMapping(container_port=3000, protocol=ecs.Protocol.TCP)
        )

        # Create service
        service = ecs.FargateService(
            self,
            "GrafanaService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=1,
            service_name=f"{self.env_name}-wumbo-grafana",
            security_groups=[self.monitoring_security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            # Enable service discovery
            cloud_map_options=ecs.CloudMapOptions(
                name="grafana",
                cloud_map_namespace=self.namespace,
            ),
        )

        # Attach to target group
        service.attach_to_application_target_group(self.grafana_target_group)

        # Allow ALB to connect to Grafana
        self.monitoring_security_group.connections.allow_from(
            self.grafana_alb_security_group,
            ec2.Port.tcp(3000),
            "Allow traffic from Grafana ALB",
        )

        return service

    def _create_cloudwatch_alarms(self) -> None:
        """Create CloudWatch alarms for critical metrics"""
        # Backend service CPU alarm
        backend_cpu_alarm = cloudwatch.Alarm(
            self,
            "BackendHighCpuAlarm",
            metric=self.backend_service.metric_cpu_utilization(),
            threshold=80,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            alarm_description="Backend service CPU utilization is too high",
            alarm_name=f"{self.env_name}-backend-high-cpu",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        backend_cpu_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Backend service memory alarm
        backend_memory_alarm = cloudwatch.Alarm(
            self,
            "BackendHighMemoryAlarm",
            metric=self.backend_service.metric_memory_utilization(),
            threshold=80,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            alarm_description="Backend service memory utilization is too high",
            alarm_name=f"{self.env_name}-backend-high-memory",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        backend_memory_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Database CPU alarm
        database_cpu_alarm = cloudwatch.Alarm(
            self,
            "DatabaseHighCpuAlarm",
            metric=self.database.metric_cpu_utilization(),
            threshold=80,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            alarm_description="Database CPU utilization is too high",
            alarm_name=f"{self.env_name}-database-high-cpu",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        database_cpu_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Database connections alarm
        database_connections_alarm = cloudwatch.Alarm(
            self,
            "DatabaseHighConnectionsAlarm",
            metric=self.database.metric_database_connections(),
            threshold=80,  # Percentage of max connections
            evaluation_periods=2,
            datapoints_to_alarm=2,
            alarm_description="Database connection count is too high",
            alarm_name=f"{self.env_name}-database-high-connections",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        database_connections_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        # Alarm topic outputs
        CfnOutput(
            self,
            "AlarmTopicArn",
            value=self.alarm_topic.topic_arn,
            description="SNS topic ARN for alarms",
            export_name=f"{self.env_name}-AlarmTopicArn",
        )

        CfnOutput(
            self,
            "AlarmTopicName",
            value=self.alarm_topic.topic_name,
            description="SNS topic name for alarms",
            export_name=f"{self.env_name}-AlarmTopicName",
        )

        # Grafana outputs
        CfnOutput(
            self,
            "GrafanaUrl",
            value=f"http://{self.grafana_alb.load_balancer_dns_name}",
            description="Grafana dashboard URL",
            export_name=f"{self.env_name}-GrafanaUrl",
        )

        CfnOutput(
            self,
            "GrafanaAlbDnsName",
            value=self.grafana_alb.load_balancer_dns_name,
            description="Grafana ALB DNS name",
            export_name=f"{self.env_name}-GrafanaAlbDnsName",
        )

        # Prometheus outputs
        CfnOutput(
            self,
            "PrometheusServiceName",
            value=self.prometheus_service.service_name,
            description="Prometheus service name",
            export_name=f"{self.env_name}-PrometheusServiceName",
        )

        # EFS outputs
        CfnOutput(
            self,
            "MonitoringFileSystemId",
            value=self.file_system.file_system_id,
            description="EFS file system ID for monitoring data",
            export_name=f"{self.env_name}-MonitoringEfsId",
        )
