from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.kanban.schemas import (
    ActivityResponse,
    BoardCreate,
    BoardDuplicatePayload,
    BoardImportConfirmPayload,
    BoardImportPreviewResponse,
    BoardPermissionResponse,
    BoardPermissionUpsert,
    BoardResponse,
    BoardViewCreate,
    BoardViewResponse,
    BoardViewUpdate,
    BoardUpdate,
    CardCreate,
    CardDuplicatePayload,
    CardMovePayload,
    CardResponse,
    CardUpdate,
    AttachmentResponse,
    ChecklistCreate,
    ChecklistItemCreate,
    ChecklistItemReorderPayload,
    ChecklistItemResponse,
    ChecklistItemUpdate,
    ChecklistResponse,
    ChecklistUpdate,
    ColumnCreate,
    ColumnReorderPayload,
    ColumnResponse,
    ColumnUpdate,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    CustomFieldCreate,
    CustomFieldResponse,
    CustomFieldUpdate,
    KanbanSummaryResponse,
    LabelCreate,
    LabelResponse,
    LabelUpdate,
    CardAssigneeResponse,
    QuickCardPayload,
    TVConfigResponse,
    TVConfigUpdate,
    UserMiniResponse,
)
from app.modules.kanban.service import KanbanService


router = APIRouter()


@router.get("/")
def kanban_root():
    return {"status": "success", "module": "kanban"}


