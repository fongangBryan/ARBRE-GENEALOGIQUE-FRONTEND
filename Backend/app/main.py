from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.db.session import engine
from app.db.base import Base
from app.db.init_db import init_db  # NOUVEAU
from app.middleware.auth import AuthMiddleware

# Create tables (in development)
def create_tables():
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Genealogie App API",
    description="Application de gestion d'arbre généalogique",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:80", "http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure properly in production
)

# Custom Auth Middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    create_tables()
    init_db()  # NOUVEAU - Crée l'admin et les données de bas
    print("✅ Database tables created/verified")

@app.get("/")
async def root():
    return {"message": "Genealogie App API", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}