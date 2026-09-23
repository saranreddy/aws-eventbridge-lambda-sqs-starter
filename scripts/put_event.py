#!/usr/bin/env python3
"""
Put a custom event to EventBridge.
"""

import argparse
import json
import sys

import boto3
from botocore.exceptions import ClientError


def put_event(
    bus_name: str,
    export_type: str,
    user_id: str,
    force_failure: bool,
    region: str | None = None,
) -> dict:
    """
    Put an export request event to EventBridge.

    Args:
        bus_name: EventBridge bus name
        export_type: Type of export (e.g., 'report', 'data', 'analytics')
        user_id: User ID requesting the export
        force_failure: Whether to force Lambda failure for demo
        region: AWS region (optional, uses default if not specified)

    Returns:
        Response from EventBridge PutEvents
    """
    events_client = boto3.client("events", region_name=region)

    detail = {
        "export_type": export_type,
        "user_id": user_id,
        "force_failure": force_failure,
    }

    entry = {
        "Source": "demo.exports",
        "DetailType": "ExportRequested",
        "Detail": json.dumps(detail),
        "EventBusName": bus_name,
    }

    response = events_client.put_events(Entries=[entry])

    if response["FailedEntryCount"] > 0:
        raise RuntimeError(f"Failed to put event: {response['Entries']}")

    return response


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Put an export request event to EventBridge"
    )
    parser.add_argument(
        "--bus-name",
        required=True,
        help="EventBridge bus name (from terraform output)",
    )
    parser.add_argument(
        "--export-type",
        default="report",
        help="Export type (default: report)",
    )
    parser.add_argument(
        "--user-id",
        default="demo-user",
        help="User ID (default: demo-user)",
    )
    parser.add_argument(
        "--force-failure",
        action="store_true",
        help="Force Lambda failure to demonstrate SQS/DLQ flow",
    )
    parser.add_argument(
        "--region",
        help="AWS region (uses default if not specified)",
    )
    args = parser.parse_args()

    try:
        print(f"Putting event to bus: {args.bus_name}")
        print(f"  Export type: {args.export_type}")
        print(f"  User ID: {args.user_id}")
        print(f"  Force failure: {args.force_failure}")

        response = put_event(
            bus_name=args.bus_name,
            export_type=args.export_type,
            user_id=args.user_id,
            force_failure=args.force_failure,
            region=args.region,
        )

        print("\n✓ Event sent successfully!")
        print(f"  Event ID: {response['Entries'][0]['EventId']}")

        if args.force_failure:
            print("\n⚠ Failure forced - check SQS queue after Lambda retries exhaust")
        else:
            print("\n✓ Check Lambda logs for processing confirmation")

        return 0

    except ClientError as e:
        print(f"\n✗ AWS error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
