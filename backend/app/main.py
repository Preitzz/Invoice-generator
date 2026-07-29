from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Invoice Generator with Payment-Reminder Engine", version="0.1.0")

    register_exception_handlers(app)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
