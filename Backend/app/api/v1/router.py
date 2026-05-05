from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, persons, filiations, unions, tree, media, events, admin, tags

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(persons.router)
api_router.include_router(filiations.router)
api_router.include_router(unions.router)
api_router.include_router(tree.router)
api_router.include_router(media.router)
api_router.include_router(events.router)
api_router.include_router(admin.router)
api_router.include_router(tags.router)