@router.get("/boards", response_model=List[BoardResponse])
def list_boards(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return KanbanService.list_boards(db, current_user, include_archived=include_archived)


@router.post("/boards", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
def create_board(payload: BoardCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_board(db, payload, current_user)


@router.get("/boards/{board_id}", response_model=BoardResponse)
def get_board(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_board_detail(db, board_id, current_user)


@router.patch("/boards/{board_id}", response_model=BoardResponse)
def update_board(board_id: int, payload: BoardUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_board(db, board_id, payload, current_user)


@router.post("/boards/{board_id}/archive", response_model=BoardResponse)
def archive_board(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.set_board_archived(db, board_id, True, current_user)


@router.post("/boards/{board_id}/restore", response_model=BoardResponse)
def restore_board(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.set_board_archived(db, board_id, False, current_user)


@router.post("/boards/{board_id}/duplicate", response_model=BoardResponse)
def duplicate_board(board_id: int, payload: BoardDuplicatePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.duplicate_board(db, board_id, payload, current_user)


@router.delete("/boards/{board_id}")
def delete_board(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_board(db, board_id, current_user)


@router.get("/boards/{board_id}/views", response_model=List[BoardViewResponse])
def list_views(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_views(db, board_id, current_user)


@router.post("/boards/{board_id}/views", response_model=BoardViewResponse, status_code=status.HTTP_201_CREATED)
def create_view(board_id: int, payload: BoardViewCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_view(db, board_id, payload, current_user)


@router.patch("/board-views/{view_id}", response_model=BoardViewResponse)
def update_view(view_id: int, payload: BoardViewUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_view(db, view_id, payload, current_user)


@router.delete("/board-views/{view_id}")
def delete_view(view_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_view(db, view_id, current_user)


@router.post("/board-views/{view_id}/set-default", response_model=BoardViewResponse)
def set_default_view(view_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.set_default_view(db, view_id, current_user)


@router.post("/board-views/{view_id}/duplicate", response_model=BoardViewResponse)
def duplicate_view(view_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.duplicate_view(db, view_id, current_user)


@router.get("/boards/{board_id}/list-data")
def get_list_data(board_id: int, view_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_list_data(db, board_id, current_user, view_id=view_id)


@router.get("/boards/{board_id}/permissions", response_model=List[BoardPermissionResponse])
def list_board_permissions(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_board_permissions(db, board_id, current_user)


@router.post("/boards/{board_id}/permissions", response_model=BoardPermissionResponse)
def upsert_board_permission(board_id: int, payload: BoardPermissionUpsert, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.upsert_board_permission(db, board_id, payload, current_user)


@router.delete("/boards/{board_id}/permissions/{permission_id}")
def delete_board_permission(board_id: int, permission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_board_permission(db, board_id, permission_id, current_user)


@router.post("/boards/{board_id}/import/preview", response_model=BoardImportPreviewResponse)
async def preview_import(board_id: int, upload: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await KanbanService.preview_import(db, board_id, upload, current_user)


@router.post("/boards/{board_id}/import/confirm")
def confirm_import(board_id: int, payload: BoardImportConfirmPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.confirm_import(db, board_id, payload, current_user)


@router.post("/boards/{board_id}/columns", response_model=ColumnResponse, status_code=status.HTTP_201_CREATED)
def create_column(board_id: int, payload: ColumnCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_column(db, board_id, payload, current_user)


@router.patch("/columns/{column_id}", response_model=ColumnResponse)
def update_column(column_id: int, payload: ColumnUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_column(db, column_id, payload, current_user)


@router.post("/columns/{column_id}/archive", response_model=ColumnResponse)
def archive_column(column_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.archive_column(db, column_id, current_user)


@router.post("/columns/{column_id}/restore", response_model=ColumnResponse)
def restore_column(column_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.restore_column(db, column_id, current_user)


@router.delete("/columns/{column_id}")
def delete_column(column_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_column(db, column_id, current_user)


@router.post("/boards/{board_id}/columns/reorder", response_model=List[ColumnResponse])
def reorder_columns(board_id: int, payload: ColumnReorderPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.reorder_columns(db, board_id, payload, current_user)


@router.post("/boards/{board_id}/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_card(board_id: int, payload: CardCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_card(db, board_id, payload, current_user)


@router.get("/cards/{card_id}", response_model=CardResponse)
def get_card(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_card_detail(db, card_id, current_user)


@router.get("/boards/{board_id}/cards/search", response_model=List[CardResponse])
def search_cards(
    board_id: int,
    text: str | None = None,
    priority: str | None = None,
    column_id: int | None = None,
    assignee_id: int | None = None,
    label_id: int | None = None,
    overdue: bool = Query(False),
    archived: bool = Query(False),
    created_by_me: bool = Query(False),
    assigned_to_me: bool = Query(False),
    unassigned: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return KanbanService.search_cards(
        db,
        board_id,
        current_user,
        text=text,
        priority=priority,
        column_id=column_id,
        assignee_id=assignee_id,
        label_id=label_id,
        overdue=overdue,
        archived=archived,
        created_by_me=created_by_me,
        assigned_to_me=assigned_to_me,
        unassigned=unassigned,
    )


@router.get("/boards/{board_id}/tv-config", response_model=TVConfigResponse)
def get_tv_config(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_tv_config(db, board_id, current_user)


@router.patch("/boards/{board_id}/tv-config", response_model=TVConfigResponse)
def update_tv_config(board_id: int, payload: TVConfigUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_tv_config(db, board_id, payload, current_user)


@router.get("/boards/{board_id}/metrics")
def get_board_metrics(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_board_metrics(db, board_id, current_user)


@router.get("/boards/{board_id}/critical-cards")
def get_critical_cards(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_critical_cards(db, board_id, current_user)


@router.get("/boards/{board_id}/tv-data")
def get_tv_data(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_tv_data(db, board_id, current_user)


@router.get("/boards/{board_id}/tv-snapshot")
def get_tv_snapshot(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_tv_data(db, board_id, current_user)


@router.post("/quick-card")
def quick_card(payload: QuickCardPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.quick_card(db, payload, current_user)


@router.patch("/cards/{card_id}", response_model=CardResponse)
def update_card(card_id: int, payload: CardUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_card(db, card_id, payload, current_user)


@router.post("/cards/{card_id}/move", response_model=CardResponse)
def move_card(card_id: int, payload: CardMovePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.move_card(db, card_id, payload, current_user)


@router.post("/cards/{card_id}/archive", response_model=CardResponse)
def archive_card(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.set_card_archived(db, card_id, True, current_user)


@router.post("/cards/{card_id}/restore", response_model=CardResponse)
def restore_card(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.set_card_archived(db, card_id, False, current_user)


@router.post("/cards/{card_id}/duplicate", response_model=CardResponse)
def duplicate_card(card_id: int, payload: CardDuplicatePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.duplicate_card(db, card_id, payload, current_user)


@router.delete("/cards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_card(db, card_id, current_user)


@router.get("/boards/{board_id}/custom-fields", response_model=List[CustomFieldResponse])
def list_custom_fields(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_custom_fields(db, board_id, current_user)


@router.post("/boards/{board_id}/custom-fields", response_model=CustomFieldResponse, status_code=status.HTTP_201_CREATED)
def create_custom_field(board_id: int, payload: CustomFieldCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_custom_field(db, board_id, payload, current_user)


@router.patch("/custom-fields/{field_id}", response_model=CustomFieldResponse)
def update_custom_field(field_id: int, payload: CustomFieldUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_custom_field(db, field_id, payload, current_user)


@router.delete("/custom-fields/{field_id}")
def delete_custom_field(field_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_custom_field(db, field_id, current_user)


@router.get("/boards/{board_id}/activity", response_model=List[ActivityResponse])
def list_board_activity(board_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_board_activity(db, board_id, current_user)


@router.get("/cards/{card_id}/activity", response_model=List[ActivityResponse])
def list_card_activity(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_card_activity(db, card_id, current_user)


@router.get("/cards/{card_id}/checklists", response_model=List[ChecklistResponse])
def list_checklists(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_checklists(db, card_id, current_user)


@router.post("/cards/{card_id}/checklists", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED)
def create_checklist(card_id: int, payload: ChecklistCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_checklist(db, card_id, payload, current_user)


@router.patch("/checklists/{checklist_id}", response_model=ChecklistResponse)
def update_checklist(checklist_id: int, payload: ChecklistUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_checklist(db, checklist_id, payload, current_user)


@router.delete("/checklists/{checklist_id}")
def delete_checklist(checklist_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_checklist(db, checklist_id, current_user)


@router.post("/checklists/{checklist_id}/items", response_model=ChecklistItemResponse, status_code=status.HTTP_201_CREATED)
def create_checklist_item(checklist_id: int, payload: ChecklistItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_checklist_item(db, checklist_id, payload, current_user)


@router.patch("/checklist-items/{item_id}", response_model=ChecklistItemResponse)
def update_checklist_item(item_id: int, payload: ChecklistItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_checklist_item(db, item_id, payload, current_user)


@router.delete("/checklist-items/{item_id}")
def delete_checklist_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_checklist_item(db, item_id, current_user)


@router.post("/checklists/{checklist_id}/items/reorder", response_model=List[ChecklistItemResponse])
def reorder_checklist_items(checklist_id: int, payload: ChecklistItemReorderPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.reorder_checklist_items(db, checklist_id, payload, current_user)


@router.get("/cards/{card_id}/comments", response_model=List[CommentResponse])
def list_comments(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_comments(db, card_id, current_user)


@router.post("/cards/{card_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(card_id: int, payload: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_comment(db, card_id, payload, current_user)


@router.patch("/card-comments/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: int, payload: CommentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_comment(db, comment_id, payload, current_user)


@router.delete("/card-comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_comment(db, comment_id, current_user)


@router.get("/cards/{card_id}/attachments", response_model=List[AttachmentResponse])
def list_attachments(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_attachments(db, card_id, current_user)


@router.post("/cards/{card_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_attachment(card_id: int, upload: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.upload_attachment(db, card_id, upload, current_user)


@router.get("/card-attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.download_attachment(db, attachment_id, current_user)


@router.delete("/card-attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_attachment(db, attachment_id, current_user)


@router.get("/boards/{board_id}/labels", response_model=List[LabelResponse])
def list_labels(board_id: int, include_inactive: bool = Query(False), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_labels(db, board_id, current_user, include_inactive=include_inactive)


@router.post("/boards/{board_id}/labels", response_model=LabelResponse, status_code=status.HTTP_201_CREATED)
def create_label(board_id: int, payload: LabelCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.create_label(db, board_id, payload, current_user)


@router.patch("/labels/{label_id}", response_model=LabelResponse)
def update_label(label_id: int, payload: LabelUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.update_label(db, label_id, payload, current_user)


@router.delete("/labels/{label_id}")
def delete_label(label_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.delete_label(db, label_id, current_user)


@router.post("/cards/{card_id}/labels/{label_id}", response_model=CardResponse)
def apply_label(card_id: int, label_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.apply_label(db, card_id, label_id, current_user)


@router.delete("/cards/{card_id}/labels/{label_id}", response_model=CardResponse)
def remove_label(card_id: int, label_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.remove_label(db, card_id, label_id, current_user)


@router.get("/cards/{card_id}/assignees", response_model=List[CardAssigneeResponse])
def list_assignees(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.list_assignees(db, card_id, current_user)


@router.post("/cards/{card_id}/assignees/{user_id}", response_model=CardResponse)
def add_assignee(card_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.add_assignee(db, card_id, user_id, current_user)


@router.delete("/cards/{card_id}/assignees/{user_id}", response_model=CardResponse)
def remove_assignee(card_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.remove_assignee(db, card_id, user_id, current_user)


@router.get("/summary", response_model=KanbanSummaryResponse)
def get_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return KanbanService.get_summary(db, current_user)


@router.get("/users", response_model=List[UserMiniResponse])
def kanban_list_users(
    search: str | None = Query(None),
    board_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.permissions import PermissionLevel
    from app.modules.kanban.permissions import BoardAccessLevel, require_board_level, require_module_level
    require_module_level(db, current_user, PermissionLevel.READ_ONLY)
    if board_id is not None:
        if not (current_user.role and current_user.role.name == "ADMIN"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Busca de acessos por quadro fica na Administracao.")
        board = KanbanService.get_board_detail(db, board_id, current_user)
        require_board_level(db, board, current_user, BoardAccessLevel.ADMIN)
    query = db.query(User).filter(User.is_active == True)
    if not (current_user.role and current_user.role.name == "MESSIAS"):
        from app.models.role import Role
        query = query.outerjoin(Role).filter((Role.name != "MESSIAS") | (Role.id == None))
    if search:
        like = f"%{search}%"
        query = query.filter(or_(User.username.ilike(like), User.email.ilike(like)))
    return query.order_by(User.username).limit(50).all()


@router.get("/roles")
def kanban_list_roles(
    board_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.permissions import PermissionLevel
    from app.modules.kanban.permissions import BoardAccessLevel, require_board_level, require_module_level
    require_module_level(db, current_user, PermissionLevel.READ_ONLY)
    if board_id is not None:
        if not (current_user.role and current_user.role.name == "ADMIN"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Busca de perfis por quadro fica na Administracao.")
        board = KanbanService.get_board_detail(db, board_id, current_user)
        require_board_level(db, board, current_user, BoardAccessLevel.ADMIN)
    from app.models.role import Role
    roles = db.query(Role).order_by(Role.id).all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]
