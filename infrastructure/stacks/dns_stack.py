# infrastructure/stacks/dns_stack.py
"""DNS and SSL certificate stack for Wumbo - Route53 and ACM"""

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_route53 as route53
from constructs import Construct


class DnsStack(Stack):
    """Stack for Route53 hosted zone and ACM SSL certificate"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        domain_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = env_name
        self.domain_name = domain_name

        # Create or lookup hosted zone
        self.hosted_zone = self._create_or_lookup_hosted_zone()

        # Create SSL certificate for all subdomains
        self.certificate = self._create_certificate()

        # Create outputs
        self._create_outputs()

    def _create_or_lookup_hosted_zone(self) -> route53.IHostedZone:
        """Create or lookup Route53 hosted zone for the domain

        For production, we typically want to look up an existing hosted zone
        For development/staging, we can create a new one
        """
        if self.env_name == "production":
            # Production should use the main domain's hosted zone
            # Lookup existing hosted zone
            hosted_zone = route53.HostedZone.from_lookup(
                self,
                "HostedZone",
                domain_name=self.domain_name,
            )
        else:
            # For dev/staging, create a subdomain hosted zone
            # e.g., dev.wumbo.app or staging.wumbo.app
            zone_name = f"{self.env_name}.{self.domain_name}"
            hosted_zone = route53.HostedZone(
                self,
                "HostedZone",
                zone_name=zone_name,
                comment=f"Hosted zone for {self.env_name} environment",
            )

        return hosted_zone

    def _create_certificate(self) -> acm.Certificate:
        """Create ACM certificate for the domain and all subdomains

        This creates a wildcard certificate that covers:
        - *.wumbo.app (production)
        - *.dev.wumbo.app (development)
        - *.staging.wumbo.app (staging)
        """
        if self.env_name == "production":
            domain_name = self.domain_name
            subject_alternative_names = [f"*.{self.domain_name}"]
        else:
            domain_name = f"{self.env_name}.{self.domain_name}"
            subject_alternative_names = [f"*.{self.env_name}.{self.domain_name}"]

        certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name=domain_name,
            subject_alternative_names=subject_alternative_names,
            validation=acm.CertificateValidation.from_dns(self.hosted_zone),
        )

        return certificate

    def get_subdomain(self, subdomain: str) -> str:
        """Get full subdomain for a given service

        Args:
            subdomain: Service name (e.g., 'api', 'admin')

        Returns:
            Full domain name (e.g., 'api.wumbo.app', 'api.dev.wumbo.app')
        """
        if self.env_name == "production":
            return f"{subdomain}.{self.domain_name}"
        else:
            return f"{subdomain}.{self.env_name}.{self.domain_name}"

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        CfnOutput(
            self,
            "HostedZoneId",
            value=self.hosted_zone.hosted_zone_id,
            description="Route53 hosted zone ID",
            export_name=f"{self.env_name}-HostedZoneId",
        )

        CfnOutput(
            self,
            "HostedZoneName",
            value=self.hosted_zone.zone_name,
            description="Route53 hosted zone name",
            export_name=f"{self.env_name}-HostedZoneName",
        )

        CfnOutput(
            self,
            "CertificateArn",
            value=self.certificate.certificate_arn,
            description="ACM certificate ARN",
            export_name=f"{self.env_name}-CertificateArn",
        )

        # Output common subdomains
        CfnOutput(
            self,
            "ApiDomain",
            value=self.get_subdomain("api"),
            description="API domain name",
        )

        CfnOutput(
            self,
            "WebDomain",
            value=self.get_subdomain("app"),
            description="Web app domain name",
        )
