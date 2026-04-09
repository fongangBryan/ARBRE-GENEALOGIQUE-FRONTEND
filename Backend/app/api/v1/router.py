from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, persons, relationships, tree, media, events, admin

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(persons.router)
api_router.include_router(relationships.router)
api_router.include_router(tree.router)
api_router.include_router(media.router)
api_router.include_router(events.router)
api_router.include_router(admin.router)