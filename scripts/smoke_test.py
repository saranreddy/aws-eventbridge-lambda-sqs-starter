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
    cloudwatch_client = boto3.client("cloudwatch", region_name=region)
    start_time = time.time()

    # Quote the search term for CloudWatch filter pattern
    # This is critical for terms containing hyphens or special characters
    filter_pattern = f'"{search_term}"'

    print(f"Waiting for Lambda execution (timeout: {timeout}s)...", end="", flush=True)

    while time.time() - start_time < timeout:
        try:
            response = logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=int((time.time() - 120) * 1000),
                filterPattern=filter_pattern,
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

    # Provide diagnostic information on timeout
    print("\n  Diagnostic information:")
    try:
        # Check if any log streams exist
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy="LastEventTime",
            descending=True,
            limit=5,
        )
        stream_count = len(streams_response.get("logStreams", []))
        print(f"    - Log streams in group: {stream_count}")

        if stream_count > 0:
            latest_stream = streams_response["logStreams"][0]
            last_event_time = latest_stream.get("lastEventTime", 0)
            if last_event_time:
                time_ago = int(time.time() * 1000 - last_event_time) // 1000
                print(f"    - Most recent log event: {time_ago}s ago")

            # Dump recent log events to help diagnose
            print("\n    Recent log events (last 2 minutes):")
            try:
                recent_logs = logs_client.filter_log_events(
                    logGroupName=log_group,
                    startTime=int((time.time() - 120) * 1000),
                    limit=50,
                )
                events = recent_logs.get("events", [])
                if events:
                    for log_event in events[:20]:
                        print(f"      {log_event.get('message', '').rstrip()}")
                else:
                    print("      (no log events found)")
            except ClientError as e:
                print(f"      Could not retrieve log events: {e}")
    except ClientError:
        print("    - Could not retrieve log stream info")

    # Check Lambda invocation metrics
    try:
        end_time = int(time.time())
        start_metric_time = end_time - 300  # Last 5 minutes

        invocations_response = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Invocations",
            Dimensions=[{"Name": "FunctionName", "Value": lambda_name}],
            StartTime=start_metric_time,
            EndTime=end_time,
            Period=60,
            Statistics=["Sum"],
        )

        errors_response = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Errors",
            Dimensions=[{"Name": "FunctionName", "Value": lambda_name}],
            StartTime=start_metric_time,
            EndTime=end_time,
            Period=60,
            Statistics=["Sum"],
        )

        total_invocations = sum(
            point["Sum"] for point in invocations_response.get("Datapoints", [])
        )
        total_errors = sum(
            point["Sum"] for point in errors_response.get("Datapoints", [])
        )

        print(f"    - Lambda invocations (last 5m): {int(total_invocations)}")
        print(f"    - Lambda errors (last 5m): {int(total_errors)}")

        if total_invocations == 0:
            print(
                "    ⚠ No Lambda invocations detected - check EventBridge rule/pattern"
            )
        elif total_errors > 0:
            print("    ✗ Lambda errors detected - check logs above for error messages")
    except ClientError:
        print("    - Could not retrieve Lambda metrics")

    print(f"    - Suggestion: Check CloudWatch Logs manually at {log_group}")
    print("    - Verify EventBridge rule matches event source/detail-type")

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

    print("✓ Lambda log entry found")

    # Check for errors in recent invocations
    print("\n3. Checking for Lambda errors...")
    cloudwatch_client = boto3.client("cloudwatch", region_name=region)
    end_time = int(time.time())
    start_metric_time = end_time - 120  # Last 2 minutes

    try:
        errors_response = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Errors",
            Dimensions=[{"Name": "FunctionName", "Value": lambda_name}],
            StartTime=start_metric_time,
            EndTime=end_time,
            Period=60,
            Statistics=["Sum"],
        )
        total_errors = sum(
            point["Sum"] for point in errors_response.get("Datapoints", [])
        )

        if total_errors > 0:
            print(
                f"✗ Lambda errors detected: {int(total_errors)} "
                f"error(s) in last 2 minutes"
            )
            print("  Check CloudWatch Logs for error details")
            return False
        else:
            print("✓ No Lambda errors detected")
    except ClientError as e:
        print(f"⚠ Could not check Lambda errors: {e}")
        print("  Proceeding with caution...")

    print("\n4. Checking DLQ for unexpected failures...")
    dlq_empty = check_dlq_empty(dlq_url, region=region)

    if not dlq_empty:
        print("⚠ DLQ is not empty - there may be failures")
        print(f"  Run: python scripts/peek_queue.py --queue-url {dlq_url}")
    else:
        print("✓ DLQ is empty (no unexpected failures)")

    print("\n" + "=" * 60)
    print("✓ Smoke test PASSED")
    return True


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
