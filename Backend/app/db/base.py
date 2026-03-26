"""
db/base.py — Configuration complète SQLAlchemy.

Ce module expose :
  - Base                 : classe déclarative partagée par tous les modèles
  - get_db()             : dependency synchrone (inject dans les routes)
  - get_async_db()       : dependency asynchrone (routes async)
  - transaction()        : context-manager pour transactions explicites sync
  - async_transaction()  : context-manager pour transactions explicites async
  - DatabaseManager      : gestion du cycle de vie (startup / shutdown / health)
  - get_engine_for_alembic() : engine dédié aux migrations (NullPool)

Pool de connexions configuré pour la production :
  - pool_size=10, max_overflow=20  → jusqu'à 30 connexions simultanées
  - pool_pre_ping=True             → détecte les connexions périmées (TCP keep-alive)
  - pool_recycle=3600              → recycle après 1h (PostgreSQL idle timeout)
  - expire_on_commit=False         → objets utilisables après commit (évite DetachedInstanceError)
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# BASE DÉCLARATIVE
# ═══════════════════════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    """
    Classe de base SQLAlchemy 2.0 pour tous les modèles.

    Avantages de DeclarativeBase vs l'ancien declarative_base() :
      - Typage fort natif avec Mapped[T]
      - Autocomplétion IDE précise sur les colonnes
      - Compatible mypy sans plugin supplémentaire
    """
    pass


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS INTERNES
# ═══════════════════════════════════════════════════════════════════════════

def _get_settings():
    """Import tardif pour éviter les imports circulaires au chargement du module."""
    from app.core.config import settings
    return settings


def _make_async_url(sync_url: str) -> str:
    """
    Convertit une URL synchrone en URL async en changeant le driver.

      postgresql://    → postgresql+asyncpg://
      sqlite:///       → sqlite+aiosqlite:///
    """
    replacements = [
        ("postgresql+psycopg2://", "postgresql+asyncpg://"),
        ("postgresql://",           "postgresql+asyncpg://"),
        ("sqlite:///",              "sqlite+aiosqlite:///"),
        ("sqlite://",               "sqlite+aiosqlite://"),
    ]
    for old, new in replacements:
        if sync_url.startswith(old):
            return sync_url.replace(old, new, 1)
    return sync_url


def _register_slow_query_listener(engine, threshold_ms: int) -> None:
    """
    Attache des listeners SQLAlchemy qui logguent les requêtes dépassant
    `threshold_ms` ms. Activé si DB_SLOW_QUERY_MS > 0 dans la config.

    Utile en développement pour détecter les N+1 et les requêtes sans index.
    """
    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("_qstart", []).append(time.monotonic())

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.monotonic() - conn.info["_qstart"].pop()) * 1000
        if elapsed_ms > threshold_ms:
            short = statement[:300].replace("\n", " ")
            logger.warning(
                "🐢 Requête lente (%.1fms > %dms) : %s…",
                elapsed_ms, threshold_ms, short,
            )


# ═══════════════════════════════════════════════════════════════════════════
# FABRIQUE LAZY D'ENGINES ET DE SESSIONS
# ═══════════════════════════════════════════════════════════════════════════

class _EngineFactory:
    """
    Fabrique paresseuse : les engines ne sont créés qu'à la première
    utilisation, évitant les erreurs d'import circulaire.

    Utilise le pattern Singleton par attribut de classe.
    """

    _sync_engine = None
    _async_engine = None
    _sync_factory = None
    _async_factory = None

    # ── Engine synchrone ───────────────────────────────────────────────────

    @classmethod
    def sync_engine(cls):
        if cls._sync_engine is None:
            s = _get_settings()
            is_sqlite = s.DATABASE_URL.startswith("sqlite")

            kwargs = dict(echo=s.DB_ECHO)
            if not is_sqlite:
                kwargs.update(
                    pool_size=s.DB_POOL_SIZE,
                    max_overflow=s.DB_POOL_MAX_OVERFLOW,
                    pool_pre_ping=True,
                    pool_recycle=s.DB_POOL_RECYCLE,
                    poolclass=QueuePool,
                )

            cls._sync_engine = create_engine(s.DATABASE_URL, **kwargs)

            if s.DB_SLOW_QUERY_MS > 0:
                _register_slow_query_listener(cls._sync_engine, s.DB_SLOW_QUERY_MS)

            logger.debug("Engine synchrone créé (%s)", cls._sync_engine.dialect.name)
        return cls._sync_engine

    # ── Engine asynchrone ──────────────────────────────────────────────────

    @classmethod
    def async_engine(cls) -> AsyncEngine:
        if cls._async_engine is None:
            s = _get_settings()
            async_url = _make_async_url(s.DATABASE_URL)
            is_sqlite = s.DATABASE_URL.startswith("sqlite")

            kwargs = dict(echo=s.DB_ECHO)
            if is_sqlite:
                # aiosqlite ne supporte pas le pool standard
                kwargs["poolclass"] = NullPool
            else:
                kwargs.update(
                    pool_size=s.DB_POOL_SIZE,
                    max_overflow=s.DB_POOL_MAX_OVERFLOW,
                    pool_pre_ping=True,
                    pool_recycle=s.DB_POOL_RECYCLE,
                )

            cls._async_engine = create_async_engine(async_url, **kwargs)
            logger.debug("Engine asynchrone créé (%s)", async_url[:50])
        return cls._async_engine

    # ── Fabriques de sessions ──────────────────────────────────────────────

    @classmethod
    def sync_factory(cls) -> sessionmaker:
        if cls._sync_factory is None:
            cls._sync_factory = sessionmaker(
                bind=cls.sync_engine(),
                autocommit=False,
                autoflush=False,
                # expire_on_commit=False : les objets restent accessibles après
                # commit sans nécessiter un SELECT supplémentaire.
                # Critique pour les response_model Pydantic qui lisent les
                # attributs APRÈS que la session ait commité.
                expire_on_commit=False,
            )
        return cls._sync_factory

    @classmethod
    def async_factory(cls) -> async_sessionmaker:
        if cls._async_factory is None:
            cls._async_factory = async_sessionmaker(
                bind=cls.async_engine(),
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                class_=AsyncSession,
            )
        return cls._async_factory

    # ── Fermeture propre ───────────────────────────────────────────────────

    @classmethod
    def dispose(cls) -> None:
        """Ferme les pools de connexions (appel au shutdown de l'app)."""
        if cls._sync_engine:
            cls._sync_engine.dispose()
            logger.info("Pool synchrone fermé")
            cls._sync_engine = None
            cls._sync_factory = None
        if cls._async_engine:
            # L'engine async doit être disposé depuis une coroutine
            # On stocke la référence pour que DatabaseManager.shutdown() le fasse
            cls._async_engine = None
            cls._async_factory = None


# Raccourcis pour compatibilité avec l'ancien code
# (certains endroits peuvent encore importer engine / SessionLocal directement)
def _engine():
    return _EngineFactory.sync_engine()

def _SessionLocal():
    return _EngineFactory.sync_factory()


# ═══════════════════════════════════════════════════════════════════════════
# DEPENDENCIES FASTAPI
# ═══════════════════════════════════════════════════════════════════════════

def get_db() -> Generator[Session, None, None]:
    """
    Dependency synchrone FastAPI — session DB par requête HTTP.

    Cycle de vie :
      1. Ouvre une session depuis le pool
      2. Injecte la session dans la route
      3. Si exception → rollback automatique
      4. Ferme la session (retour au pool) dans tous les cas

    Pourquoi expire_on_commit=False ?
      FastAPI sérialise la réponse (via Pydantic) APRÈS que la fonction
      de route a retourné, donc potentiellement après le commit.
      Sans ce flag, accéder à un attribut déclencherait un
      DetachedInstanceError ou un SELECT implicite inattendu.

    Usage dans un router :
        @router.get("/persons/{id}")
        def get_person(id: uuid.UUID, db: Session = Depends(get_db)):
            return db.get(Person, id)
    """
    db: Session = _EngineFactory.sync_factory()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency asynchrone FastAPI — session async par requête.

    Utilisée pour les routes async qui exécutent des requêtes complexes
    (graphe, full-text search, agrégations lourdes) sans bloquer l'event loop.

    Usage dans un router :
        @router.get("/graph/subtree")
        async def subtree(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Person).where(...))
            persons = result.scalars().all()
            ...
    """
    async with _EngineFactory.async_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGERS — TRANSACTIONS EXPLICITES
# ═══════════════════════════════════════════════════════════════════════════

@contextmanager
def transaction(db: Session) -> Generator[Session, None, None]:
    """
    Context manager synchrone pour les transactions multi-opérations.

    Différence avec get_db() :
      - get_db() ouvre une transaction implicite pour TOUTE la requête HTTP.
      - transaction() permet d'encapsuler des opérations dans une
        transaction explicite dans du code de service, un script CLI,
        ou un worker Celery.

    Commit automatique à la sortie du `with`.
    Rollback automatique en cas d'exception (qui est ensuite re-levée).

    Usage dans un service :
        def transfer_credits(db: Session, from_id, to_id, amount):
            with transaction(db):
                sender = db.get(User, from_id)
                if sender.credits < amount:
                    raise InsufficientFundsError()
                sender.credits -= amount

                receiver = db.get(User, to_id)
                receiver.credits += amount

                db.add(Transaction(from_id=from_id, to_id=to_id, amount=amount))
                # ← commit automatique ici
    """
    try:
        yield db
        db.commit()
        logger.debug("Transaction committed")
    except Exception as exc:
        db.rollback()
        logger.debug("Transaction rolled back : %s(%s)", type(exc).__name__, exc)
        raise


@asynccontextmanager
async def async_transaction(db: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager asynchrone pour les transactions explicites.

    Usage :
        async def create_order_with_items(db: AsyncSession, ...):
            async with async_transaction(db):
                order = Order(...)
                db.add(order)
                await db.flush()   # obtenir l'ID sans committer
                for item in items:
                    db.add(OrderItem(order_id=order.id, ...))
                # ← commit automatique ici
    """
    try:
        yield db
        await db.commit()
        logger.debug("Async transaction committed")
    except Exception as exc:
        await db.rollback()
        logger.debug("Async transaction rolled back : %s(%s)", type(exc).__name__, exc)
        raise


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE MANAGER — cycle de vie de l'application
# ═══════════════════════════════════════════════════════════════════════════

