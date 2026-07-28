import os
import sys
import argparse
import requests
import logging
import subprocess

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("vesper.legacy_importer")

class PortalLegacyClient:
    """
    Cliente de API do Portal Vesper para interagir com os endpoints de staging legado.
    """
    def __init__(self, base_url: str, username: str = "admin", password: str = "portal-dev-only"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.headers = {}

    def login(self) -> bool:
        """
        Realiza a autenticação no Portal Vesper para obter o token Bearer.
        """
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        try:
            logger.info(f"Tentando autenticar em {url} com usuario: {self.username}...")
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                self.token = data.get("access_token")
                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                logger.info("Autenticado com sucesso no Portal Vesper.")
                return True
            else:
                logger.error(f"Falha na autenticacao (Status {res.status_code}): {res.text}")
                return False
        except Exception as e:
            logger.error(f"Erro de conexao ao tentar autenticar no Portal: {e}")
            return False

    def create_batch(self, source_app: str, source_name: str, source_path_masked: str, module_target: str, notes: str = None) -> str:
        """
        Cria um lote de importação (Batch) e retorna o batch_id (UUID).
        """
        url = f"{self.base_url}/api/v1/legacy-import/batches"
        payload = {
            "source_app": source_app,
            "source_name": source_name,
            "source_path_masked": source_path_masked,
            "module_target": module_target,
            "notes": notes
        }
        res = requests.post(url, json=payload, headers=self.headers, timeout=10)
        res.raise_for_status()
        batch = res.json()
        logger.info(f"Lote criado com sucesso. ID: {batch['id']} | Status: {batch['status']}")
        return batch["id"]

    def upload_rows(self, batch_id: str, rows: list) -> int:
        """
        Envia em lote as linhas de staging para um Batch específico.
        """
        url = f"{self.base_url}/api/v1/legacy-import/batches/{batch_id}/rows"
        # Organiza no schema LegacyImportRowBulkCreate
        payload = {"rows": rows}
        res = requests.post(url, json=payload, headers=self.headers, timeout=30)
        res.raise_for_status()
        uploaded_count = len(res.json())
        logger.info(f"Enviadas {uploaded_count} linhas para o lote {batch_id}.")
        return uploaded_count


def run_compras(client: PortalLegacyClient, dry_run: bool):
    try:
        from legacy_import_compras import import_compras
        import_compras(client, dry_run)
    except ImportError as e:
        logger.error(f"Erro ao importar adaptador compras: {e}")

def run_helpdesk(client: PortalLegacyClient, dry_run: bool):
    try:
        from legacy_import_helpdesk import import_helpdesk
        import_helpdesk(client, dry_run)
    except ImportError as e:
        logger.error(f"Erro ao importar adaptador helpdesk: {e}")

def run_producao(client: PortalLegacyClient, dry_run: bool):
    try:
        from legacy_import_producao import import_producao
        import_producao(client, dry_run)
    except ImportError as e:
        logger.error(f"Erro ao importar adaptador producao: {e}")

def run_projeto(client: PortalLegacyClient, dry_run: bool):
    try:
        from legacy_import_projeto import import_projeto
        import_projeto(client, dry_run)
    except ImportError as e:
        logger.error(f"Erro ao importar adaptador projeto: {e}")

def run_propostas(client: PortalLegacyClient, dry_run: bool):
    try:
        from legacy_import_propostas import import_propostas
        import_propostas(client, dry_run)
    except ImportError as e:
        logger.error(f"Erro ao importar adaptador propostas: {e}")

def run_ti_routines(client: PortalLegacyClient, dry_run: bool):
    try:
        from legacy_import_ti_routines import import_ti_routines
        import_ti_routines(client, dry_run)
    except ImportError as e:
        logger.error(f"Erro ao importar adaptador ti_routines: {e}")


def main():
    parser = argparse.ArgumentParser(description="Orquestrador CLI de importacao de dados dos sistemas legados.")
    parser.add_argument("--app", choices=["compras", "helpdesk", "producao", "projeto", "propostas", "ti_routines", "all"], default="all",
                        help="Sistema legado especifico a ser importado ou 'all' para todos.")
    parser.add_argument("--url", default=os.getenv("PORTAL_API_URL", "http://localhost:8000"),
                        help="URL base da API do Portal Vesper.")
    parser.add_argument("--user", default=os.getenv("PORTAL_ADMIN_USER", "admin"),
                        help="Usuario administrador/gerente do Portal.")
    parser.add_argument("--password", default=os.getenv("PORTAL_ADMIN_PASSWORD", "portal-dev-only"),
                        help="Senha do administrador/gerente do Portal.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Se marcado, apenas extrai e imprime os dados localmente, sem enviar para a API.")
    parser.add_argument("--real-run", action="store_true",
                        help="Executa go-live local seguro e idempotente usando os services/modelos do backend.")

    args = parser.parse_args()

    if args.real_run:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy_go_live_operational.py")
        logger.info("===== MODO REAL-RUN LOCAL ATIVADO. Usando ativador operacional idempotente =====")
        subprocess.run([sys.executable, script_path, "--execute"], check=True)
        return

    # Adiciona a pasta do script ao path para permitir imports locais dos adaptadores
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)

    client = None
    if not args.dry_run:
        client = PortalLegacyClient(args.url, args.user, args.password)
        if not client.login():
            logger.error("Falha ao inicializar o cliente. Cancelando execucao.")
            sys.exit(1)
    else:
        logger.info("===== MODO DRY-RUN ATIVADO. Nenhum dado sera enviado para a API do Portal =====")

    apps_to_run = []
    if args.app == "all":
        apps_to_run = ["compras", "helpdesk", "producao", "projeto", "propostas", "ti_routines"]
    else:
        apps_to_run = [args.app]

    for app in apps_to_run:
        logger.info(f"--- Iniciando importacao do aplicativo legado: {app.upper()} ---")
        if app == "compras":
            run_compras(client, args.dry_run)
        elif app == "helpdesk":
            run_helpdesk(client, args.dry_run)
        elif app == "producao":
            run_producao(client, args.dry_run)
        elif app == "projeto":
            run_projeto(client, args.dry_run)
        elif app == "propostas":
            run_propostas(client, args.dry_run)
        elif app == "ti_routines":
            run_ti_routines(client, args.dry_run)
        logger.info(f"--- Fim da importacao de: {app.upper()} ---\n")

    logger.info("Processo de importacao legado concluido.")

if __name__ == "__main__":
    main()
