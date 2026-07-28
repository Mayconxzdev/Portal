from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import List, Dict, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.permissions import require_admin, PermissionLevel, get_current_user
from app.core.security import get_password_hash
from app.core.audit import log_action
from app.models.user import User
from app.models.role import Role
from app.models.module import Module
from app.models.user_module_access import UserModuleAccess
from app.models.audit_log import AuditLog
from app.models.kanban import KanbanBoard, KanbanBoardPermission
from app.models.admin_lifecycle import (
    UserSession,
    UserTemporaryAccess,
    UserTemporarySubstitution,
    UserOffboardingCase,
    UserOffboardingTask,
)

router = APIRouter(dependencies=[Depends(require_admin)])

class ModulePermissionSchema(BaseModel):
    module_id: int
    permission_level: PermissionLevel

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    password: str
    role_id: int
    is_active: bool = True
    must_change_password: bool = True
    module_permissions: List[ModulePermissionSchema] = []

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("A senha temporaria nao pode ser vazia ou conter apenas espacos.")
        return v

class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    must_change_password: Optional[bool] = None

class ModuleAccessUpdateRequest(BaseModel):
    permissions: List[ModulePermissionSchema]

class UserModuleAccessResponse(BaseModel):
    module_id: int
    module_code: str
    module_name: str
    permission_level: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    role_id: Optional[int]
    role_name: Optional[str]
    is_active: bool
    must_change_password: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    module_permissions: List[UserModuleAccessResponse]

    model_config = ConfigDict(from_attributes=True)

class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ModuleResponse(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool
    is_restricted: bool

    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    module: str
    details: dict
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserSearchResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role_name: Optional[str] = None


class AdminKanbanBoardResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_archived: bool


class AdminBoardPermissionItem(BaseModel):
    board_id: int
    board_name: str
    board_slug: str
    access_level: str
    permission_id: Optional[int] = None


class AdminBoardPermissionsResponse(BaseModel):
    user_id: int
    username: str
    email: Optional[str] = None
    role_name: Optional[str] = None
    permissions: List[AdminBoardPermissionItem]


class AdminBoardPermissionBulkItem(BaseModel):
    board_id: int
    access_level: str


class AdminBoardPermissionBulkRequest(BaseModel):
    user_id: int
    permissions: List[AdminBoardPermissionBulkItem]


class RevokeSessionRequest(BaseModel):
    reason: Optional[str] = None


class TemporaryAccessCreateRequest(BaseModel):
    module_id: int
    permission_level: str
    reason: str
    expires_at: datetime


class TemporarySubstitutionCreateRequest(BaseModel):
    substitute_user_id: int
    reason: str
    expires_at: datetime


class OffboardingCreateRequest(BaseModel):
    reason: str
    replacement_user_id: Optional[int] = None


BOARD_ACCESS_LEVELS = {"NO_ACCESS", "READ_ONLY", "NORMAL", "MANAGER", "ADMIN"}


def _serialize_user_search(user: User) -> Dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role_name": user.role.name if user.role else None,
    }


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado ou inativo")
    return user