class DatabaseManager:
    """
    Gestion du cycle de vie de la connexion DB dans FastAPI.

    Intégration recommandée dans main.py :

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await DatabaseManager.startup(create_tables=settings.DEBUG)
            yield
            await DatabaseManager.shutdown()

        app = FastAPI(lifespan=lifespan)
    """

    @staticmethod
    async def startup(create_tables: bool = False) -> None:
        """
        À appeler au démarrage de l'application :
          1. Force la création de l'engine (vérifie la config)
          2. Teste la connexion à la BDD
          3. Crée les tables si create_tables=True (dev uniquement)
          4. Logue les infos du pool
        """
        settings = _get_settings()
        logger.info("📦 Connexion à la base de données...")

        try:
            engine = _EngineFactory.sync_engine()
            with engine.connect() as conn:
                # Requête portables SQLite + PostgreSQL
                if engine.dialect.name == "postgresql":
                    row = conn.execute(text("SELECT current_database(), version()")).one()
                    logger.info("✅ PostgreSQL '%s' : %s", row[0], str(row[1])[:60])
                else:
                    conn.execute(text("SELECT 1"))
                    logger.info("✅ DB connectée (%s)", engine.dialect.name)
        except Exception as exc:
            logger.error("❌ Connexion DB impossible : %s", exc)
            raise RuntimeError(f"DB connection failed: {exc}") from exc

        if create_tables:
            logger.warning(
                "⚠️  create_tables=True (dev uniquement) — utiliser Alembic en production"
            )
            Base.metadata.create_all(bind=_EngineFactory.sync_engine())
            tables = sorted(Base.metadata.tables.keys())
            logger.info("Tables : %s", tables)

        try:
            pool = _EngineFactory.sync_engine().pool
            logger.info(
                "Pool : size=%s, checked_in=%s, overflow=%s",
                pool.size(), pool.checkedin(), pool.overflow(),
            )
        except Exception:
            pass  # SQLite ou pool sans stats

    @staticmethod
    async def shutdown() -> None:
        """Fermeture propre des pools au shutdown de l'application."""
        logger.info("🛑 Fermeture des pools de connexions DB...")
        engine = _EngineFactory._async_engine
        if engine:
            await engine.dispose()
            logger.info("Pool asynchrone fermé")
        _EngineFactory.dispose()

    @staticmethod
    async def check_health() -> dict:
        """
        Vérifie la santé de la connexion DB.
        Retourné dans GET /health/detailed.

        Exemple de retour :
            {
                "status": "ok",
                "latency_ms": 2.4,
                "pool_size": 10,
                "pool_checked_in": 9,
                "pool_overflow": 0,
                "error": null
            }
        """
        result: dict = {
            "status": "ok",
            "latency_ms": None,
            "pool_size": None,
            "pool_checked_in": None,
            "pool_overflow": None,
            "error": None,
        }
        t0 = time.monotonic()
        try:
            with _EngineFactory.sync_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            result["latency_ms"] = round((time.monotonic() - t0) * 1000, 2)
            pool = _EngineFactory.sync_engine().pool
            result["pool_size"] = pool.size()
            result["pool_checked_in"] = pool.checkedin()
            result["pool_overflow"] = pool.overflow()
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
            result["latency_ms"] = round((time.monotonic() - t0) * 1000, 2)
        return result

    @staticmethod
    def pool_stats() -> dict:
        """Métriques du pool exposables dans /metrics ou /admin."""
        try:
            pool = _EngineFactory.sync_engine().pool
            return {
                "pool_size":      pool.size(),
                "checked_in":     pool.checkedin(),
                "checked_out":    pool.checkedout(),
                "overflow":       pool.overflow(),
            }
        except Exception:
            return {}


