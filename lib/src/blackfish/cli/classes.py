from dataclasses import dataclass
from typing import Optional

from blackfish.server.config import config


@dataclass
class ServiceOptions:
    mount: Optional[str] = None
    grace_period: int = config.GRACE_PERIOD
    # A pinned container image as "repo:tag". None means "use the configured
    # default", which the server records on the service once it launches.
    image_ref: Optional[str] = None
