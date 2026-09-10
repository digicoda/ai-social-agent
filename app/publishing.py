from dataclasses import dataclass

import httpx

from .config import Settings
from .linkedin_media import LinkedInMediaClient


class PublishingError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(slots=True)
class PublishResult:
    provider: str
    remote_id: str
    url: str = ""


class Publisher:
    provider = ""

    def publish(self, title: str, body: str, hashtags: list[str], media_paths: list[str] | None = None) -> PublishResult:
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

    def publish(self, title: str, body: str, hashtags: list[str], media_paths: list[str] | None = None) -> PublishResult:
        commentary = body.strip()
        if hashtags:
            commentary += "\n\n" + " ".join(f"#{tag.lstrip('#')}" for tag in hashtags)
        if not commentary:
            raise PublishingError("cannot publish an empty post", retryable=False)

        content: dict = {}
        if media_paths:
            if len(media_paths) > 1:
                raise PublishingError("Phase 6C supports one LinkedIn image per post", retryable=False)
            media = LinkedInMediaClient(
                self.token,
                self.author,
                self.version,
                self.timeout,
                poll_attempts=self.media_poll_attempts,
                poll_seconds=self.media_poll_seconds,
            )
            image_urn = media.upload_image(media_paths[0])
            content = {"media": {"id": image_urn, "title": title.strip()}}

        payload = {
            "author": self.author,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
            **content,
        }
        try:
            response = httpx.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Linkedin-Version": self.version,
                    "X-Restli-Protocol-Version": "2.0.0",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise PublishingError(
                f"LinkedIn publish failed with HTTP {status}",
                retryable=status in {408, 409, 429} or status >= 500,
            ) from exc
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
