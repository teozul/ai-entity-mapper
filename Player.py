from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Club:
    id: str
    name: str


@dataclass
class Player:
    id: str
    name: str
    position: Optional[str]
    age: Optional[int]
    nationalities: List[str]
    club: Optional[Club]
    market_value: Optional[int] = None

    @staticmethod
    def from_dict(d: dict):
        return Player(
            id=d["id"],
            name=d["name"],
            position=d.get("position"),
            age=d.get("age"),
            nationalities=d.get("nationalities", []),
            market_value=d.get("marketValue"),
            club=Club(**d["club"]) if d.get("club") else None
        )
