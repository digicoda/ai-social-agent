from __future__ import annotations

from pathlib import Path

import httpx

from .publishing import PublishingError


class LinkedInMediaClient:
    endpoint = "https://api.linkedin.com/rest/images"

    def __init__(self, token: str, author: str, version: str, timeout: float) -> None:
        self.token = token
        self.author = author
        self.version = version
        self.timeout = timeout

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Linkedin-Version": self.version,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def upload_image(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.is_file():
            raise PublishingError(f"image file not found: {image_path}", retryable=False)
        content = path.read_bytes()
        if not content:
            raise PublishingError("image file is empty", retryable=False)
        try:
            response = httpx.post(
                self.endpoint,
                headers=self._headers("application/octet-stream"),
                params={"owner": self.author},
                content=content,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise PublishingError(
                f"LinkedIn image upload failed with HTTP {status}",
                retryable=status in {408, 409, 429} or status >= 500,
            ) from exc
        except httpx.RequestError as exc:
            raise PublishingError(f"LinkedIn image upload request failed: {exc}", retryable=True) from exc
        image_urn = response.headers.get("x-restli-id", "")
        if not image_urn:
            raise PublishingError("LinkedIn did not return an image URN", retryable=True)
        return image_urn
