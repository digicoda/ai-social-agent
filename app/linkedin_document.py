from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from .errors import PublishingError


class LinkedInDocumentClient:
    """Upload and verify LinkedIn document assets using the Documents API."""

    endpoint = "https://api.linkedin.com/rest/documents"
    supported_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

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
            f"LinkedIn document {action} failed with HTTP {status}",
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
            raise PublishingError(f"LinkedIn document initialization request failed: {exc}", retryable=True) from exc

        try:
            value = response.json()["value"]
            upload_url = value["uploadUrl"]
            document_urn = value["document"]
        except (TypeError, KeyError, ValueError) as exc:
            raise PublishingError("LinkedIn document initialization returned an invalid response", retryable=True) from exc

        if not upload_url or not document_urn:
            raise PublishingError("LinkedIn document initialization did not return uploadUrl and document", retryable=True)
        return upload_url, document_urn

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
            raise PublishingError(f"LinkedIn document upload request failed: {exc}", retryable=True) from exc

    def _wait_until_available(self, document_urn: str) -> None:
        url = f"{self.endpoint}/{quote(document_urn, safe='')}"
        last_status = ""
        for attempt in range(self.poll_attempts):
            try:
                response = httpx.get(url, headers=self._headers(), timeout=self.timeout)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_http_error("status check", exc)
            except httpx.RequestError as exc:
                raise PublishingError(f"LinkedIn document status request failed: {exc}", retryable=True) from exc

            try:
                last_status = str(response.json().get("status", ""))
            except (TypeError, ValueError) as exc:
                raise PublishingError("LinkedIn document status returned an invalid response", retryable=True) from exc

            if last_status == "AVAILABLE":
                return
            if last_status in {"PROCESSING_FAILED", "FAILED"}:
                raise PublishingError(
                    f"LinkedIn document processing failed with status {last_status}",
                    retryable=False,
                )
            if attempt < self.poll_attempts - 1 and self.poll_seconds:
                time.sleep(self.poll_seconds)

        raise PublishingError(
            f"LinkedIn document did not become available (last status: {last_status or 'unknown'})",
            retryable=True,
        )

    def upload_document(self, document_path: str) -> str:
        path = Path(document_path)
        if not path.is_file():
            raise PublishingError(f"document file not found: {document_path}", retryable=False)
        content = path.read_bytes()
        if not content:
            raise PublishingError("document file is empty", retryable=False)

        content_type, _ = mimetypes.guess_type(path.name)
        if content_type not in self.supported_types:
            raise PublishingError(
                "LinkedIn Documents API supports PDF, DOC, DOCX, PPT, and PPTX files",
                retryable=False,
            )

        upload_url, document_urn = self._initialize_upload()
        self._upload(upload_url, content, content_type)
        self._wait_until_available(document_urn)
        return document_urn
