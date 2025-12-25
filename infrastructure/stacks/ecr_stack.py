# infrastructure/stacks/ecr_stack.py
"""ECR repositories for container images"""

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from constructs import Construct


class EcrStack(Stack):
    """Stack for ECR repositories"""

    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = env_name

        # Backend repository (used for API, Celery worker, Celery beat)
        self.backend_repo = self._create_repository("backend", "FastAPI backend container images")

        # Migration repository (for Alembic migrations)
        self.migration_repo = self._create_repository(
            "migration", "Database migration container images"
        )

        # Create IAM user for GitHub Actions
        self.github_actions_user = self._create_github_actions_user()

        # Create outputs
        self._create_outputs()

    def _get_image_retention_count(self) -> int:
        """Get number of images to retain based on environment"""
        retention_map = {
            "development": 3,  # Keep last 3 images in dev
            "staging": 5,  # Keep last 5 images in staging
            "production": 10,  # Keep last 10 images in production
        }
        return retention_map.get(self.env_name, 3)

    def _get_untagged_retention_days(self) -> int:
        """Get retention days for untagged images"""
        retention_map = {
            "development": 1,  # Delete untagged images after 1 day
            "staging": 3,  # Delete after 3 days
            "production": 7,  # Delete after 7 days
        }
        return retention_map.get(self.env_name, 1)

    def _create_repository(self, name: str, description: str) -> ecr.Repository:
        """Create ECR repository with optimized lifecycle policies"""

        repository = ecr.Repository(
            self,
            f"{name.title()}Repository",
            repository_name=f"{self.env_name}-wumbo-{name}",
            # OPTIMIZATION: Enable image scanning only for production
            image_scan_on_push=self.env_name == "production",
            # OPTIMIZATION: Use AES256 encryption for dev/staging (free)
            # Use KMS only for production if needed
            encryption=ecr.RepositoryEncryption.AES_256,
            # OPTIMIZATION: Auto-delete repositories in dev/staging
            removal_policy=(
                RemovalPolicy.DESTROY if self.env_name != "production" else RemovalPolicy.RETAIN
            ),
            # OPTIMIZATION: Auto-delete images when repo is deleted (dev/staging only)
            auto_delete_images=self.env_name != "production",
            # Lifecycle policies to manage image retention
            lifecycle_rules=[
                # OPTIMIZATION: Keep only N tagged images
                ecr.LifecycleRule(
                    description=f"Keep last {self._get_image_retention_count()} tagged images",
                    rule_priority=1,
                    tag_status=ecr.TagStatus.TAGGED,
                    tag_prefix_list=["latest", "v"],  # Keep versioned and latest tags
                    max_image_count=self._get_image_retention_count(),
                ),
                # OPTIMIZATION: Delete untagged images quickly
                ecr.LifecycleRule(
                    description=f"Delete untagged images after {self._get_untagged_retention_days()} days",
                    rule_priority=2,
                    tag_status=ecr.TagStatus.UNTAGGED,
                    max_image_age=Duration.days(self._get_untagged_retention_days()),
                ),
                # OPTIMIZATION: Delete old tagged images by age
                ecr.LifecycleRule(
                    description="Delete images older than 30 days (except latest)",
                    rule_priority=3,
                    tag_status=ecr.TagStatus.TAGGED,
                    tag_prefix_list=["sha-", "build-"],  # Only for build-specific tags
                    max_image_age=Duration.days(30),
                ),
            ],
        )

        # OPTIMIZATION: Add resource tags for cost allocation
        repository.node.add_metadata("cost-center", "wumbo")
        repository.node.add_metadata("environment", self.env_name)

        return repository

    def _create_github_actions_user(self) -> iam.User:
        """Create IAM user for GitHub Actions to push to ECR"""

        user = iam.User(
            self,
            "GitHubActionsUser",
            user_name=f"{self.env_name}-wumbo-github-actions",
        )

        # Grant permissions to push to all ECR repos
        policy = iam.Policy(
            self,
            "GitHubActionsEcrPolicy",
            policy_name=f"{self.env_name}-wumbo-ecr-push",
            statements=[
                # ECR login
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:GetAuthorizationToken",
                    ],
                    resources=["*"],
                ),
                # Repository access
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:GetRepositoryPolicy",
                        "ecr:DescribeRepositories",
                        "ecr:ListImages",
                        "ecr:DescribeImages",
                        "ecr:BatchGetImage",
                        "ecr:InitiateLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:CompleteLayerUpload",
                        "ecr:PutImage",
                    ],
                    resources=[
                        self.backend_repo.repository_arn,
                        self.migration_repo.repository_arn,
                    ],
                ),
                # OPTIMIZATION: Only grant ECS deployment permissions for staging/production
                *(
                    [
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecs:UpdateService",
                                "ecs:DescribeServices",
                                "ecs:DescribeTaskDefinition",
                                "ecs:RegisterTaskDefinition",
                            ],
                            resources=[
                                f"arn:aws:ecs:{self.region}:{self.account}:service/{self.env_name}-wumbo-cluster/*",
                                f"arn:aws:ecs:{self.region}:{self.account}:task-definition/{self.env_name}-wumbo-*:*",
                            ],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "iam:PassRole",
                            ],
                            resources=[
                                f"arn:aws:iam::{self.account}:role/{self.env_name}-*-TaskRole*",
                                f"arn:aws:iam::{self.account}:role/{self.env_name}-*-ExecutionRole*",
                            ],
                            conditions={
                                "StringEquals": {"iam:PassedToService": "ecs-tasks.amazonaws.com"}
                            },
                        ),
                    ]
                    if self.env_name in ["staging", "production"]
                    else []
                ),
            ],
        )

        policy.attach_to_user(user)

        return user

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""

        # Repository URIs
        CfnOutput(
            self,
            "BackendRepositoryUri",
            value=self.backend_repo.repository_uri,
            description="Backend ECR repository URI",
            export_name=f"{self.env_name}-BackendRepositoryUri",
        )

        CfnOutput(
            self,
            "MigrationRepositoryUri",
            value=self.migration_repo.repository_uri,
            description="Migration ECR repository URI",
            export_name=f"{self.env_name}-MigrationRepositoryUri",
        )

        # Repository ARNs
        CfnOutput(
            self,
            "BackendRepositoryArn",
            value=self.backend_repo.repository_arn,
            description="Backend ECR repository ARN",
            export_name=f"{self.env_name}-BackendRepositoryArn",
        )

        CfnOutput(
            self,
            "MigrationRepositoryArn",
            value=self.migration_repo.repository_arn,
            description="Migration ECR repository ARN",
            export_name=f"{self.env_name}-MigrationRepositoryArn",
        )

        # GitHub Actions user
        CfnOutput(
            self,
            "GitHubActionsUserName",
            value=self.github_actions_user.user_name,
            description="IAM user name for GitHub Actions",
            export_name=f"{self.env_name}-GitHubActionsUserName",
        )

        CfnOutput(
            self,
            "GitHubActionsUserArn",
            value=self.github_actions_user.user_arn,
            description="IAM user ARN for GitHub Actions",
            export_name=f"{self.env_name}-GitHubActionsUserArn",
        )
