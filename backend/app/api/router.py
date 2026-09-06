from fastapi import APIRouter
from .routes import backups, chain, demo, development, recovery, source

api_router = APIRouter()
api_router.include_router(source.router)
api_router.include_router(backups.router)
api_router.include_router(chain.router)
api_router.include_router(recovery.router)
api_router.include_router(demo.router)
api_router.include_router(development.router)
