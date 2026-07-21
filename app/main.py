import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import auth, claims, users
from app.core.config import get_settings
from app.db.database import SessionLocal, engine
from app.db.initialization import initialize_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database(engine, SessionLocal, get_settings())
    yield


def create_app(*, initialize_on_startup: bool = True) -> FastAPI:
    app = FastAPI(
        title="Expense Claim API",
        debug=False,
        lifespan=lifespan if initialize_on_startup else None,
    )
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(claims.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unexpected error while handling %s", request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
