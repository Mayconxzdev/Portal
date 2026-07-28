import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.it import ITCredential
from app.models.purchase import PurchaseSenderAccount
from app.models.user import User
from app.modules.it.credentials import encrypt_secret

def bootstrap_config():
    db = SessionLocal()
    try:
        # 1. Encontra um usuário administrador ou do sistema para ser o autor
        user = db.query(User).filter(User.is_active == True).first()
        if not user:
            print("ERRO: Nenhum usuário ativo encontrado no banco de dados para associar às credenciais.")
            sys.exit(1)
            
        print(f"Usando usuário: {user.username} (ID: {user.id}) para criar/atualizar credenciais.")
        
        # 2. Definição dos segredos que a especificação exige
        secrets_to_bootstrap = [
            {
                "title": "Chave SerpApi de Compras Inteligentes",
                "system_name": "purchases/serpapi/api-key",
                "username": "serpapi",
                "secret": "b342cecd0158da7d5de19e489b10da020220f7a8",
                "notes": "Chave SerpApi de teste autorizada corporativa para Compras Inteligentes."
            },
            {
                "title": "Senha SMTP Compras Vesper",
                "system_name": "purchases/smtp/vesper",
                "username": "compras@portal.example",
                "secret": "Vpcompras5",
                "notes": "Senha de e-mail SMTP Vesper para envio de cotações automáticas."
            },
            {
                "title": "Senha SMTP Compras Empresa Parceira",
                "system_name": "purchases/smtp/ventrio",
                "username": "compras@empresa-parceira.example",
                "secret": "Vpcompras5",
                "notes": "Senha de e-mail SMTP Ventrio para envio de cotações automáticas."
            }
        ]
        
        # 3. Processamento e inserção idempotente
        for item in secrets_to_bootstrap:
            existing = db.query(ITCredential).filter(
                ITCredential.system_name == item["system_name"]
            ).first()
            
            secret_enc = encrypt_secret(item["secret"])
            
            if existing:
                existing.title = item["title"]
                existing.username = item["username"]
                existing.secret_encrypted = secret_enc
                existing.notes = item["notes"]
                existing.updated_by_user_id = user.id
                existing.is_active = True
                print(f"SEGREDOS: Credencial '{item['system_name']}' atualizada com sucesso no Cofre.")
            else:
                new_cred = ITCredential(
                    title=item["title"],
                    system_name=item["system_name"],
                    username=item["username"],
                    secret_encrypted=secret_enc,
                    notes=item["notes"],
                    visibility_level="IT_MANAGER",
                    is_active=True,
                    created_by_user_id=user.id
                )
                db.add(new_cred)
                print(f"SEGREDOS: Credencial '{item['system_name']}' criada com sucesso no Cofre.")
        
        # 4. Atualiza as contas remetentes para configuradas
        db.query(PurchaseSenderAccount).filter(
            PurchaseSenderAccount.email == "compras@portal.example"
        ).update({
            PurchaseSenderAccount.status: "configured",
            PurchaseSenderAccount.has_secret: True
        })
        
        db.query(PurchaseSenderAccount).filter(
            PurchaseSenderAccount.email == "compras@empresa-parceira.example"
        ).update({
            PurchaseSenderAccount.status: "configured",
            PurchaseSenderAccount.has_secret: True
        })
                
        db.commit()
        print("BOOTSTRAP: Credenciais de Compras Inteligentes configuradas com sucesso de forma segura!")
        
    except Exception as e:
        db.rollback()
        print(f"ERRO durante o bootstrap: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    bootstrap_config()
