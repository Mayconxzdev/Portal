from sqlalchemy.orm import Session

from app.models.it import ITTicket


def get_ticket(db: Session, ticket_id: int) -> ITTicket | None:
    return db.query(ITTicket).filter(ITTicket.id == ticket_id).first()
