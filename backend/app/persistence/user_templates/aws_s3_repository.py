"""AWS S3 storage for user template version payloads (future production swap)."""

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger("user_template_storage")


class AwsS3UserTemplateRepository:
    backend_name = "aws_s3"

    def __init__(self) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for USER_TEMPLATE_STORAGE=aws_s3. "
                "Install boto3 or use supabase/local storage."
            ) from exc

        if not settings.aws_s3_bucket:
            raise RuntimeError("AWS_S3_BUCKET is required for USER_TEMPLATE_STORAGE=aws_s3")

        self._bucket = settings.aws_s3_bucket
        self._client = boto3.client("s3", region_name=settings.aws_s3_region or None)
        self._prefix = settings.aws_s3_user_templates_prefix.strip("/")

    def build_storage_key(self, scope_type: str, scope_id: str, version_id: str) -> str:
        name = f"{scope_type}s/{scope_id}/{version_id}.json"
        if self._prefix:
            return f"{self._prefix}/{name}"
        return name

    def save_version(self, storage_key: str, payload: dict[str, Any]) -> str:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self._client.put_object(
            Bucket=self._bucket,
            Key=storage_key,
            Body=body,
            ContentType="application/json",
        )
        return storage_key

    def load_version(self, storage_key: str) -> dict[str, Any]:
        response = self._client.get_object(Bucket=self._bucket, Key=storage_key)
        return json.loads(response["Body"].read().decode("utf-8"))

    def delete_version(self, storage_key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=storage_key)
