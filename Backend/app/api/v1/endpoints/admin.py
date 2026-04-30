from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate, UserRoleUpdate, UserListResponse
from app.schemas.acl import AccessControlCreate, AccessControlResponse
from app.schemas.common import StatsResponse, SystemInfoResponse
from app.services.user_service import UserService
from app.services.acl_service import ACLService
from app.services.export_service import ExportService
from app.api.deps import get_current_admin_user
from app.api.v1.guards.roles import require_admin  # NOUVEAU
from app.core.exceptions import NotFoundException, PermissionDeniedException, ConflictException  # NOUVEAU

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])  # MODIFIÉ - Protection au niveau du router


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