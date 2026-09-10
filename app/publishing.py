from dataclasses import dataclass

import httpx

from .config import Settings


class PublishingError(RuntimeError):
    pass


@dataclass(slots=True)
class PublishResult:
    provider: str
    remote_id: str
    url: str = ""


class Publisher:
    provider = ""

    def publish(self, title: str, body: str, hashtags: list[str]) -> PublishResult:
        raise NotImplementedError


class LinkedInPublisher(Publisher):
    provider = "linkedin"
    endpoint = "https://api.linkedin.com/rest/posts"

    def __init__(self, settings: Settings) -> None:
        self.token = settings.linkedin_access_token
        self.author = settings.linkedin_author_urn
        self.version = settings.linkedin_api_version
        self.timeout = settings.publishing_timeout_seconds
        if not self.token or not self.author:
            raise PublishingError("LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN are required")

    def publish(self, title: str, body: str, hashtags: list[str]) -> PublishResult:
        commentary = body.strip()
        if hashtags:
            commentary += "\n\n" + " ".join(f"#{tag.lstrip('#')}" for tag in hashtags)
        payload = {
            "author": self.author,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
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
        except httpx.HTTPError as exc:
            raise PublishingError(f"LinkedIn publish failed: {exc}") from exc
        remote_id = response.headers.get("x-restli-id", "")
        if not remote_id:
            raise PublishingError("LinkedIn did not return x-restli-id")
        return PublishResult(provider=self.provider, remote_id=remote_id)


def get_publisher(settings: Settings, provider: str) -> Publisher:
    if provider == "linkedin":
        return LinkedInPublisher(settings)
    raise PublishingError(f"unsupported publishing provider: {provider}")
