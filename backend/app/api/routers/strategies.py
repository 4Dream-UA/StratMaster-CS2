from fastapi import APIRouter

router = APIRouter()


# Endpoints will be implemented in strategy-feed git-branch and strategy-details git-branch
# GET /api/maps                  — list all active maps
# GET /api/strategies            — list strategies with filters
# GET /api/strategies/{id}       — strategy detail with grenades, images, buy tags