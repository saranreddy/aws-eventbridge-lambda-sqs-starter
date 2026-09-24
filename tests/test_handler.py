"""Unit tests for Lambda handler."""

import json
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

# Add src directory to Python path to enable imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Use importlib to import from lambda directory (keyword workaround)
lambda_module = import_module("lambda.handler")
lambda_handler = lambda_module.lambda_handler


class FakeLambdaContext:
    """Fake Lambda context object with real LambdaContext attributes."""

    def __init__(self) -> None:
        self.aws_request_id = "test-request-id-12345"
        self.function_name = "test-lambda-function"
        self.memory_limit_in_mb = "512"
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:test-lambda-function"
        )
        self.log_group_name = "/aws/lambda/test-lambda-function"
        self.log_stream_name = "2024/01/01/[$LATEST]abcdef123456"

    def get_remaining_time_in_millis(self) -> int:
        """Return fake remaining time in milliseconds."""
        return 30000


@pytest.fixture
def lambda_context() -> FakeLambdaContext:
    """Provide a fake Lambda context for tests."""
    return FakeLambdaContext()


@pytest.fixture
def event_bridge_event_dict() -> dict[str, Any]:
    """Provide a realistic EventBridge event with detail as dict."""
    return {
        "version": "0",
        "id": "event-id-123",
        "detail-type": "ExportRequested",
        "source": "demo.exports",
        "account": "123456789012",
        "time": "2024-01-01T12:00:00Z",
        "region": "us-east-1",
        "resources": [],
        "detail": {
            "export_type": "report",
            "user_id": "test-user-456",
        },
    }


@pytest.fixture
def event_bridge_event_json() -> dict[str, Any]:
    """Provide a realistic EventBridge event with detail as JSON string."""
    return {
        "version": "0",
        "id": "event-id-456",
        "detail-type": "ExportRequested",
        "source": "demo.exports",
        "account": "123456789012",
        "time": "2024-01-01T12:00:00Z",
        "region": "us-east-1",
        "resources": [],
        "detail": json.dumps(
            {
                "export_type": "analytics",
                "user_id": "test-user-789",
            }
        ),
    }


def test_lambda_handler_success_with_dict_detail(
    event_bridge_event_dict: dict[str, Any],
    lambda_context: FakeLambdaContext,
) -> None:
    """Test successful Lambda invocation with detail as dict."""
    response = lambda_handler(event_bridge_event_dict, lambda_context)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["status"] == "success"
    assert body["request_id"] == "test-request-id-12345"
    assert body["export_type"] == "report"
    assert body["user_id"] == "test-user-456"


def test_lambda_handler_success_with_json_detail(
    event_bridge_event_json: dict[str, Any],
    lambda_context: FakeLambdaContext,
) -> None:
    """Test successful Lambda invocation with detail as JSON string."""
    response = lambda_handler(event_bridge_event_json, lambda_context)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["status"] == "success"
    assert body["request_id"] == "test-request-id-12345"
    assert body["export_type"] == "analytics"
    assert body["user_id"] == "test-user-789"


def test_lambda_handler_force_failure(
    event_bridge_event_dict: dict[str, Any],
    lambda_context: FakeLambdaContext,
) -> None:
    """Test Lambda invocation with force_failure flag (should raise)."""
    event_bridge_event_dict["detail"]["force_failure"] = True

    with pytest.raises(ValueError, match="Forced failure for demo purposes"):
        lambda_handler(event_bridge_event_dict, lambda_context)


def test_lambda_handler_missing_detail_fields(
    lambda_context: FakeLambdaContext,
) -> None:
    """Test Lambda invocation with minimal event (missing optional fields)."""
    minimal_event = {
        "version": "0",
        "id": "event-id-minimal",
        "detail-type": "UnknownType",
        "source": "unknown.source",
        "detail": {},
    }

    response = lambda_handler(minimal_event, lambda_context)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["status"] == "success"
    assert body["request_id"] == "test-request-id-12345"
    assert body["export_type"] == "unknown"
    assert body["user_id"] == "anonymous"
