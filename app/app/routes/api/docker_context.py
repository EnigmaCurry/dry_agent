from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/test", response_class=JSONResponse)
async def test(request: Request):
    return {"message": "test"}
