.PHONY: help install synth deploy deploy-all destroy diff bootstrap list outputs clean

# Default environment
ENV ?= development

help:
	@echo "Wumbo Infrastructure - Available commands:"
	@echo ""
	@echo "  make install          - Install Python dependencies"
	@echo "  make synth            - Synthesize CloudFormation templates"
	@echo "  make deploy           - Deploy all stacks"
	@echo "  make deploy-stack     - Deploy specific stack (STACK=SecurityStack)"
	@echo "  make destroy          - Destroy all stacks"
	@echo "  make diff             - Show differences between deployed and local"
	@echo "  make bootstrap        - Bootstrap CDK for first time use"
	@echo "  make list             - List all stacks"
	@echo "  make outputs          - Show stack outputs"
	@echo "  make clean            - Clean synthesized templates"
	@echo ""
	@echo "Environment: $(ENV) (override with ENV=staging or ENV=production)"
	@echo ""

install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

synth:
	@echo "Synthesizing CloudFormation templates for $(ENV)..."
	cdk synth -c environment=$(ENV)

deploy:
	@echo "Deploying all stacks for $(ENV)..."
	cdk deploy -c environment=$(ENV) --all --require-approval never

deploy-stack:
	@echo "Deploying $(STACK) for $(ENV)..."
	cdk deploy -c environment=$(ENV) $(ENV)-$(STACK) --require-approval never

destroy:
	@echo "WARNING: This will destroy all infrastructure for $(ENV)!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	cdk destroy -c environment=$(ENV) --all

diff:
	@echo "Showing differences for $(ENV)..."
	cdk diff -c environment=$(ENV)

bootstrap:
	@echo "Bootstrapping CDK..."
	cdk bootstrap

list:
	@echo "Listing stacks for $(ENV)..."
	cdk list -c environment=$(ENV)

outputs:
	@echo "Stack outputs for $(ENV):"
	@echo ""
	@echo "=== Security Stack ==="
	@aws cloudformation describe-stacks --stack-name $(ENV)-SecurityStack \
		--query 'Stacks[0].Outputs' --output table 2>/dev/null || echo "Stack not deployed"
	@echo ""
	@echo "=== Database Stack ==="
	@aws cloudformation describe-stacks --stack-name $(ENV)-DatabaseStack \
		--query 'Stacks[0].Outputs' --output table 2>/dev/null || echo "Stack not deployed"
	@echo ""
	@echo "=== Cache Stack ==="
	@aws cloudformation describe-stacks --stack-name $(ENV)-CacheStack \
		--query 'Stacks[0].Outputs' --output table 2>/dev/null || echo "Stack not deployed"
	@echo ""
	@echo "=== Compute Stack ==="
	@aws cloudformation describe-stacks --stack-name $(ENV)-ComputeStack \
		--query 'Stacks[0].Outputs' --output table 2>/dev/null || echo "Stack not deployed"

clean:
	@echo "Cleaning synthesized templates..."
	rm -rf cdk.out
	rm -f cdk.context.json

# Deployment order commands
deploy-foundation:
	@echo "Deploying foundation stacks (Security, ECR, Database, Cache)..."
	cdk deploy -c environment=$(ENV) \
		$(ENV)-SecurityStack \
		$(ENV)-EcrStack \
		$(ENV)-DatabaseStack \
		$(ENV)-CacheStack \
		--require-approval never

deploy-compute:
	@echo "Deploying compute stack..."
	cdk deploy -c environment=$(ENV) $(ENV)-ComputeStack --require-approval never

deploy-monitoring:
	@echo "Deploying monitoring stack..."
	cdk deploy -c environment=$(ENV) $(ENV)-MonitoringStack --require-approval never
