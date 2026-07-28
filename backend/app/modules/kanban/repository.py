from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.kanban import (
    KanbanBoard,
    KanbanCard,
    KanbanColumn,
    KanbanCustomField,
    KanbanCardChecklist,
    KanbanCardAttachment,
    KanbanCardAssignee,
    KanbanCardLabel,
)


def get_board(db: Session, board_id: int) -> KanbanBoard | None:
    return (
        db.query(KanbanBoard)
        .options(
            joinedload(KanbanBoard.columns).joinedload(KanbanColumn.cards),
            joinedload(KanbanBoard.custom_fields),
            joinedload(KanbanBoard.permissions),
            joinedload(KanbanBoard.labels),
            joinedload(KanbanBoard.views),
        )
        .filter(KanbanBoard.id == board_id)
        .first()
    )


def get_card(db: Session, card_id: int) -> KanbanCard | None:
    return (
        db.query(KanbanCard)
        .options(
            selectinload(KanbanCard.checklists).selectinload(KanbanCardChecklist.items),
            selectinload(KanbanCard.attachments).selectinload(KanbanCardAttachment.file),
            selectinload(KanbanCard.assignees).selectinload(KanbanCardAssignee.user),
            selectinload(KanbanCard.label_links).selectinload(KanbanCardLabel.label),
        )
        .filter(KanbanCard.id == card_id)
        .first()
    )


def get_column(db: Session, column_id: int) -> KanbanColumn | None:
    return db.query(KanbanColumn).filter(KanbanColumn.id == column_id).first()


def get_custom_field(db: Session, field_id: int) -> KanbanCustomField | None:
    return db.query(KanbanCustomField).filter(KanbanCustomField.id == field_id).first()
