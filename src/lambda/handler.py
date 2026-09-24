"""
Event processor Lambda handler.
Processes events from EventBridge, with failure handling to SQS.
"""

import json
import logging
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Process EventBridge events.

    Args:
        event: EventBridge event payload
        context: Lambda context object

    Returns:
        Response dict with statusCode and body

    Raises:
        ValueError: If event processing should fail (triggers SQS delivery)
    """
    request_id = context.aws_request_id
    logger.info(f"Processing event {request_id}")
    logger.info(f"Event: {json.dumps(event)}")

    try:
        detail_raw = event.get("detail", {})
        if isinstance(detail_raw, str):
            detail = json.loads(detail_raw)
        else:
            detail = detail_raw

        detail_type = event.get("detail-type", "Unknown")
        source = event.get("source", "Unknown")

        logger.info(
            f"Event details - Source: {source}, Type: {detail_type}, "
            f"Detail: {json.dumps(detail)}"
        )

        force_failure = detail.get("force_failure", False)

        if force_failure:
            logger.warning(f"Forced failure requested for event {request_id}")
            raise ValueError("Forced failure for demo purposes")

        export_type = detail.get("export_type", "unknown")
        user_id = detail.get("user_id", "anonymous")

        logger.info(
            f"Successfully processed {export_type} export "
            f"for user {user_id} (request_id={request_id})"
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "success",
                    "request_id": request_id,
                    "export_type": export_type,
                    "user_id": user_id,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Failed to process event {request_id}: {e!s}")
        raise
