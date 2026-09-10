from pathlib import Path

import pytest

from app.errors import PublishingError
from app.linkedin_multiimage import LinkedInMultiImageClient


def test_multiimage_requires_two_to_twenty(tmp_path: Path) -> None:
    client = LinkedInMultiImageClient("token", "urn:li:organization:1", "202608", 5)
    image = tmp_path / "one.jpg"
    image.write_bytes(b"image")
    with pytest.raises(PublishingError):
        client.upload_images([str(image)])
    with pytest.raises(PublishingError):
        client.upload_images([str(image)] * 21)


def test_multiimage_missing_file_is_permanent() -> None:
    client = LinkedInMultiImageClient("token", "urn:li:organization:1", "202608", 5)
    with pytest.raises(PublishingError) as exc:
        client.upload_images(["missing-1.jpg", "missing-2.jpg"])
    assert exc.value.retryable is False
