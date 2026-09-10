from __future__ import annotations

import mimetypes
import time
from pathlib import Path

import httpx

from .errors import PublishingError


class LinkedInVideoClient:
    """Upload and verify LinkedIn video assets using the Videos API."""

    endpoint = "https://api.linkedin.com/rest/videos"
    supported_types = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}

    def __init__(
        self,
        token: str,
        owner: str,
        version: str,
        timeout: float,
        poll_attempts: int = 10,
        poll_seconds: float = 1.0,
    ) -> None:
        self.token = token
        self.owner = owner
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
            f"LinkedIn video {action} failed with HTTP {status}",
            retryable=self._retryable(status),
        ) from exc

    def _initialize_upload(self, file_size: int) -> tuple[str, list[dict[str, int | str]], str]:
        try:
            response = httpx.post(
                self.endpoint,
                params={"action": "initializeUpload"},
                headers=self._headers("application/json"),
                json={
                    "initializeUploadRequest": {
                        "owner": self.owner,
                        "fileSizeBytes": file_size,
                        "uploadCaptions": False,
                        "uploadThumbnail": False,
                    }
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_http_error("initialization", exc)
        except httpx.RequestError as exc:
            raise PublishingError(f"LinkedIn video initialization request failed: {exc}", retryable=True) from exc

        try:
            value = response.json()["value"]
            video_urn = str(value["video"])
            token = str(value.get("uploadToken", ""))
            instructions = value["uploadInstructions"]
            if not instructions:
                raise ValueError("uploadInstructions is empty")
            normalized = [
                {
                    "uploadUrl": str(item["uploadUrl"]),
                    "firstByte": int(item["firstByte"]),
                    "lastByte": int(item["lastByte"]),
                }
                for item in instructions
            ]
        except (TypeError, KeyError, ValueError) as exc:
            raise PublishingError("LinkedIn video initialization returned an invalid response", retryable=True) from exc

        return video_urn, normalized, token

    def _upload_part(self, upload_url: str, content: bytes, first_byte: int, last_byte: int) -> str:
        try:
            response = httpx.put(
                upload_url,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Range": f"bytes {first_byte}-{last_byte}/*",
                },
                content=content,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_http_error("part upload", exc)
        except httpx.RequestError as exc:
            raise PublishingError(f"LinkedIn video part upload request failed: {exc}", retryable=True) from exc

        etag = response.headers.get("etag", "").strip('"')
        if not etag:
            raise PublishingError("LinkedIn video part upload did not return an ETag", retryable=True)
        return etag

    def _finalize_upload(self, video_urn: str, upload_token: str, part_ids: list[str]) -> None:
        try:
            response = httpx.post(
                self.endpoint,
                params={"action": "finalizeUpload"},
                headers=self._headers("application/json"),
                json={
                    "finalizeUploadRequest": {
                        "video": video_urn,
                        "uploadToken": upload_token,
                        "uploadedPartIds": part_ids,
                    }
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_http_error("finalization", exc)
        except httpx.RequestError as exc:
            raise PublishingError(f"LinkedIn video finalization request failed: {exc}", retryable=True) from exc

    def _wait_until_available(self, video_urn: str) -> None:
        url = f"{self.endpoint}/{video_urn}"
        last_status = ""
        for attempt in range(self.poll_attempts):
            try:
                response = httpx.get(url, headers=self._headers(), timeout=self.timeout)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_http_error("status check", exc)
            except httpx.RequestError as exc:
                raise PublishingError(f"LinkedIn video status request failed: {exc}", retryable=True) from exc

            try:
                last_status = str(response.json().get("status", ""))
            except (TypeError, ValueError) as exc:
                raise PublishingError("LinkedIn video status returned an invalid response", retryable=True) from exc

            if last_status == "AVAILABLE":
                return
            if last_status in {"PROCESSING_FAILED", "FAILED"}:
                raise PublishingError(f"LinkedIn video processing failed with status {last_status}", retryable=False)
            if attempt < self.poll_attempts - 1 and self.poll_seconds:
                time.sleep(self.poll_seconds)

        raise PublishingError(
            f"LinkedIn video did not become available (last status: {last_status or 'unknown'})",
            retryable=True,
        )

    def upload_video(self, video_path: str) -> str:
        path = Path(video_path)
        if not path.is_file():
            raise PublishingError(f"video file not found: {video_path}", retryable=False)
        file_size = path.stat().st_size
        if file_size <= 0:
            raise PublishingError("video file is empty", retryable=False)
        content_type, _ = mimetypes.guess_type(path.name)
        if content_type not in self.supported_types:
            raise PublishingError("LinkedIn Videos API supports common video files such as MP4, MOV, AVI, and WebM", retryable=False)

        video_urn, instructions, upload_token = self._initialize_upload(file_size)
        part_ids: list[str] = []
        with path.open("rb") as handle:
            for instruction in instructions:
                first_byte = int(instruction["firstByte"])
                last_byte = int(instruction["lastByte"])
                expected_size = last_byte - first_byte + 1
                handle.seek(first_byte)
                chunk = handle.read(expected_size)
                if len(chunk) != expected_size:
                    raise PublishingError("LinkedIn video upload instruction exceeds the local file", retryable=False)
                part_ids.append(self._upload_part(str(instruction["uploadUrl"]), chunk, first_byte, last_byte))

        self._finalize_upload(video_urn, upload_token, part_ids)
        self._wait_until_available(video_urn)
        return video_urn
