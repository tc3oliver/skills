"""Video timeline segment metadata."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    segment_id: str
    title: str
    text: str
