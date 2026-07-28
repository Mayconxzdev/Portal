import logging
import sys

def setup_logging() -> None:
    """
    Configura o sistema de logs padrão do Python para exibir mensagens formatadas
    de forma clara no console do servidor.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Desativa ruídos excessivos de bibliotecas de terceiros
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
