#!/usr/bin/env python3
"""
Peek at messages in the SQS failure queue without deleting them.
"""

import argparse
import json
import sys
from typing import Optional

import boto3
from botocore.exceptions import ClientError


def peek_queue(
    queue_url: str,
    max_messages: int = 10,
    region: Optional[str] = None,
    delete: bool = False,
) -> None:
    """
    Peek at messages in an SQS queue.

    Args:
        queue_url: SQS queue URL
        max_messages: Maximum number of messages to retrieve (1-10)
        region: AWS region (optional)
        delete: Whether to delete messages after reading
    """
    sqs_client = boto3.client("sqs", region_name=region)

    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=min(max_messages, 10),
        WaitTimeSeconds=5,
        AttributeNames=["All"],
        MessageAttributeNames=["All"],
    )

    messages = response.get("Messages", [])

    if not messages:
        print("✓ Queue is empty (no messages received)")
        return

    print(f"Found {len(messages)} message(s):\n")

    for i, msg in enumerate(messages, 1):
        print(f"Message {i}:")
        print(f"  ID: {msg['MessageId']}")
        print(f"  Receipt Handle: {msg['ReceiptHandle'][:50]}...")

        attributes = msg.get("Attributes", {})
        if attributes:
            print(f"  Sent: {attributes.get('SentTimestamp')}")
            print(f"  Receive count: {attributes.get('ApproximateReceiveCount')}")

        try:
            body = json.loads(msg["Body"])
            print(f"  Body:")
            print(json.dumps(body, indent=4))
        except json.JSONDecodeError:
            print(f"  Body (raw): {msg['Body']}")

        if delete:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=msg["ReceiptHandle"],
            )
            print(f"  ✓ Deleted")

        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Peek at SQS queue messages (non-destructive by default)"
    )
    parser.add_argument(
        "--queue-url",
        required=True,
        help="SQS queue URL (from terraform output)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=10,
        help="Maximum messages to retrieve (1-10, default: 10)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete messages after reading (use with caution)",
    )
    parser.add_argument(
        "--region",
        help="AWS region (uses default if not specified)",
    )
    args = parser.parse_args()

    try:
        if args.delete:
            confirm = input(
                "⚠ This will DELETE messages from the queue. Continue? (yes/no): "
            )
            if confirm.lower() not in ("yes", "y"):
                print("Cancelled.")
                return 0

        peek_queue(
            queue_url=args.queue_url,
            max_messages=args.max_messages,
            region=args.region,
            delete=args.delete,
        )
        return 0

    except ClientError as e:
        print(f"\n✗ AWS error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
