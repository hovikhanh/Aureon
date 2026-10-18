"""MinIO / S3 compatible storage service with AWS Signature V4 support (T-007, T-202).

Provides upload, download, deletion, and presigned URL generation (default 15 minutes)
without adding external heavy dependencies (uses Python standard library + httpx).
Matches docs/3.EXECUTION/07-TECH-ARCHITECTURE.md §4 and docs/2.PRODUCT/04-IDP-FEATURE-SPEC.md §8.
"""

import hashlib
import hmac
import logging
import urllib.parse
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_config

logger = logging.getLogger(__name__)


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    return _sign(k_service, "aws4_request")


class StorageService:
    """Service for managing files in MinIO/S3 object storage."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        cfg = get_config()
        self.endpoint = (endpoint or cfg.s3_endpoint).rstrip("/")
        self.access_key = access_key or cfg.s3_access_key.get_secret_value()
        self.secret_key = secret_key or cfg.s3_secret_key.get_secret_value()
        self.bucket = bucket or cfg.s3_bucket
        self.region = region

    def _auth_headers(
        self, method: str, path: str, query: str = "", payload: bytes = b""
    ) -> dict[str, str]:
        """Generate AWS SigV4 authorization headers."""
        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        parsed_url = urllib.parse.urlparse(self.endpoint)
        host = parsed_url.netloc

        payload_hash = hashlib.sha256(payload).hexdigest()
        canonical_uri = path
        canonical_querystring = query

        canonical_headers = (
            f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"

        canonical_request = (
            f"{method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = _get_signature_key(self.secret_key, date_stamp, self.region, "s3")
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        auth_header = (
            f"{algorithm} Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        return {
            "Host": host,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": payload_hash,
            "Authorization": auth_header,
        }

    def ensure_bucket_exists(self) -> None:
        """Create the target bucket if it doesn't already exist."""
        path = f"/{self.bucket}"
        headers = self._auth_headers("HEAD", path)
        with httpx.Client(timeout=10.0) as client:
            resp = client.head(f"{self.endpoint}{path}", headers=headers)
            if resp.status_code == 404:
                # Create bucket
                put_headers = self._auth_headers("PUT", path)
                put_resp = client.put(f"{self.endpoint}{path}", headers=put_headers)
                if put_resp.status_code not in (200, 204):
                    msg = f"Failed to create bucket {self.bucket}: {put_resp.text}"
                    raise RuntimeError(msg)

    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw bytes to MinIO/S3 and return the object storage key."""
        clean_key = key.lstrip("/")
        path = f"/{self.bucket}/{clean_key}"
        headers = self._auth_headers("PUT", path, payload=data)
        headers["Content-Type"] = content_type

        with httpx.Client(timeout=30.0) as client:
            resp = client.put(f"{self.endpoint}{path}", headers=headers, content=data)
            if resp.status_code not in (200, 201, 204):
                msg = f"Failed to upload object {key}: {resp.status_code} {resp.text}"
                raise RuntimeError(msg)
        return clean_key

    def get_object(self, key: str) -> bytes:
        """Download raw bytes of an object from MinIO/S3."""
        clean_key = key.lstrip("/")
        path = f"/{self.bucket}/{clean_key}"
        headers = self._auth_headers("GET", path)

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.endpoint}{path}", headers=headers)
            if resp.status_code == 404:
                msg = f"Object not found: {key}"
                raise FileNotFoundError(msg)
            if resp.status_code != 200:
                msg = f"Failed to get object {key}: {resp.status_code} {resp.text}"
                raise RuntimeError(msg)
            return resp.content

    def delete_object(self, key: str) -> None:
        """Delete an object from MinIO/S3."""
        clean_key = key.lstrip("/")
        path = f"/{self.bucket}/{clean_key}"
        headers = self._auth_headers("DELETE", path)

        with httpx.Client(timeout=10.0) as client:
            resp = client.delete(f"{self.endpoint}{path}", headers=headers)
            if resp.status_code not in (200, 204, 404):
                msg = f"Failed to delete object {key}: {resp.status_code} {resp.text}"
                raise RuntimeError(msg)

    def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 900,
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL using AWS Signature Version 4 query parameters (default 15m)."""
        clean_key = key.lstrip("/")
        path = f"/{self.bucket}/{clean_key}"

        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        parsed_url = urllib.parse.urlparse(self.endpoint)
        host = parsed_url.netloc

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        credential = f"{self.access_key}/{credential_scope}"

        query_params: dict[str, Any] = {
            "X-Amz-Algorithm": algorithm,
            "X-Amz-Credential": credential,
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires_in),
            "X-Amz-SignedHeaders": "host",
        }

        canonical_querystring = urllib.parse.urlencode(sorted(query_params.items()))
        canonical_headers = f"host:{host}\n"
        signed_headers = "host"
        payload_hash = "UNSIGNED-PAYLOAD"

        canonical_request = (
            f"{method}\n"
            f"{path}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = _get_signature_key(self.secret_key, date_stamp, self.region, "s3")
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return f"{self.endpoint}{path}?{canonical_querystring}&X-Amz-Signature={signature}"


@lru_cache
def get_storage_service() -> StorageService:
    """Return singleton StorageService instance."""
    service = StorageService()
    try:
        service.ensure_bucket_exists()
    except Exception as exc:
        logger.warning("Could not auto-ensure MinIO bucket exists: %s", exc)
    return service
