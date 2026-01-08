from dataclasses import dataclass
from typing import Optional


@dataclass
class ServiceOptions:
    mount: Optional[str] = None
    grace_period: int = 180
