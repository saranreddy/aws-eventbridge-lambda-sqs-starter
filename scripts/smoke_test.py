#!/usr/bin/env python3
"""
Smoke test for EventBridge + Lambda + SQS stack.
Post-deployment validation that the happy path works.
"""

import argparse
import json
import sys
import time

import boto3
from botocore.exceptions import ClientError


def wait_for_log_events(
    log_group: str,
    lambda_name: str,
    search_term: str,
    timeout: int = 60,
    region: str | None = None,
) -> bool:
    """
    Wait for a specific log event to appear in CloudWatch Logs.

    Args:
        log_group: CloudWatch log group name
        lambda_name: Lambda function name (for display)
        search_term: Term to search for in logs
        timeout: Maximum seconds to wait
        region: AWS region

    Returns:
        True if found, False if timeout
    """
    logs_client = boto3.client("logs", region_name=region)
    start_time = time.time()

    print(f"Waiting for Lambda execution (timeout: {timeout}s)...", end="", flush=True)

    while time.time() - start_time < timeout:
        try:
            response = logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=int((time.time() - 120) * 1000),
                filterPattern=search_term,
            )

            if response.get("events"):
                print(" found!")
                return True

        except ClientError as e:
            if "ResourceNotFoundException" in str(e):
                pass
            else:
                raise

        print(".", end="", flush=True)
        time.sleep(2)

    print(" timeout!")
    return False


def check_dlq_empty(queue_url: str, region: str | None = None) -> bool:
    """
    Check that the DLQ is empty (no unexpected failures).

    Args:
        queue_url: DLQ URL
        region: AWS region

    Returns:
        True if empty, False if messages present
    """
    sqs_client = boto3.client("sqs", region_name=region)

    response = sqs_client.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages"],
    )

    count = int(response["Attributes"]["ApproximateNumberOfMessages"])
    return count == 0


def run_smoke_test(
    bus_name: str,
    lambda_name: str,
    log_group: str,
    dlq_url: str,
    region: str | None = None,
) -> bool:
    """
    Run smoke test: send event, verify Lambda execution, check no DLQ buildup.

    Returns:
        True if all checks pass
    """
    events_client = boto3.client("events", region_name=region)

    print("=" * 60)
    print("EventBridge + Lambda + SQS Smoke Test")
    print("=" * 60)

    test_id = f"smoke-test-{int(time.time())}"

    print(f"\n1. Sending test event (ID: {test_id})...")
    detail = {
        "export_type": "smoke-test",
        "user_id": test_id,
        "force_failure": False,
    }

    response = events_client.put_events(
        Entries=[
            {
                "Source": "demo.exports",
                "DetailType": "ExportRequested",
                "Detail": json.dumps(detail),
                "EventBusName": bus_name,
            }
        ]
    )

    if response["FailedEntryCount"] > 0:
        print(f"✗ Failed to send event: {response}")
        return False

    event_id = response["Entries"][0]["EventId"]
    print(f"✓ Event sent (ID: {event_id})")

    print("\n2. Verifying Lambda execution...")
    found = wait_for_log_events(
        log_group=log_group,
        lambda_name=lambda_name,
        search_term=test_id,
        timeout=60,
        region=region,
    )

    if not found:
        print(f"✗ Lambda execution not detected in {log_group}")
        print("  Check CloudWatch Logs manually")
        return False

    print("✓ Lambda processed event successfully")

    print("\n3. Checking DLQ for unexpected failures...")
    dlq_empty = check_dlq_empty(dlq_url, region=region)

    if not dlq_empty:
        print("⚠ DLQ is not empty - there may be failures")
        print(f"  Run: python scripts/peek_queue.py --queue-url {dlq_url}")
    else:
        print("✓ DLQ is empty (no unexpected failures)")

    print("\n" + "=" * 60)

    if found and dlq_empty:
        print("✓ Smoke test PASSED")
        return True
    else:
        print("✗ Smoke test FAILED")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run smoke test for EventBridge + Lambda + SQS stack"
    )
    parser.add_argument(
        "--bus-name",
        required=True,
        help="EventBridge bus name",
    )
    parser.add_argument(
        "--lambda-name",
        required=True,
        help="Lambda function name",
    )
    parser.add_argument(
        "--log-group",
        required=True,
        help="Lambda CloudWatch log group name",
    )
    parser.add_argument(
        "--dlq-url",
        required=True,
        help="Dead letter queue URL",
    )
    parser.add_argument(
        "--region",
        help="AWS region",
    )
    args = parser.parse_args()

    try:
        passed = run_smoke_test(
            bus_name=args.bus_name,
            lambda_name=args.lambda_name,
            log_group=args.log_group,
            dlq_url=args.dlq_url,
            region=args.region,
        )
        return 0 if passed else 1

    except ClientError as e:
        print(f"\n✗ AWS error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
