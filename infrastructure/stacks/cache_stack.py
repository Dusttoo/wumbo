"""ElastiCache Redis stack for caching and Celery broker"""

from aws_cdk import CfnOutput, RemovalPolicy, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticache as elasticache
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class CacheStack(Stack):
    """ElastiCache Redis cluster for caching and Celery message broker"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = vpc
        self.env_name = env_name

        # Create Redis subnet group (use isolated subnets for database-tier resources)
        self.subnet_group = self._create_subnet_group()

        # Create Redis parameter group
        self.parameter_group = self._create_parameter_group()

        # Create security group for Redis
        self.security_group = self._create_security_group()

        # Create Redis cluster/replication group based on environment
        if env_name == "production":
            self._create_production_redis()
        else:
            self._create_dev_staging_redis()

        # Store endpoint in SSM Parameter Store
        self._create_ssm_parameters()

        # Tag all resources
        Tags.of(self).add("Stack", "CacheStack")
        Tags.of(self).add("Service", "ElastiCache")
        Tags.of(self).add("Purpose", "CachingAndMessaging")

    def _create_subnet_group(self) -> elasticache.CfnSubnetGroup:
        """Create subnet group for Redis in isolated subnets"""
        # Use isolated subnets if available, otherwise private subnets
        subnets = (
            self.vpc.isolated_subnets if self.vpc.isolated_subnets else self.vpc.private_subnets
        )

        subnet_group = elasticache.CfnSubnetGroup(
            self,
            "RedisSubnetGroup",
            description=f"Subnet group for {self.env_name} Redis cache",
            subnet_ids=[subnet.subnet_id for subnet in subnets],
            cache_subnet_group_name=f"wumbo-redis-{self.env_name}",
            tags=[
                {"key": "Name", "value": f"{self.env_name}-redis-subnet-group"},
                {"key": "Environment", "value": self.env_name},
            ],
        )

        return subnet_group

    def _create_parameter_group(self) -> elasticache.CfnParameterGroup:
        """Create Redis parameter group optimized for caching and messaging"""
        parameter_group = elasticache.CfnParameterGroup(
            self,
            "RedisParameterGroup",
            cache_parameter_group_family="redis7",
            description=f"Redis parameters for {self.env_name} caching and messaging",
            properties={
                # Eviction policy: Remove least recently used keys when memory is full
                "maxmemory-policy": "allkeys-lru",
                # Close idle connections after 10 minutes
                "timeout": "600",
                # Note: 'save' parameter omitted to use default behavior
                # (snapshots are disabled by default for cache clusters without backup enabled)
            },
            tags=[
                {"key": "Name", "value": f"{self.env_name}-redis-params"},
                {"key": "Environment", "value": self.env_name},
            ],
        )

        return parameter_group

    def _create_security_group(self) -> ec2.SecurityGroup:
        """Create security group for Redis

        Note: Ingress rules will be added by ComputeStack after ECS security group is created
        to avoid circular dependencies.
        """
        redis_sg = ec2.SecurityGroup(
            self,
            "RedisSG",
            vpc=self.vpc,
            description=f"Security group for {self.env_name} ElastiCache Redis",
            allow_all_outbound=False,  # Redis doesn't need outbound
        )

        # Allow inbound from VPC CIDR for now
        # ComputeStack will add specific ECS security group rules
        redis_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(6379),
            description="Allow Redis access from VPC (will be restricted to ECS in ComputeStack)",
        )

        Tags.of(redis_sg).add("Name", f"{self.env_name}-redis-sg")

        return redis_sg

    def _get_node_type(self) -> str:
        """Get appropriate instance type based on environment"""
        # Using Graviton2 (t4g/r7g) for 20% cost savings
        node_types = {
            "development": "cache.t4g.micro",  # $0.016/hr (~$12/mo) - 0.5GB RAM
            "staging": "cache.t4g.small",  # $0.034/hr (~$25/mo) - 1.37GB RAM
            "production": "cache.r7g.large",  # $0.145/hr (~$106/mo) - 13.07GB RAM
        }
        return node_types.get(self.env_name, "cache.t4g.micro")

    def _create_production_redis(self) -> None:
        """Create production Redis with Multi-AZ replication for high availability"""
        # Create auth token secret for production
        auth_token_secret = secretsmanager.Secret(
            self,
            "RedisAuthToken",
            description=f"Redis auth token for {self.env_name}",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                password_length=32,
            ),
            removal_policy=RemovalPolicy.RETAIN,  # Keep secret on stack deletion
        )

        # Create replication group for HA
        self.cache_cluster = elasticache.CfnReplicationGroup(
            self,
            "RedisCluster",
            replication_group_description=f"Redis cluster for {self.env_name} caching and messaging",
            engine="redis",
            engine_version="7.1",
            cache_node_type=self._get_node_type(),
            num_cache_clusters=2,  # Primary + 1 replica
            automatic_failover_enabled=True,
            multi_az_enabled=True,
            cache_subnet_group_name=self.subnet_group.cache_subnet_group_name,
            cache_parameter_group_name=self.parameter_group.ref,
            security_group_ids=[self.security_group.security_group_id],
            # Security: Encryption at rest and in transit
            at_rest_encryption_enabled=True,
            transit_encryption_enabled=True,
            auth_token=auth_token_secret.secret_value.unsafe_unwrap(),
            # Backups
            snapshot_retention_limit=7,  # Keep 7 days of backups
            snapshot_window="03:00-05:00",  # 3-5 AM UTC
            preferred_maintenance_window="sun:05:00-sun:06:00",  # Sunday 5-6 AM UTC
            # Auto minor version upgrades
            auto_minor_version_upgrade=True,
            tags=[
                {"key": "Name", "value": f"{self.env_name}-redis-cluster"},
                {"key": "Environment", "value": self.env_name},
                {"key": "HighAvailability", "value": "true"},
            ],
        )

        # Add dependencies
        self.cache_cluster.add_dependency(self.subnet_group)
        self.cache_cluster.add_dependency(self.parameter_group)

        # Store auth token in SSM for easy retrieval
        ssm.StringParameter(
            self,
            "RedisAuthTokenParam",
            parameter_name=f"/wumbo/{self.env_name}/redis/auth-token",
            string_value=auth_token_secret.secret_value.unsafe_unwrap(),
            description="Redis auth token",
        )

        # Export endpoints
        self.redis_endpoint = self.cache_cluster.attr_primary_end_point_address
        self.redis_port = self.cache_cluster.attr_primary_end_point_port
        self.redis_auth_token = auth_token_secret.secret_value.unsafe_unwrap()

        CfnOutput(
            self,
            "RedisPrimaryEndpoint",
            value=self.redis_endpoint,
            description="Redis primary endpoint address",
            export_name=f"{self.env_name}-redis-primary",
        )

        CfnOutput(
            self,
            "RedisPort",
            value=self.redis_port,
            description="Redis port",
            export_name=f"{self.env_name}-redis-port",
        )

    def _create_dev_staging_redis(self) -> None:
        """Create single-instance Redis for dev/staging (no HA, no encryption)"""
        self.cache_cluster = elasticache.CfnCacheCluster(
            self,
            "RedisInstance",
            cache_node_type=self._get_node_type(),
            engine="redis",
            engine_version="7.1",
            num_cache_nodes=1,  # Single instance
            cache_subnet_group_name=self.subnet_group.cache_subnet_group_name,
            cache_parameter_group_name=self.parameter_group.ref,
            vpc_security_group_ids=[self.security_group.security_group_id],
            az_mode="single-az",
            preferred_maintenance_window="sun:05:00-sun:06:00",
            # Auto minor version upgrades
            auto_minor_version_upgrade=True,
            tags=[
                {"key": "Name", "value": f"{self.env_name}-redis-instance"},
                {"key": "Environment", "value": self.env_name},
                {"key": "HighAvailability", "value": "false"},
            ],
        )

        # Add dependencies
        self.cache_cluster.add_dependency(self.subnet_group)
        self.cache_cluster.add_dependency(self.parameter_group)

        # Export endpoints
        self.redis_endpoint = self.cache_cluster.attr_redis_endpoint_address
        self.redis_port = self.cache_cluster.attr_redis_endpoint_port
        self.redis_auth_token = None  # No auth for dev/staging

        CfnOutput(
            self,
            "RedisEndpoint",
            value=self.redis_endpoint,
            description="Redis endpoint address",
            export_name=f"{self.env_name}-redis-endpoint",
        )

        CfnOutput(
            self,
            "RedisPort",
            value=self.redis_port,
            description="Redis port",
            export_name=f"{self.env_name}-redis-port",
        )

    def _create_ssm_parameters(self) -> None:
        """Store Redis connection info in SSM Parameter Store"""
        ssm.StringParameter(
            self,
            "RedisEndpointParam",
            parameter_name=f"/wumbo/{self.env_name}/redis/endpoint",
            string_value=self.redis_endpoint,
            description=f"Redis endpoint for {self.env_name}",
        )

        ssm.StringParameter(
            self,
            "RedisPortParam",
            parameter_name=f"/wumbo/{self.env_name}/redis/port",
            string_value=self.redis_port,
            description=f"Redis port for {self.env_name}",
        )

        # Store complete connection string for convenience
        # Note: Production uses SSL and auth token
        if self.env_name == "production" and self.redis_auth_token:
            # Format: rediss://:password@host:port/db
            connection_string = (
                f"rediss://:{self.redis_auth_token}@{self.redis_endpoint}:{self.redis_port}/0"
            )
        else:
            connection_string = f"redis://{self.redis_endpoint}:{self.redis_port}/0"

        ssm.StringParameter(
            self,
            "RedisConnectionString",
            parameter_name=f"/wumbo/{self.env_name}/redis/connection-string",
            string_value=connection_string,
            description=f"Redis connection string for {self.env_name} (includes auth token for production)",
            tier=(
                ssm.ParameterTier.ADVANCED
                if self.env_name == "production"
                else ssm.ParameterTier.STANDARD
            ),
        )
