from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from oculis_api.core.config import settings
from oculis_api.routers import analyses, health

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyses.router)
app.mount("/artifacts", StaticFiles(directory="/artifacts", check_dir=False), name="artifacts")