def _board_permission_matrix(db: Session, user: User) -> Dict[str, object]:
    boards = db.query(KanbanBoard).order_by(KanbanBoard.is_archived, KanbanBoard.name).all()
    permissions = {
        perm.board_id: perm
        for perm in db.query(KanbanBoardPermission).filter(KanbanBoardPermission.user_id == user.id).all()
    }
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role_name": user.role.name if user.role else None,
        "permissions": [
            {
                "board_id": board.id,
                "board_name": board.name,
                "board_slug": board.slug,
                "access_level": permissions[board.id].access_level if board.id in permissions else "NO_ACCESS",
                "permission_id": permissions[board.id].id if board.id in permissions else None,
            }
            for board in boards
        ],
    }


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista todos os usuários reais do banco de dados, incluindo seus acessos aos módulos.
    """
    users = db.query(User).order_by(User.id).all()
    result = []
    
    # Lista todos os módulos para garantir mapeamento completo
    all_modules = db.query(Module).all()
    
    # Recupera o ID da role ADMIN para mascarar
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    admin_role_id = admin_role.id if admin_role else None
    
    is_current_messias = current_user.role and current_user.role.name == "MESSIAS"
    
    for u in users:
        if u.role and u.role.name == "MESSIAS" and not is_current_messias:
            continue
            
        role_id = u.role_id
        role_name = u.role.name if u.role else None
        
        mod_perms = []
        # Adiciona acessos existentes no banco
        for acc in u.module_accesses:
            mod_perms.append({
                "module_id": acc.module_id,
                "module_code": acc.module.code,
                "module_name": acc.module.name,
                "permission_level": acc.permission_level
            })
        
        # Preenche módulos que não tenham mapeamento explícito no banco
        existing_module_ids = {acc.module_id for acc in u.module_accesses}
        for m in all_modules:
            if m.id not in existing_module_ids:
                mod_perms.append({
                    "module_id": m.id,
                    "module_code": m.code,
                    "module_name": m.name,
                    "permission_level": "ADMIN" if (u.role and u.role.name in ["ADMIN", "MESSIAS"]) else "NO_ACCESS"
                })

        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "department": u.department,
            "job_title": u.job_title,
            "role_id": role_id,
            "role_name": role_name,
            "is_active": u.is_active,
            "must_change_password": u.must_change_password or False,
            "created_at": u.created_at,
            "updated_at": u.updated_at,
            "last_login": u.last_login,
            "module_permissions": mod_perms
        })
    return result


@router.get("/users/search", response_model=List[AdminUserSearchResponse])
def search_users(
    q: str = "", 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Busca usuarios ativos para telas administrativas sem expor senha ou dados tecnicos.
    """
    query = db.query(User).filter(User.is_active == True)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter((User.username.ilike(term)) | (User.email.ilike(term)))
        
    users = query.order_by(User.username).limit(20).all()
    is_current_messias = current_user.role and current_user.role.name == "MESSIAS"
    
    results = []
    for u in users:
        if u.role and u.role.name == "MESSIAS" and not is_current_messias:
            continue
        role_name = u.role.name if u.role else None
            
        results.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role_name": role_name
        })
    return results


@router.get("/kanban/boards", response_model=List[AdminKanbanBoardResponse])
def list_kanban_boards_for_admin(db: Session = Depends(get_db)):
    return db.query(KanbanBoard).order_by(KanbanBoard.is_archived, KanbanBoard.name).all()


