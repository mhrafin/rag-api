from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import verify_auth_secret
from src.database import get_session

router = APIRouter(dependencies=[Depends(verify_auth_secret)])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    try:
        # https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html#getting-orm-results-from-textual-statements
        result = await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database Unreachable")

    return {"status": "healthy", "database": "ok", "query_result": result.scalar()}
