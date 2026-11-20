from fastapi import APIRouter

from app.api.routes import auth, health, membership_types, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(membership_types.router)
api_router.include_router(users.router)
