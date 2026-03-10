from pydantic import BaseModel
from typing import Optional

class Pokemon(BaseModel):
    name: str
    item: Optional[str] = None
    ability: Optional[str] = None
    tera_type: Optional[str] = None
    evs: Optional[dict] = None
    nature: Optional[str] = None
    moves: list[str] = []
    level: int = 100

class Team(BaseModel):
    pokemon: list[Pokemon]
    format: str = "gen9ou"
    raw_paste: str = ""

class AnalysisRequest(BaseModel):
    pokepaste: str
    format: str = "gen9ou"
