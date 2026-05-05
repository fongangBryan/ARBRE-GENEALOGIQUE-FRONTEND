from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate, UserRoleUpdate, UserListResponse
from app.schemas.acl import AccessControlCreate, AccessControlResponse
from app.schemas.common import StatsResponse, SystemInfoResponse
from app.services.user_service import UserService
from app.services.acl_service import ACLService
from app.services.export_service import ExportService
from app.models.audit_log import AuditLog
from app.models.user import User
from app.core.security import create_email_token
from app.config import settings
from datetime import timedelta
from app.api.deps import get_current_admin_user
from app.api.v1.guards.roles import require_admin
from app.core.exceptions import NotFoundException, PermissionDeniedException, ConflictException

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])  # MODIFIÉ - Protection au niveau du router


# ============ JOURNAL D'ACTIVITÉ ============

@router.get("/logs")
def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Journal d'activité global (Admin uniquement)."""
    q = db.query(AuditLog)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    logs = q.order_by(desc(AuditLog.created_at)).offset((page - 1) * limit).limit(limit).all()

    # Résoudre les emails en une seule requête
    user_ids = {log.user_id for log in logs if log.user_id}
    users_map: dict = {}
    if user_ids:
        rows = db.query(User.id, User.email, User.first_name, User.last_name).filter(User.id.in_(user_ids)).all()
        for r in rows:
            users_map[str(r.id)] = {
                "email": r.email,
                "first_name": r.first_name,
                "last_name": r.last_name,
            }

    items = [
        {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "user": users_map.get(str(log.user_id)) if log.user_id else None,
        }
        for log in logs
    ]
    return {"items": items, "total": total, "page": page, "pages": max(1, (total + limit - 1) // limit)}


# ============ GESTION DES UTILISATEURS ============

@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Liste tous les utilisateurs (Admin uniquement)"""
    user_service = UserService(db)
    users, total = user_service.list_users(search, page, limit)
    pages = (total + limit - 1) // limit if total > 0 else 1
    return UserListResponse(items=users, total=total, page=page, limit=limit, pages=pages)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Récupérer un utilisateur par son ID"""
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour un utilisateur"""
    user_service = UserService(db)
    user = user_service.update_user(user_id, user_data)
    if not user:
        raise NotFoundException("User", user_id)
    return user


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db)
):
    """Changer le rôle d'un utilisateur (admin/editor/reader)"""
    user_service = UserService(db)
    user = user_service.update_role(user_id, role_data.role)
    if not user:
        raise NotFoundException("User", user_id)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Supprimer un utilisateur (Admin uniquement)"""
    if str(current_user.id) == str(user_id):
        raise ConflictException("Cannot delete your own account")
    
    user_service = UserService(db)
    success = user_service.delete_user(user_id, soft_delete=False)
    if not success:
        raise NotFoundException("User", user_id)


@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Activer un utilisateur"""
    user_service = UserService(db)
    user = user_service.activate_user(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    return {"message": "User activated"}


@router.post("/users/{user_id}/verification-link")
def get_verification_link(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Génère un lien de vérification email pour un utilisateur (sans envoyer d'email)."""
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email déjà vérifié")
    token = create_email_token(
        str(user.id), "email_verification",
        timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
    )
    link = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    return {"link": link, "expires_hours": settings.VERIFICATION_TOKEN_EXPIRE_HOURS}


@router.post("/users/{user_id}/reset-link")
def get_reset_link(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Génère un lien de réinitialisation de mot de passe pour un utilisateur (sans envoyer d'email)."""
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    token = create_email_token(
        str(user.id), "password_reset",
        timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    )
    link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    return {"link": link, "expires_minutes": settings.RESET_TOKEN_EXPIRE_MINUTES}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: UUID,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Désactiver un utilisateur"""
    if str(current_user.id) == str(user_id):
        raise ConflictException("Cannot deactivate your own account")
    
    user_service = UserService(db)
    user = user_service.deactivate_user(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    return {"message": "User deactivated"}


# ============ GESTION DES ACL ============

@router.get("/acls", response_model=List[AccessControlResponse])
def list_acls(
    person_id: Optional[UUID] = Query(None),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Liste toutes les ACLs (Admin uniquement)"""
    acl_service = ACLService(db, current_user)
    acls = acl_service.list_acls_for_person(person_id) if person_id else []
    return acls


@router.post("/acls", response_model=AccessControlResponse)
def create_acl(
    acl_data: AccessControlCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Créer une ACL (donner un accès spécifique)"""
    acl_service = ACLService(db, current_user)
    acl = acl_service.grant_access(
        person_id=acl_data.person_id,
        principal_type=acl_data.principal_type,
        principal_id=acl_data.principal_id,
        permission=acl_data.permission
    )
    return acl


@router.delete("/acls/{acl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_acl(
    acl_id: UUID,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Supprimer une ACL"""
    acl_service = ACLService(db, current_user)
    success = acl_service.revoke_access(acl_id)
    if not success:
        raise NotFoundException("ACL", acl_id)


# ============ STATISTIQUES ============

@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db)
):
    """Récupérer les statistiques globales de l'application"""
    from app.services.stats_service import StatsService
    
    stats_service = StatsService(db)
    stats = stats_service.get_global_stats()
    return stats


@router.get("/stats/users")
def get_user_stats(
    db: Session = Depends(get_db)
):
    """Statistiques détaillées des utilisateurs"""
    from app.services.stats_service import StatsService
    
    stats_service = StatsService(db)
    return stats_service.get_user_stats()


@router.get("/stats/persons")
def get_person_stats(
    db: Session = Depends(get_db)
):
    """Statistiques détaillées des personnes"""
    from app.services.stats_service import StatsService
    
    stats_service = StatsService(db)
    return stats_service.get_person_stats()


# ============ EXPORT / IMPORT ============

@router.post("/export/all")
def export_all_data(
    format: str = Query("json", regex="^(json|gedcom)$"),
    db: Session = Depends(get_db)
):
    """Exporter toutes les données de l'application"""
    export_service = ExportService(db)
    
    if format == "json":
        data = export_service.export_to_json()
        return data
    else:
        data = export_service.export_to_gedcom()
        return {"gedcom": data}


@router.post("/export/users")
def export_users(
    db: Session = Depends(get_db)
):
    """Exporter la liste des utilisateurs (CSV)"""
    export_service = ExportService(db)
    return export_service.export_users_to_csv()


# ============ SYSTÈME ============

@router.get("/system/info", response_model=SystemInfoResponse)
def get_system_info(
    db: Session = Depends(get_db)
):
    """Informations système (version, uptime, etc.)"""
    import time
    from datetime import datetime
    
    return SystemInfoResponse(
        version="1.0.0",
        uptime_seconds=time.time() - getattr(get_system_info, "start_time", time.time()),
        database_status="connected",
        redis_status="connected"
    )


@router.post("/system/health-check")
def health_check(
    db: Session = Depends(get_db)
):
    """Vérification complète du système"""
    from app.db.session import engine
    
    try:
        connection = engine.connect()
        connection.execute("SELECT 1")
        connection.close()
        db_status = "ok"
    except Exception:
        db_status = "error"
    
    return {
        "database": db_status,
        "api": "ok",
        "timestamp": "2024-01-01T00:00:00Z"
    }