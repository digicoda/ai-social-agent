from __future__ import annotations

from pathlib import Path

from .errors import PublishingError
from .linkedin_media import LinkedInMediaClient


class LinkedInMultiImageClient:
    """Upload multiple LinkedIn image assets for a native MultiImage post."""

    def __init__(self, token: str, author: str, version: str, timeout: float, poll_attempts: int = 10, poll_seconds: float = 1.0) -> None:
        self.client = LinkedInMediaClient(token, author, version, timeout, poll_attempts=poll_attempts, poll_seconds=poll_seconds)

    def upload_images(self, image_paths: list[str]) -> list[str]:
        if not 2 <= len(image_paths) <= 20:
            raise PublishingError("LinkedIn MultiImage publishing requires between 2 and 20 images", retryable=False)
        urns: list[str] = []
        for image_path in image_paths:
            path = Path(image_path)
            if not path.is_file():
                raise PublishingError(f"image file not found: {image_path}", retryable=False)
            urns.append(self.client.upload_image(str(path)))
        return urns