# ═══════════════════════════════════════════════════════════════════════════
# UTILITAIRE ALEMBIC
# ═══════════════════════════════════════════════════════════════════════════

def get_engine_for_alembic():
    """
    Engine dédié aux migrations Alembic (NullPool, pas de persistance).

    Utilisé dans alembic/env.py :
        from app.db.base import get_engine_for_alembic
        connectable = get_engine_for_alembic()
    """
    from app.core.config import settings
    return create_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)


# ═══════════════════════════════════════════════════════════════════════════
# RÉTROCOMPATIBILITÉ — anciens imports directs
# ═══════════════════════════════════════════════════════════════════════════
# Certains fichiers existants importent `engine` et `SessionLocal` directement.
# Ces proxys assurent la compatibilité sans casser l'existant.

class _EngineProxy:
    """Proxy vers l'engine synchrone (créé à la demande)."""
    def __getattr__(self, item):
        return getattr(_EngineFactory.sync_engine(), item)
    def __call__(self, *a, **kw):
        return _EngineFactory.sync_engine()(*a, **kw)

class _SessionProxy:
    """Proxy vers la factory de sessions (créée à la demande)."""
    def __call__(self, *a, **kw):
        return _EngineFactory.sync_factory()(*a, **kw)
    def __getattr__(self, item):
        return getattr(_EngineFactory.sync_factory(), item)

engine = _EngineProxy()
SessionLocal = _EngineProxy()   # garde le nom historique
