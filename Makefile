.PHONY: help doctor smoke fmt lint clean

help:
	@echo "EventBridge + Lambda + SQS Starter - Makefile targets"
	@echo ""
	@echo "  make doctor     - Check prerequisites (AWS creds, Terraform, Python)"
	@echo "  make smoke      - Run post-deployment smoke test"
	@echo "  make fmt        - Format Terraform and Python code"
	@echo "  make lint       - Lint Terraform and Python code"
	@echo "  make clean      - Clean temporary files"
	@echo ""

doctor:
	@python3 scripts/doctor.py --verbose

smoke:
	@echo "Running smoke test..."
	@echo "Make sure you have run 'terraform apply' first!"
	@cd infra && \
		BUS_NAME=$$(terraform output -raw event_bus_name) && \
		LAMBDA_NAME=$$(terraform output -raw lambda_function_name) && \
		LOG_GROUP=$$(terraform output -raw lambda_log_group) && \
		DLQ_URL=$$(terraform output -raw sqs_dlq_url) && \
		cd .. && \
		python3 scripts/smoke_test.py \
			--bus-name "$$BUS_NAME" \
			--lambda-name "$$LAMBDA_NAME" \
			--log-group "$$LOG_GROUP" \
			--dlq-url "$$DLQ_URL"

fmt:
	@echo "Formatting Terraform..."
	@cd infra && terraform fmt -recursive
	@echo "Formatting Python..."
	@black scripts/ src/
	@isort scripts/ src/

lint:
	@echo "Linting Terraform..."
	@cd infra && terraform fmt -check -recursive
	@cd infra && terraform validate
	@echo "Linting Python..."
	@ruff check scripts/ src/
	@black --check scripts/ src/
	@isort --check scripts/ src/

clean:
	@echo "Cleaning temporary files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf infra/.terraform/lambda_function.zip
	@echo "Clean complete."
