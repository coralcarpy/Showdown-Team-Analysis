from fastapi import APIRouter
from app.models.pokemon import AnalysisRequest
from app.services.parser import parse_pokepaste

router = APIRouter()

@router.post("/parse")
async def parse_team(request: AnalysisRequest):
    team = parse_pokepaste(request.pokepaste, request.format)
    return {"pokemon": [p.model_dump() for p in team.pokemon], "format": team.format}