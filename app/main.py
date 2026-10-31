from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.liveness_routes import router as liveness_router
from app.api.routes import router
from app.auth.routes import router as auth_router
from app.auth.service import initialize_auth_database
from app.core.config import Settings, get_settings
from app.core.services import AppServices, build_services
from app.database.attendance_db import initialize_database


ServiceFactory = Callable[[Settings], AppServices]


def create_app(
    settings: Settings | None = None,
    service_factory: ServiceFactory = build_services,
) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.settings = app_settings

        initialize_database(app_settings.database_path)
        initialize_auth_database(app_settings.database_path)

        application.state.database_initialized = True
        application.state.auth_initialized = True

        print("Database schema initialized")

        services = service_factory(app_settings)

        application.state.services = services
        application.state.liveness_service = services.liveness_service
        application.state.face_service = services.face_service
        application.state.attendance_service = services.attendance_service

        try:
            yield
        finally:
            services.close()

    application = FastAPI(
        title="AI Attendance System",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(router)
    application.include_router(liveness_router)
    application.include_router(auth_router)

    @application.get("/")
    def root():
        return {
            "message": "AI Attendance Service is running"
        }

    return application


app = create_app()
