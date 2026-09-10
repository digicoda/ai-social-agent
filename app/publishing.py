from dataclasses import dataclass

import httpx

from .config import Settings
from .errors import PublishingError
from .linkedin_document import LinkedInDocumentClient
from .linkedin_media import LinkedInMediaClient
from .linkedin_multiimage import LinkedInMultiImageClient
from .linkedin_video import LinkedInVideoClient


@dataclass(slots=True)
class PublishResult:
    provider: str
    remote_id: str
    url: str = ""


class Publisher:
    provider = ""

    def publish(self, title: str, body: str, hashtags: list[str], media_paths: list[str] | None = None, media_type: str = "none") -> PublishResult:
        raise NotImplementedError


class LinkedInPublisher(Publisher):
    provider = "linkedin"
    endpoint = "https://api.linkedin.com/rest/posts"

    def __init__(self, settings: Settings) -> None:
        self.token = settings.linkedin_access_token
        self.author = settings.linkedin_author_urn
        self.version = settings.linkedin_api_version
        self.timeout = settings.publishing_timeout_seconds
        self.media_poll_attempts = settings.linkedin_media_poll_attempts
        self.media_poll_seconds = settings.linkedin_media_poll_seconds
        if not self.token or not self.author:
            raise PublishingError("LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN are required", retryable=False)

    def publish(self, title: str, body: str, hashtags: list[str], media_paths: list[str] | None = None, media_type: str = "none") -> PublishResult:
        commentary = body.strip()
        if hashtags:
            commentary += "\n\n" + " ".join(f"#{tag.lstrip('#')}" for tag in hashtags)
        if not commentary:
            raise PublishingError("cannot publish an empty post", retryable=False)
        if media_type not in {"none", "image", "document", "video", "multi_image"}:
            raise PublishingError(f"unsupported LinkedIn media type: {media_type}", retryable=False)

        paths = media_paths or []
        # Preserve the historical direct-publish API: supplying one media path
        # without an explicit media_type means an image post.
        if media_type == "none" and paths:
            media_type = "image"
        if media_type == "multi_image" and not 2 <= len(paths) <= 20:
            raise PublishingError("LinkedIn MultiImage publishing requires between 2 and 20 images", retryable=False)
        if media_type not in {"none", "multi_image"} and len(paths) > 1:
            raise PublishingError("LinkedIn publishing supports one media file per post for this media type", retryable=False)
        if media_type in {"document", "video", "image"} and len(paths) != 1:
            raise PublishingError(f"LinkedIn {media_type} publishing requires exactly one media file", retryable=False)

        content: dict = {}
        if paths:
            if media_type == "multi_image":
                media = LinkedInMultiImageClient(self.token, self.author, self.version, self.timeout, poll_attempts=self.media_poll_attempts, poll_seconds=self.media_poll_seconds)
                image_urns = media.upload_images(paths)
                content = {"multiImage": {"images": [{"id": urn} for urn in image_urns]}}
            elif media_type == "document":
                media = LinkedInDocumentClient(self.token, self.author, self.version, self.timeout, poll_attempts=self.media_poll_attempts, poll_seconds=self.media_poll_seconds)
                document_urn = media.upload_document(paths[0])
                content = {"media": {"id": document_urn, "title": title.strip() or paths[0]}}
            elif media_type == "video":
                media = LinkedInVideoClient(self.token, self.author, self.version, self.timeout, poll_attempts=self.media_poll_attempts, poll_seconds=self.media_poll_seconds)
                video_urn = media.upload_video(paths[0])
                content = {"media": {"id": video_urn}}
            else:
                media = LinkedInMediaClient(self.token, self.author, self.version, self.timeout, poll_attempts=self.media_poll_attempts, poll_seconds=self.media_poll_seconds)
                image_urn = media.upload_image(paths[0])
                content = {"media": {"id": image_urn}}

        payload = {
            "author": self.author,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if content:
            payload["content"] = content
        try:
            response = httpx.post(self.endpoint, headers={"Authorization": f"Bearer {self.token}", "Linkedin-Version": self.version, "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise PublishingError(f"LinkedIn publish failed with HTTP {status}", retryable=status in {408, 409, 429} or status >= 500) from exc
        except httpx.RequestError as exc:
            raise PublishingError(f"LinkedIn publish request failed: {exc}", retryable=True) from exc
        remote_id = response.headers.get("x-restli-id", "")
        if not remote_id:
            raise PublishingError("LinkedIn did not return x-restli-id", retryable=True)
        return PublishResult(provider=self.provider, remote_id=remote_id)


def get_publisher(settings: Settings, provider: str) -> Publisher:
    if provider == "linkedin":
        return LinkedInPublisher(settings)
    raise PublishingError(f"unsupported publishing provider: {provider}", retryable=False)
