"""r2.py — thin Cloudflare R2 (S3-compatible) client over boto3.

R2 exposes the S3 API at https://{account_id}.r2.cloudflarestorage.com. Credentials
come from env (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
R2_BACKUP_BUCKET) so nothing secret lives in the repo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class R2ConfigError(RuntimeError):
    """Raised when required R2_* env vars are missing."""


@dataclass(frozen=True)
class R2Object:
    key: str
    last_modified: datetime
    size: int


def r2_endpoint(account_id: str) -> str:
    """The S3 API endpoint for an R2 account."""
    return f"https://{account_id}.r2.cloudflarestorage.com"


class R2Client:
    """Minimal R2 wrapper: upload / list / delete / download for one bucket."""

    def __init__(self, *, client: Any | None = None, bucket: str | None = None) -> None:
        self.bucket = bucket or os.environ.get("R2_BACKUP_BUCKET", "")
        self._client = client if client is not None else self._build_client()
        if not self.bucket:
            raise R2ConfigError("R2_BACKUP_BUCKET is required")

    @staticmethod
    def _build_client() -> Any:
        account = os.environ.get("R2_ACCOUNT_ID", "")
        key_id = os.environ.get("R2_ACCESS_KEY_ID", "")
        secret = os.environ.get("R2_SECRET_ACCESS_KEY", "")
        missing = [
            name
            for name, val in (
                ("R2_ACCOUNT_ID", account),
                ("R2_ACCESS_KEY_ID", key_id),
                ("R2_SECRET_ACCESS_KEY", secret),
            )
            if not val
        ]
        if missing:
            raise R2ConfigError(f"missing R2 env vars: {', '.join(missing)}")
        import boto3  # local import — keeps callers that inject a client boto3-free

        return boto3.client(
            "s3",
            endpoint_url=r2_endpoint(account),
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            region_name="auto",  # R2 ignores region but boto3 requires one
        )

    def upload_file(self, local_path: str, key: str) -> None:
        self._client.upload_file(local_path, self.bucket, key)

    def download_file(self, key: str, local_path: str) -> None:
        self._client.download_file(self.bucket, key, local_path)

    def list_objects(self, prefix: str) -> list[R2Object]:
        """All objects under `prefix`, paginated."""
        out: list[R2Object] = []
        token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = self._client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []) or []:
                out.append(
                    R2Object(
                        key=obj["Key"],
                        last_modified=obj["LastModified"],
                        size=int(obj.get("Size", 0)),
                    )
                )
            if not resp.get("IsTruncated"):
                return out
            token = resp.get("NextContinuationToken")

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)