@router.get("/kanban/board-permissions", response_model=AdminBoardPermissionsResponse)
def get_kanban_board_permissions(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = _get_user_or_404(db, user_id)
    is_current_messias = current_user.role and current_user.role.name == "MESSIAS"
    if user.role and user.role.name == "MESSIAS" and not is_current_messias:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado ou inativo")
    return _board_permission_matrix(db, user)


@router.put("/kanban/board-permissions/bulk", response_model=AdminBoardPermissionsResponse)
def update_kanban_board_permissions_bulk(
    data: AdminBoardPermissionBulkRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    target = _get_user_or_404(db, data.user_id)
    is_current_messias = admin_user.role and admin_user.role.name == "MESSIAS"
    if target.role and target.role.name == "MESSIAS" and not is_current_messias:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado ou inativo")
        
    board_ids = {board.id for board in db.query(KanbanBoard.id).all()}
    old_permissions = {
        perm.board_id: perm.access_level
        for perm in db.query(KanbanBoardPermission).filter(KanbanBoardPermission.user_id == target.id).all()
    }
    changed = []
    for item in data.permissions:
        if item.board_id not in board_ids:
            raise HTTPException(status_code=400, detail=f"Quadro {item.board_id} nao encontrado")
        if item.access_level not in BOARD_ACCESS_LEVELS:
            raise HTTPException(status_code=400, detail="Nivel de acesso invalido")
        permission = db.query(KanbanBoardPermission).filter(
            KanbanBoardPermission.board_id == item.board_id,
            KanbanBoardPermission.user_id == target.id,
        ).first()
        previous = permission.access_level if permission else "NO_ACCESS"
        if item.access_level == "NO_ACCESS":
            if permission:
                db.delete(permission)
                changed.append({"board_id": item.board_id, "old": previous, "new": "NO_ACCESS", "action": "removed"})
        elif permission:
            permission.access_level = item.access_level
            permission.updated_at = datetime.now(timezone.utc)
            changed.append({"board_id": item.board_id, "old": previous, "new": item.access_level, "action": "updated"})
        else:
            db.add(KanbanBoardPermission(board_id=item.board_id, user_id=target.id, access_level=item.access_level))
            changed.append({"board_id": item.board_id, "old": "NO_ACCESS", "new": item.access_level, "action": "granted"})

    db.flush()
    action = "admin.kanban_access.bulk_updated" if len(changed) != 1 else {
        "granted": "admin.kanban_access.granted",
        "updated": "admin.kanban_access.updated",
        "removed": "admin.kanban_access.removed",
    }.get(changed[0]["action"], "admin.kanban_access.bulk_updated")
    log_action(
        db=db,
        user_id=admin_user.id,
        action=action,
        module="admin",
        details={
            "target_user_id": target.id,
            "target_username": target.username,
            "old_permissions": old_permissions,
            "changes": changed,
        },
        commit=False,
    )
    db.commit()
    return _board_permission_matrix(db, target)


@router.get("/users/{id}", response_model=UserResponse)
def get_user(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna os detalhes de um usuário específico.
    """
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    is_current_messias = current_user.role and current_user.role.name == "MESSIAS"
    if u.role and u.role.name == "MESSIAS" and not is_current_messias:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Recupera o ID da role ADMIN para mascarar
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    admin_role_id = admin_role.id if admin_role else None
    
    role_id = u.role_id
    role_name = u.role.name if u.role else None

    all_modules = db.query(Module).all()
    mod_perms = []
    for acc in u.module_accesses:
        mod_perms.append({
            "module_id": acc.module_id,
            "module_code": acc.module.code,
            "module_name": acc.module.name,
            "permission_level": acc.permission_level
        })
        
    existing_module_ids = {acc.module_id for acc in u.module_accesses}
    for m in all_modules:
        if m.id not in existing_module_ids:
            mod_perms.append({
                "module_id": m.id,
                "module_code": m.code,
                "module_name": m.name,
                "permission_level": "ADMIN" if (u.role and u.role.name in ["ADMIN", "MESSIAS"]) else "NO_ACCESS"
            })
            
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "department": u.department,
        "job_title": u.job_title,
        "role_id": role_id,
        "role_name": role_name,
        "is_active": u.is_active,
        "must_change_password": u.must_change_password or False,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "last_login": u.last_login,
        "module_permissions": mod_perms
    }


@router.post("/users", response_model=UserResponse)
def create_user(
    data: UserCreateRequest, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Cria um novo usuário no banco com senha hasheada e permissões de módulo iniciais.
    """
    if data.username:
        dup_user = db.query(User).filter(User.username == data.username).first()
        if dup_user:
            raise HTTPException(status_code=400, detail="Este nome de usuario ja esta em uso.")
    if data.email:
        dup_email = db.query(User).filter(User.email == data.email).first()
        if dup_email:
            raise HTTPException(status_code=400, detail="Este e-mail ja esta cadastrado.")
    
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Papel (Role) inválido")

    # Cria o usuário
    new_user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        department=data.department,
        job_title=data.job_title,
        must_change_password=data.must_change_password,
        hashed_password=get_password_hash(data.password),
        role_id=data.role_id,
        is_active=data.is_active,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(new_user)
    db.flush()

    # Adiciona as permissões específicas solicitadas
    for perm in data.module_permissions:
        module = db.query(Module).filter(Module.id == perm.module_id).first()
        if not module:
            raise HTTPException(status_code=400, detail=f"Módulo com id {perm.module_id} não existe")
        
        access = UserModuleAccess(
            user_id=new_user.id,
            module_id=perm.module_id,
            permission_level=perm.permission_level.value
        )
        db.add(access)

    db.commit()
    db.refresh(new_user)

    # Auditoria
    log_action(
        db=db,
        user_id=admin_user.id,
        action="CREATE_USER",
        module="admin",
        details={"created_user_id": new_user.id, "username": new_user.username, "role": role.name},
        commit=True
    )

    # Constrói o retorno
    mod_perms = []
    for acc in new_user.module_accesses:
        mod_perms.append({
            "module_id": acc.module_id,
            "module_code": acc.module.code,
            "module_name": acc.module.name,
            "permission_level": acc.permission_level
        })
    
    all_modules = db.query(Module).all()
    existing_module_ids = {acc.module_id for acc in new_user.module_accesses}
    for m in all_modules:
        if m.id not in existing_module_ids:
            mod_perms.append({
                "module_id": m.id,
                "module_code": m.code,
                "module_name": m.name,
                "permission_level": "ADMIN" if role.name == "ADMIN" else "NO_ACCESS"
            })

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "department": new_user.department,
        "job_title": new_user.job_title,
        "role_id": new_user.role_id,
        "role_name": role.name,
        "is_active": new_user.is_active,
        "must_change_password": new_user.must_change_password or False,
        "created_at": new_user.created_at,
        "updated_at": new_user.updated_at,
        "last_login": new_user.last_login,
        "module_permissions": mod_perms
    }


@router.patch("/users/{id}", response_model=UserResponse)
def update_user(
    id: int, 
    data: UserUpdateRequest, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Atualiza dados básicos do usuário (username, e-mail, papel, status ativo).
    Previne que o último administrador ativo seja desativado ou rebaixado.
    """
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    is_current_messias = admin_user.role and admin_user.role.name == "MESSIAS"
    if u.role and u.role.name == "MESSIAS" and not is_current_messias:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    
    # Valida regras para o último administrador ativo
    if (data.is_active is False) or (data.role_id is not None and data.role_id != admin_role.id):
        if u.role and u.role.name == "ADMIN":
            active_admins = db.query(User).join(Role).filter(
                Role.name == "ADMIN",
                User.is_active == True
            ).count()
            
            if active_admins <= 1 and u.is_active:
                raise HTTPException(
                    status_code=400,
                    detail="Operação negada. Não é permitido inativar ou remover o papel ADMIN do único administrador ativo do sistema."
                )

    old_values = {
        "username": u.username,
        "email": u.email,
        "role_id": u.role_id,
        "is_active": u.is_active
    }
    
    if data.username is not None:
        dup = db.query(User).filter(User.username == data.username, User.id != id).first()
        if dup:
            raise HTTPException(status_code=400, detail="Este nome de usuario ja esta em uso.")
        u.username = data.username
        
    if data.email is not None:
        if data.email.strip() != "":
            dup = db.query(User).filter(User.email == data.email, User.id != id).first()
            if dup:
                raise HTTPException(status_code=400, detail="Este e-mail ja esta cadastrado.")
            u.email = data.email
        else:
            u.email = None
        
    if data.password is not None and data.password.strip() != "":
        u.hashed_password = get_password_hash(data.password)
        
    if data.role_id is not None:
        role = db.query(Role).filter(Role.id == data.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="Papel (Role) inválido")
        u.role_id = data.role_id
        
    if data.full_name is not None:
        u.full_name = data.full_name
    if data.department is not None:
        u.department = data.department
    if data.job_title is not None:
        u.job_title = data.job_title
    if data.must_change_password is not None:
        u.must_change_password = data.must_change_password

    if data.is_active is not None:
        if data.is_active is False and u.is_active is True:
            sessions = db.query(UserSession).filter(
                UserSession.user_id == u.id,
                UserSession.revoked_at.is_(None),
            ).all()
            now_utc = datetime.now(timezone.utc)
            for s_item in sessions:
                s_item.revoked_at = now_utc
                s_item.revoked_by_user_id = admin_user.id
                s_item.revocation_reason = "Usuario inativado pela administracao"
            
            accesses = db.query(UserTemporaryAccess).filter(
                UserTemporaryAccess.target_user_id == u.id,
                UserTemporaryAccess.status == "ACTIVE",
            ).all()
            for acc in accesses:
                acc.status = "REVOKED"
                acc.revoked_at = now_utc
                acc.revoked_by_user_id = admin_user.id
                acc.revocation_reason = "Usuario inativado pela administracao"
        u.is_active = data.is_active

    u.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(u)

    # Auditoria
    log_action(
        db=db,
        user_id=admin_user.id,
        action="UPDATE_USER",
        module="admin",
        details={
            "updated_user_id": u.id,
            "old_values": old_values,
            "new_values": {
                "username": u.username,
                "email": u.email,
                "role_id": u.role_id,
                "is_active": u.is_active
            }
        },
        commit=True
    )

    # Retorno
    mod_perms = []
    for acc in u.module_accesses:
        mod_perms.append({
            "module_id": acc.module_id,
            "module_code": acc.module.code,
            "module_name": acc.module.name,
            "permission_level": acc.permission_level
        })
        
    all_modules = db.query(Module).all()
    existing_module_ids = {acc.module_id for acc in u.module_accesses}
    for m in all_modules:
        if m.id not in existing_module_ids:
            mod_perms.append({
                "module_id": m.id,
                "module_code": m.code,
                "module_name": m.name,
                "permission_level": "ADMIN" if u.role and u.role.name == "ADMIN" else "NO_ACCESS"
            })

    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "department": u.department,
        "job_title": u.job_title,
        "role_id": u.role_id,
        "role_name": u.role.name if u.role else None,
        "is_active": u.is_active,
        "must_change_password": u.must_change_password or False,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "last_login": u.last_login,
        "module_permissions": mod_perms
    }


@router.patch("/users/{id}/module-access", response_model=UserResponse)
def update_user_module_access(
    id: int, 
    data: ModuleAccessUpdateRequest, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Atualiza as permissões de acesso a módulos de um usuário específico.
    """
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    is_current_messias = admin_user.role and admin_user.role.name == "MESSIAS"
    if u.role and u.role.name == "MESSIAS" and not is_current_messias:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    old_permissions = {acc.module.code: acc.permission_level for acc in u.module_accesses}

    # Atualiza ou cria as permissões específicas
    for perm in data.permissions:
        module = db.query(Module).filter(Module.id == perm.module_id).first()
        if not module:
            raise HTTPException(status_code=400, detail=f"Módulo com id {perm.module_id} não existe")
        
        access = db.query(UserModuleAccess).filter(
            UserModuleAccess.user_id == u.id,
            UserModuleAccess.module_id == perm.module_id
        ).first()

        if access:
            access.permission_level = perm.permission_level.value
        else:
            access = UserModuleAccess(
                user_id=u.id,
                module_id=perm.module_id,
                permission_level=perm.permission_level.value
            )
            db.add(access)

    u.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(u)

    new_permissions = {acc.module.code: acc.permission_level for acc in u.module_accesses}

    # Auditoria
    log_action(
        db=db,
        user_id=admin_user.id,
        action="admin.module_access.updated",
        module="admin",
        details={
            "updated_user_id": u.id,
            "old_permissions": old_permissions,
            "new_permissions": new_permissions
        },
        commit=True
    )

    # Retorno
    mod_perms = []
    for acc in u.module_accesses:
        mod_perms.append({
            "module_id": acc.module_id,
            "module_code": acc.module.code,
            "module_name": acc.module.name,
            "permission_level": acc.permission_level
        })
        
    all_modules = db.query(Module).all()
    existing_module_ids = {acc.module_id for acc in u.module_accesses}
    for m in all_modules:
        if m.id not in existing_module_ids:
            mod_perms.append({
                "module_id": m.id,
                "module_code": m.code,
                "module_name": m.name,
                "permission_level": "ADMIN" if u.role and u.role.name == "ADMIN" else "NO_ACCESS"
            })

    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "department": u.department,
        "job_title": u.job_title,
        "role_id": u.role_id,
        "role_name": u.role.name if u.role else None,
        "is_active": u.is_active,
        "must_change_password": u.must_change_password or False,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "last_login": u.last_login,
        "module_permissions": mod_perms
    }


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a lista de papéis (Roles) disponíveis.
    """
    roles = db.query(Role).order_by(Role.id).all()
    is_current_messias = current_user.role and current_user.role.name == "MESSIAS"
    if not is_current_messias:
        roles = [r for r in roles if r.name != "MESSIAS"]
    return roles


@router.get("/modules", response_model=List[ModuleResponse])
def list_modules(db: Session = Depends(get_db)):
    """
    Retorna a lista de módulos registrados no sistema.
    """
    return db.query(Module).order_by(Module.id).all()


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(db: Session = Depends(get_db)):
    """
    Retorna os últimos 100 logs de auditoria ordenados por data.
    """
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    result = []
    
    for log in logs:
        username = None
        if log.user_id:
            user = db.query(User).filter(User.id == log.user_id).first()
            if user:
                username = user.username
                
        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": username,
            "action": log.action,
            "module": log.module,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        })
        
    return result


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exclui fisicamente um usuário do banco de dados.
    Impede a exclusão do super-usuário MESSIAS e do próprio administrador logado.
    Trata violações de chave estrangeira (RESTRICT) de forma amigável ao usuário.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    
    if user.username == "MESSIAS" or (user.role and user.role.name == "MESSIAS"):
        raise HTTPException(
            status_code=400,
            detail="Acao nao permitida: O super-usuario MESSIAS nao pode ser excluido."
        )
        
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Acao nao permitida: Voce nao pode excluir sua propria conta administrativa."
        )
        
    try:
        username = user.username
        db.delete(user)
        db.commit()
        log_action(
            db=db,
            user_id=current_user.id,
            action="admin.user.deleted",
            module="admin",
            details={"deleted_user_id": user_id, "deleted_username": username}
        )
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if "foreign key" in error_msg.lower() or "violates foreign key constraint" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Nao e possivel excluir o usuario '{user.username}' porque ele possui registros de atividades (como chamados de TI, mensagens de chat ou aprovacoes) vinculados. Em vez de excluir, desative o usuario na aba Seguranca para revogar o acesso."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao excluir usuario: {error_msg}"
        )


@router.get("/users/{user_id}/sessions")
def list_user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).order_by(UserSession.created_at.desc()).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [
        {
            "id": session.id,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "created_at": session.created_at,
            "last_activity_at": session.last_activity_at,
            "expires_at": session.expires_at,
            "revoked_at": session.revoked_at,
            "revocation_reason": session.revocation_reason,
            "is_active": session.revoked_at is None and session.expires_at > now
        }
        for session in sessions
    ]


@router.post("/users/{user_id}/sessions/{session_id}/revoke")
def revoke_user_session(
    user_id: int,
    session_id: int,
    data: RevokeSessionRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    session = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session.revoked_at = now
    session.revoked_by_user_id = admin_user.id
    session.revocation_reason = data.reason or "Revogada manualmente pela administracao"
    db.commit()
    db.refresh(session)
    
    log_action(
        db=db,
        user_id=admin_user.id,
        action="admin.session.revoked",
        module="admin",
        details={
            "target_user_id": user_id,
            "session_db_id": session.id,
            "reason": session.revocation_reason
        },
        commit=True
    )
    
    return {
        "id": session.id,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "created_at": session.created_at,
        "last_activity_at": session.last_activity_at,
        "expires_at": session.expires_at,
        "revoked_at": session.revoked_at,
        "revocation_reason": session.revocation_reason,
        "is_active": session.revoked_at is None and session.expires_at > now
    }


@router.get("/users/{user_id}/temporary-access")
def list_user_temporary_access(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    accesses = db.query(UserTemporaryAccess).filter(
        UserTemporaryAccess.target_user_id == user_id
    ).order_by(UserTemporaryAccess.created_at.desc()).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [
        {
            "id": acc.id,
            "module_id": acc.module_id,
            "module_code": acc.module.code,
            "module_name": acc.module.name,
            "permission_level": acc.permission_level,
            "reason": acc.reason,
            "starts_at": acc.starts_at,
            "expires_at": acc.expires_at,
            "status": acc.status,
            "revoked_at": acc.revoked_at,
            "revocation_reason": acc.revocation_reason,
            "is_effective": acc.status == "ACTIVE" and acc.starts_at <= now and acc.expires_at > now and acc.revoked_at is None
        }
        for acc in accesses
    ]


@router.post("/users/{user_id}/temporary-access")
def create_user_temporary_access(
    user_id: int,
    data: TemporaryAccessCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    
    module = db.query(Module).filter(Module.id == data.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Modulo nao encontrado")
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at_naive = data.expires_at.replace(tzinfo=None) if data.expires_at.tzinfo else data.expires_at
    if expires_at_naive <= now:
        raise HTTPException(status_code=400, detail="Data de expiracao deve ser no futuro")
        
    access = UserTemporaryAccess(
        target_user_id=user_id,
        module_id=data.module_id,
        permission_level=data.permission_level,
        reason=data.reason,
        starts_at=now,
        expires_at=expires_at_naive,
        status="ACTIVE",
        created_by_user_id=admin_user.id
    )
    db.add(access)
    db.commit()
    db.refresh(access)
    
    log_action(
        db=db,
        user_id=admin_user.id,
        action="admin.temporary_access.created",
        module="admin",
        details={
            "target_user_id": user_id,
            "module_code": module.code,
            "permission_level": data.permission_level,
            "expires_at": expires_at_naive.isoformat()
        },
        commit=True
    )
    
    return {
        "id": access.id,
        "module_id": access.module_id,
        "module_code": module.code,
        "module_name": module.name,
        "permission_level": access.permission_level,
        "reason": access.reason,
        "starts_at": access.starts_at,
        "expires_at": access.expires_at,
        "status": access.status,
        "revoked_at": access.revoked_at,
        "revocation_reason": access.revocation_reason,
        "is_effective": access.status == "ACTIVE" and access.starts_at <= now and access.expires_at > now and access.revoked_at is None
    }


@router.post("/users/{user_id}/temporary-access/{access_id}/revoke")
def revoke_user_temporary_access(
    user_id: int,
    access_id: int,
    data: RevokeSessionRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    access = db.query(UserTemporaryAccess).filter(
        UserTemporaryAccess.target_user_id == user_id,
        UserTemporaryAccess.id == access_id
    ).first()
    if not access:
        raise HTTPException(status_code=404, detail="Acesso temporario nao encontrado")
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    access.status = "REVOKED"
    access.revoked_at = now
    access.revoked_by_user_id = admin_user.id
    access.revocation_reason = data.reason or "Revogado pela administracao"
    db.commit()
    db.refresh(access)
    
    log_action(
        db=db,
        user_id=admin_user.id,
        action="admin.temporary_access.revoked",
        module="admin",
        details={
            "target_user_id": user_id,
            "access_id": access.id,
            "reason": access.revocation_reason
        },
        commit=True
    )
    
    return {
        "id": access.id,
        "module_id": access.module_id,
        "module_code": access.module.code,
        "module_name": access.module.name,
        "permission_level": access.permission_level,
        "reason": access.reason,
        "starts_at": access.starts_at,
        "expires_at": access.expires_at,
        "status": access.status,
        "revoked_at": access.revoked_at,
        "revocation_reason": access.revocation_reason,
        "is_effective": False
    }


@router.get("/users/{user_id}/temporary-substitutions")
def list_user_temporary_substitutions(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    subs = db.query(UserTemporarySubstitution).filter(
        UserTemporarySubstitution.replaced_user_id == user_id
    ).order_by(UserTemporarySubstitution.created_at.desc()).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [
        {
            "id": sub.id,
            "substitute_user_id": sub.substitute_user_id,
            "substitute_username": sub.substitute_user.username,
            "reason": sub.reason,
            "starts_at": sub.starts_at,
            "expires_at": sub.expires_at,
            "status": sub.status,
            "ended_at": sub.ended_at,
            "is_effective": sub.status == "ACTIVE" and sub.starts_at <= now and sub.expires_at > now and sub.ended_at is None
        }
        for sub in subs
    ]


@router.post("/users/{user_id}/temporary-substitutions")
def create_user_temporary_substitution(
    user_id: int,
    data: TemporarySubstitutionCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario a ser substituido nao encontrado")
        
    substitute = db.query(User).filter(User.id == data.substitute_user_id).first()
    if not substitute:
        raise HTTPException(status_code=404, detail="Usuario substituto nao encontrado")
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at_naive = data.expires_at.replace(tzinfo=None) if data.expires_at.tzinfo else data.expires_at
    if expires_at_naive <= now:
        raise HTTPException(status_code=400, detail="Data de expiracao deve ser no futuro")
        
    sub = UserTemporarySubstitution(
        replaced_user_id=user_id,
        substitute_user_id=data.substitute_user_id,
        reason=data.reason,
        starts_at=now,
        expires_at=expires_at_naive,
        status="ACTIVE",
        created_by_user_id=admin_user.id
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    
    log_action(
        db=db,
        user_id=admin_user.id,
        action="admin.temporary_substitution.created",
        module="admin",
        details={
            "replaced_user_id": user_id,
            "substitute_user_id": data.substitute_user_id,
            "expires_at": expires_at_naive.isoformat()
        },
        commit=True
    )
    
    return {
        "id": sub.id,
        "substitute_user_id": sub.substitute_user_id,
        "substitute_username": substitute.username,
        "reason": sub.reason,
        "starts_at": sub.starts_at,
        "expires_at": sub.expires_at,
        "status": sub.status,
        "ended_at": sub.ended_at,
        "is_effective": sub.status == "ACTIVE" and sub.starts_at <= now and sub.expires_at > now and sub.ended_at is None
    }


@router.get("/users/{user_id}/offboarding/impact")
def get_user_offboarding_impact(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    from app.modules.admin.lifecycle import build_offboarding_impact
    return build_offboarding_impact(db, user_id)


@router.post("/users/{user_id}/offboarding")
def initiate_user_offboarding(
    user_id: int,
    data: OffboardingCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    from app.modules.admin.lifecycle import build_offboarding_impact, create_offboarding_tasks, ensure_not_last_active_admin
    
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    ensure_not_last_active_admin(db, target)
        
    impact = build_offboarding_impact(db, user_id)
    
    case = UserOffboardingCase(
        target_user_id=user_id,
        replacement_user_id=data.replacement_user_id,
        status="DRAFT",
        reason=data.reason,
        impact_snapshot=impact,
        created_by_user_id=admin_user.id
    )
    db.add(case)
    db.flush()
    
    create_offboarding_tasks(db, case)
    db.commit()
    db.refresh(case)
    
    log_action(
        db=db,
        user_id=admin_user.id,
        action="admin.offboarding.initiated",
        module="admin",
        details={
            "case_id": case.id,
            "target_user_id": user_id,
            "reason": data.reason
        },
        commit=True
    )
    
    return {
        "id": case.id,
        "status": case.status,
        "reason": case.reason,
        "replacement_user_id": case.replacement_user_id,
        "impact_snapshot": case.impact_snapshot,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "requires_human_review": task.requires_human_review
            }
            for task in case.tasks
        ]
    }


@router.post("/offboarding/{case_id}/confirm")
def confirm_user_offboarding(
    case_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    from app.modules.admin.lifecycle import confirm_offboarding_case
    case = db.query(UserOffboardingCase).filter(UserOffboardingCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso de desligamento nao encontrado")
        
    counts = confirm_offboarding_case(db, case, admin_user)
    db.commit()
    db.refresh(case)
    
    log_action(
        db=db,
        user_id=admin_user.id,
        action="admin.offboarding.confirmed",
        module="admin",
        details={
            "case_id": case.id,
            "target_user_id": case.target_user_id,
            "applied_counts": counts
        },
        commit=True
    )
    
    return {
        "status": "success",
        "applied_counts": counts,
        "case": {
            "id": case.id,
            "status": case.status,
            "reason": case.reason,
            "replacement_user_id": case.replacement_user_id,
            "impact_snapshot": case.impact_snapshot,
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "requires_human_review": task.requires_human_review
                }
                for task in case.tasks
            ]
        }
    }


@router.post("/temporary-access/sweep")
def sweep_temporary_records(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    from app.modules.admin.lifecycle import sweep_expired_temporary_records
    counts = sweep_expired_temporary_records(db)
    return {"status": "success", "applied_counts": counts}


@router.post("/offboarding/tasks/{task_id}/complete")
def complete_offboarding_task(
    task_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    task = db.query(UserOffboardingTask).filter(UserOffboardingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa de desligamento nao encontrada")
    
    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return {"status": "success", "task_id": task.id, "task_status": task.status}


@router.post("/offboarding/tasks/{task_id}/fail")
def fail_offboarding_task(
    task_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    task = db.query(UserOffboardingTask).filter(UserOffboardingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa de desligamento nao encontrada")
    
    task.status = "FAILED"
    task.completed_at = None
    db.commit()
    db.refresh(task)
    return {"status": "success", "task_id": task.id, "task_status": task.status}


@router.post("/offboarding/{case_id}/cancel")
def cancel_offboarding_case(
    case_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    case = db.query(UserOffboardingCase).filter(UserOffboardingCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso de desligamento nao encontrado")
        
    if case.status == "CONFIRMED":
        raise HTTPException(status_code=400, detail="Nao e possivel cancelar um desligamento ja confirmado")
        
    case.status = "CANCELLED"
    case.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(case)
    return {"status": "success", "case_id": case.id, "case_status": case.status}

