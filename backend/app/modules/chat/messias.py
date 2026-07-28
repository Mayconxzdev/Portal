from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Optional
import logging

from app.models.user import User
from app.modules.chat.repository import ChatRepository
from app.modules.chat.permissions import ChatPermissions

# messias_user_id -> target_user_id
ACTIVE_SIMULATIONS: Dict[int, int] = {}

logger = logging.getLogger("chat.messias")


class ChatMessiasManager:
    @staticmethod
    def start_simulation(db: Session, messias_user: User, target_user_id: int) -> User:
        """
        Inicia a simulação de visualização como outro usuário.
        Dispara log de auditoria do MESSIAS.
        """
        if not ChatPermissions.is_messias(messias_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Apenas usuários com papel MESSIAS podem utilizar a simulação."
            )
            
        target_user = db.query(User).filter(User.id == target_user_id, User.is_active == True).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Usuário alvo da simulação nao encontrado ou inativo."
            )
            
        ACTIVE_SIMULATIONS[messias_user.id] = target_user_id
        
        # Log da auditoria
        ChatRepository.create_messias_audit_log(
            db=db,
            messias_user_id=messias_user.id,
            action="chat.messias.view_as_user.started",
            target_user_id=target_user_id,
            metadata={"target_username": target_user.username}
        )
        db.commit()
        
        return target_user

    @staticmethod
    def stop_simulation(db: Session, messias_user: User) -> Optional[int]:
        """
        Encerra a simulação ativa.
        """
        if not ChatPermissions.is_messias(messias_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Apenas usuários com papel MESSIAS podem utilizar a simulação."
            )
            
        target_user_id = ACTIVE_SIMULATIONS.pop(messias_user.id, None)
        if target_user_id:
            ChatRepository.create_messias_audit_log(
                db=db,
                messias_user_id=messias_user.id,
                action="chat.messias.view_as_user.ended",
                target_user_id=target_user_id
            )
            db.commit()
            
        return target_user_id

    @staticmethod
    def get_simulated_user_id(user: User) -> Optional[int]:
        """
        Retorna o ID do usuário simulado se o MESSIAS estiver no modo visualização.
        """
        return ACTIVE_SIMULATIONS.get(user.id)

    @staticmethod
    def verify_write_block(user: User):
        """
        Bloqueia operações de escrita se o usuário estiver sob simulação.
        """
        if user.id in ACTIVE_SIMULATIONS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operação negada. O modo visualização como usuário é estritamente somente leitura."
            )
            
    @staticmethod
    def get_effective_user(db: Session, user: User) -> User:
        """
        Retorna o usuário efetivo para fins de checagem de permissão (o simulado se houver).
        """
        simulated_id = ACTIVE_SIMULATIONS.get(user.id)
        if simulated_id:
            sim_user = db.query(User).filter(User.id == simulated_id).first()
            if sim_user:
                return sim_user
        return user
