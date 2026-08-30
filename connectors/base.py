"""
Connector contract. Every data source implements this one interface, so the
collector and UI never care whether data comes from a REST API, a webhook, a
CSV, or a manual form. To add a source (transactional data, a new platform,
an API you sign up for later): create a class here, implement collect(), and
register it. Nothing else changes.
"""
from abc import ABC, abstractmethod


class Connector(ABC):
    id: str = "base"
    name: str = "Base"
    kind: str = "api"  # "api" | "manual"

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def is_configured(self) -> bool:
        """True when this source has the credentials/inputs it needs to run."""

    @abstractmethod
    def collect(self, db_path) -> dict:
        """Fetch current data and persist it. Return a short status dict."""


def registry(config):
    """All known connectors. Import here to avoid circular imports."""
    from .youtube import YouTubeConnector
    from .instagram import InstagramConnector
    from .beatstars import BeatStarsConnector
    return [
        YouTubeConnector(config),
        InstagramConnector(config),
        BeatStarsConnector(config),
    ]
