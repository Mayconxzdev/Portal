import html
from typing import Optional

def sanitize_message_body(text: Optional[str]) -> Optional[str]:
    """
    Sanitiza o corpo da mensagem contra ataques XSS.
    Escapa tags HTML e remove trechos potencialmente perigosos, mantendo menções seguras.
    """
    if not text:
        return text
    
    # Escapa completamente o HTML bruto contra tags script, iframe, etc.
    escaped_text = html.escape(text)
    
    return escaped_text
