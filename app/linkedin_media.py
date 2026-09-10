from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from .publishing import PublishingError


class LinkedInMediaClient:
    """Upload and verify LinkedIn image assets using the current Images API."""

    endpoint = "https://api.linkedin.com/rest/images"

    def __init__(
        self,
        token: str,
        author: str,
        version: str,
        timeout: float,
        poll_attempts: int = 10,
        poll_seconds: float = 1.0,
    ) -> None:
        self.token = token
        self.author = author
        self.version = version
        self.timeout = timeout
        self.poll_attempts = max(1, poll_attempts)
        self.poll_seconds = max(0.0, poll_seconds)

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Linkedin-Version": self.version,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    @staticmethod
    def _retryable(status: int) -> bool:
        return status in {408, 409, 429} or status >= 500

    def _raise_http_error(self, action: str, exc: httpx.HTTPStatusError) -> None:
        status = exc.response.status_code
        raise PublishingError(
            f"LinkedIn image {action} failed with HTTP {status}",
            retryable=self._retryable(status),
        ) from exc

    def _initialize_upload(self) -> tuple[str, str]:
        try:
            response = httpx.post(
                self.endpoint,
                params={"action": "initializeUpload"},
                headers=self._headers("application/json"),
                json={"initializeUploadRequest": {"owner": self.author}},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_http_error("initialization", exc)
        except httpx.RequestError as exc:
            raise PublishingError(f"LinkedIn image initialization request failed: {exc}", retryable=True) from exc

        try:
            value = response.json()["value"]
            upload_url = value["uploadUrl"]
            image_urn = value["image"]
        except (TypeError, KeyError, ValueError) as exc:
            raise PublishingError("LinkedIn image initialization returned an invalid response", retryable=True) from exc

        if not upload_url or not image_urn:
            raise PublishingError("LinkedIn image initialization did not return uploadUrl and image", retryable=True)
        return upload_url, image_urn

    def _upload(self, upload_url: str, content: bytes, content_type: str) -> None:
        try:
            response = httpx.put(
                upload_url,
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": content_type},
                content=content,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_http_error("upload", exc)
        except httpx.RequestError as exc:
            raise PublishingError(f"LinkedIn image upload request failed: {exc}", retryable=True) from exc

    def _wait_until_available(self, image_urn: str) -> None:
        url = f"{self.endpoint}/{quote(image_urn, safe='')}"
        last_status = ""
        for attempt in range(self.poll_attempts):
            try:
                response = httpx.get(
                    url,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_http_error("status check", exc)
            except httpx.RequestError as exc:
                raise PublishingError(f"LinkedIn image status request failed: {exc}", retryable=True) from exc

            try:
                last_status = str(response.json().get("status", ""))
            except (TypeError, ValueError) as exc:
                raise PublishingError("LinkedIn image status returned an invalid response", retryable=True) from exc

            if last_status == "AVAILABLE":
                return
            if last_status in {"PROCESSING_FAILED", "FAILED"}:
                raise PublishingError(
                    f"LinkedIn image processing failed with status {last_status}",
                    retryable=False,
                )

            if attempt < self.poll_attempts - 1 and self.poll_seconds:
                time.sleep(self.poll_seconds)

        raise PublishingError(
            f"LinkedIn image did not become available (last status: {last_status or 'unknown'})",
            retryable=True,
        )

    def upload_image(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.is_file():
            raise PublishingError(f"image file not found: {image_path}", retryable=False)
        content = path.read_bytes()
        if not content:
            raise PublishingError("image file is empty", retryable=False)

        content_type, _ = mimetypes.guess_type(path.name)
        if content_type not in {"image/jpeg", "image/png", "image/gif"}:
            raise PublishingError(
                "LinkedIn Images API supports JPEG, PNG, and GIF files",
                retryable=False,
            )

        upload_url, image_urn = self._initialize_upload()
        self._upload(upload_url, content, content_type)
        self._wait_until_available(image_urn)
        return image_urn
