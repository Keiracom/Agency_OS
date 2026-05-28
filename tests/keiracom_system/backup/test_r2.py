"""Tests for the R2 client wrapper (mock boto3 — no network)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.keiracom_system.backup import r2


class FakeBoto:
    def __init__(self, pages: list[dict]) -> None:
        self._pages = pages
        self.uploaded: list[tuple] = []
        self.downloaded: list[tuple] = []
        self.deleted: list[tuple] = []

    def upload_file(self, local: str, bucket: str, key: str) -> None:
        self.uploaded.append((local, bucket, key))

    def download_file(self, bucket: str, key: str, local: str) -> None:
        self.downloaded.append((bucket, key, local))

    def delete_object(self, *, Bucket: str, Key: str) -> None:  # noqa: N803 boto3 kwarg casing
        self.deleted.append((Bucket, Key))

    def list_objects_v2(self, **_kwargs: object) -> dict:
        return self._pages.pop(0)


def test_r2_endpoint():
    assert r2.r2_endpoint("abc123") == "https://abc123.r2.cloudflarestorage.com"


def test_missing_bucket_raises():
    with pytest.raises(r2.R2ConfigError):
        r2.R2Client(client=FakeBoto([]), bucket="")


def test_upload_download_delete_delegate():
    fake = FakeBoto([])
    client = r2.R2Client(client=fake, bucket="bk")
    client.upload_file("/tmp/x", "weaviate/x")
    client.download_file("weaviate/x", "/tmp/y")
    client.delete_object("weaviate/x")
    assert fake.uploaded == [("/tmp/x", "bk", "weaviate/x")]
    assert fake.downloaded == [("bk", "weaviate/x", "/tmp/y")]
    assert fake.deleted == [("bk", "weaviate/x")]


def test_list_objects_paginates():
    dt = datetime(2026, 6, 1, tzinfo=UTC)
    pages = [
        {
            "Contents": [{"Key": "p/a", "LastModified": dt, "Size": 10}],
            "IsTruncated": True,
            "NextContinuationToken": "tok",
        },
        {
            "Contents": [{"Key": "p/b", "LastModified": dt, "Size": 20}],
            "IsTruncated": False,
        },
    ]
    client = r2.R2Client(client=FakeBoto(pages), bucket="bk")
    objs = client.list_objects("p/")
    assert [o.key for o in objs] == ["p/a", "p/b"]
    assert objs[1].size == 20


def test_list_objects_empty():
    client = r2.R2Client(client=FakeBoto([{"IsTruncated": False}]), bucket="bk")
    assert client.list_objects("p/") == []
