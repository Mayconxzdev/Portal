import os
import sys
import re
import socket
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import requests

# Exceção personalizada para credenciais ausentes
class CredentialsMissingException(Exception):
    def __init__(self, provider_name: str, missing_keys: List[str]):
        self.provider_name = provider_name
        self.missing_keys = missing_keys
        keys_str = ", ".join(missing_keys)
        super().__init__(f"Credenciais ausentes para o provedor '{provider_name}': {keys_str}")


# ---------------------------------------------------------------------------
# Validador de Segurança de URLs (Mitigação de SSRF)
# ---------------------------------------------------------------------------
def is_safe_url(url: str, allowed_schemes: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Valida se a URL é segura para requisições no servidor.
    Mitiga ataques de SSRF resolvendo o host e bloqueando IPs de redes privadas e locais.
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, "URL malformada."

    if parsed.scheme not in allowed_schemes:
        return False, f"Esquema '{parsed.scheme}' não permitido. Use apenas http ou https."

    if not parsed.netloc:
        return False, "Host ausente na URL."

    # Remove credenciais da URL para evitar vazamento
    if parsed.username or parsed.password:
        return False, "URLs contendo credenciais (usuário/senha) não são permitidas."

    host = parsed.hostname
    if not host:
        return False, "Host inválido."

    # Evita localhost/loopback direto por nome
    host_lower = host.lower()
    if host_lower in ["localhost", "127.0.0.1", "::1", "0.0.0.0"]:
        return False, "Acesso a endereços locais (localhost) é bloqueado por segurança."

    # Resolução de DNS
    try:
        ip_addresses = socket.getaddrinfo(host, parsed.port or (80 if parsed.scheme == "http" else 443))
    except socket.gaierror:
        return False, f"Não foi possível resolver o domínio '{host}'."

    # Verifica cada IP retornado
    for family, _, _, _, sockaddr in ip_addresses:
        ip = sockaddr[0]
        # Mitiga SSRF contra faixas de IP privado e local
        if is_private_ip(ip):
            return False, f"Acesso ao IP privado/local '{ip}' é bloqueado por segurança."

    return True, url


def is_private_ip(ip: str) -> bool:
    """
    Retorna True se o IP pertence a faixas privadas, de loopback ou reservadas.
    """
    # IPv4 loopback
    if ip.startswith("127."):
        return True
    # IPv4 privado Classe A
    if ip.startswith("10."):
        return True
    # IPv4 privado Classe B (172.16.0.0 - 172.31.255.255)
    if ip.startswith("172."):
        parts = ip.split(".")
        if len(parts) >= 2:
            try:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return True
            except ValueError:
                pass
    # IPv4 privado Classe C
    if ip.startswith("192.168."):
        return True
    # IPv4 Link-local e AWS Metadata
    if ip.startswith("169.254."):
        return True
    # IPv6 loopback
    if ip == "::1" or ip == "0:0:0:0:0:0:0:1":
        return True
    # Outros reservados / não-roteáveis
    if ip == "0.0.0.0" or ip == "::":
        return True
    
    return False


def safe_fetch_html(url: str, timeout_seconds: int = 10, max_bytes: int = 2 * 1024 * 1024) -> str:
    """
    Busca o HTML de um link de forma segura aplicando limites de redirecionamento,
    segurança de URL contra SSRF e limite de tamanho de payload (max_bytes = 2MB).
    """
    is_safe, msg = is_safe_url(url)
    if not is_safe:
        raise ValueError(msg)

    # Faz a requisição com stream habilitado para controlar o tamanho máximo do payload
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    # Executamos requisição manual para rastrear redirecionamentos e re-validar contra SSRF em cada passo
    current_url = url
    max_redirects = 3
    redirect_count = 0

    while redirect_count <= max_redirects:
        response = requests.get(current_url, headers=headers, timeout=timeout_seconds, stream=True, allow_redirects=False)
        
        # Se for redirect (301, 302, 303, 307, 308)
        if response.status_code in [301, 302, 303, 307, 308]:
            redirect_url = response.headers.get("Location")
            if not redirect_url:
                break
            # Resolve URL relativa se necessário
            redirect_url = urllib.parse.urljoin(current_url, redirect_url)
            
            # Valida segurança da nova URL
            is_safe, msg = is_safe_url(redirect_url)
            if not is_safe:
                raise ValueError(f"Redirecionamento bloqueado: {msg}")
            
            current_url = redirect_url
            redirect_count += 1
            continue
        
        # Não é redirect, valida status
        response.raise_for_status()
        
        # Lê a resposta limitando o tamanho
        content_bytes = bytearray()
        for chunk in response.iter_content(chunk_size=4096):
            content_bytes.extend(chunk)
            if len(content_bytes) > max_bytes:
                raise ValueError(f"O tamanho da resposta excedeu o limite máximo permitido de {max_bytes / (1024*1024):.1f}MB.")
        
        # Converte para string usando encoding detectado ou utf-8
        encoding = response.encoding or "utf-8"
        try:
            return content_bytes.decode(encoding, errors="ignore")
        except Exception:
            return content_bytes.decode("utf-8", errors="ignore")

    raise ValueError("Número máximo de redirecionamentos excedido.")


# ---------------------------------------------------------------------------
# Interface Abstrata de Provedor de Pesquisa de Produtos
# ---------------------------------------------------------------------------
class ExternalProductSearchProvider(ABC):
    
    @abstractmethod
    def search_products(self, query: str, constraints: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Pesquisa produtos no provedor externo correspondente.
        Retorna uma lista de opções de produto normalizadas.
        """
        pass

    @abstractmethod
    def fetch_product_url(self, url: str) -> Dict[str, Any]:
        """
        Extrai metadados estruturados de um link direto de produto.
        """
        pass

    @abstractmethod
    def import_cart(self, url_or_text: str) -> List[Dict[str, Any]]:
        """
        Importa itens de um carrinho público ou analisa texto de carrinho privado.
        """
        pass

    @abstractmethod
    def normalize_result(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza os dados retornados para o formato esperado pelo domínio do Portal Vesper.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verifica se o provedor está configurado e funcional.
        """
        pass


# ---------------------------------------------------------------------------
# Provedor Real: SerpApi (Google Shopping)
# ---------------------------------------------------------------------------
class SerpApiProductSearchProvider(ExternalProductSearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SERPAPI_API_KEY")

    def _require_api_key(self):
        if not self.api_key:
            raise CredentialsMissingException("SerpApi (Google Shopping)", ["SERPAPI_API_KEY"])

    def search_products(self, query: str, constraints: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._require_api_key()
        
        # Configura os parâmetros de busca no Google Shopping
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "hl": "pt",
            "gl": "br"
        }
        
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=12)
            response.raise_for_status()
            data = response.json()
            
            shopping_results = data.get("shopping_results", [])
            normalized = []
            for item in shopping_results[:6]:  # Pega as 6 melhores opções
                normalized.append(self.normalize_result(item))
            return normalized
        except CredentialsMissingException:
            raise
        except Exception as e:
            # Em caso de falha de conexão ou HTTP, repassa ou lança erro amigável
            raise RuntimeError(f"Falha na busca externa via SerpApi: {str(e)}")

    def fetch_product_url(self, url: str) -> Dict[str, Any]:
        """
        Faz raspagem de metadados do HTML de forma segura contra SSRF.
        """
        try:
            html = safe_fetch_html(url)
            
            # Extrai título usando regex simples do HTML
            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Produto Externo"
            
            # Tenta extrair tags OpenGraph para imagem e preço
            og_title_match = re.search(r'property="og:title"\s+content="(.*?)"', html, re.IGNORECASE) or \
                             re.search(r'content="(.*?)"\s+property="og:title"', html, re.IGNORECASE)
            og_image_match = re.search(r'property="og:image"\s+content="(.*?)"', html, re.IGNORECASE) or \
                             re.search(r'content="(.*?)"\s+property="og:image"', html, re.IGNORECASE)
            og_price_match = re.search(r'property="product:price:amount"\s+content="(.*?)"', html, re.IGNORECASE) or \
                             re.search(r'content="(.*?)"\s+property="product:price:amount"', html, re.IGNORECASE)
            
            if og_title_match:
                title = og_title_match.group(1).strip()
            
            image_url = og_image_match.group(1).strip() if og_image_match else None
            price = 0.0
            if og_price_match:
                try:
                    price = float(og_price_match.group(1).replace(",", "."))
                except Exception:
                    pass
            else:
                # Tenta achar preços comuns no HTML (heurística simples)
                price_match = re.search(r"R\$\s*(\d+(?:[.,]\d+)?)", html, re.IGNORECASE)
                if price_match:
                    try:
                        price = float(price_match.group(1).replace(".", "").replace(",", "."))
                    except Exception:
                        pass

            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc.replace("www.", "").lower()

            return {
                "source_type": "MANUAL_LINK",
                "store_name": domain.split(".")[0].capitalize(),
                "seller_name": domain,
                "title": title,
                "unit_price": price,
                "shipping_price": 0.0,
                "total_price": price,
                "product_url": url,
                "image_url": image_url,
                "availability": True,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "raw_source_metadata": {"parsed_via": "og-tags"}
            }
        except Exception as e:
            raise RuntimeError(f"Erro ao extrair metadados estruturados do link: {str(e)}")

    def import_cart(self, url_or_text: str) -> List[Dict[str, Any]]:
        self._require_api_key()
        # Se for link, tenta analisar como link. Se for texto colado, faz o parse do texto.
        if url_or_text.startswith("http://") or url_or_text.startswith("https://"):
            html = safe_fetch_html(url_or_text)
            # Exemplo de parser de carrinho público (heurística simples)
            # Para fins práticos, se o link for público extrai do HTML ou retorna erro de carrinho privado
            if "cart" in url_or_text.lower() or "carrinho" in url_or_text.lower():
                # Tenta achar padrões comuns de lista de itens
                return []
            raise ValueError("O link informado não parece ser um carrinho público válido.")
        else:
            # Caso seja texto colado de carrinho privado
            return self._parse_cart_text(url_or_text)

    def _parse_cart_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Lê um bloco de texto copiado de um carrinho privado (ex: Mercado Livre, Amazon)
        e extrai nome, preço e quantidade dos itens.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        items = []
        # Heurística para agrupar nome do produto e preço consecutivo
        current_title = None
        for line in lines:
            # Se for linha de preço (ex: R$ 120,00 ou 120.00)
            price_match = re.search(r"(?:R\$\s*)?(\d+(?:[.,]\d{2}))", line)
            if price_match and current_title:
                try:
                    price = float(price_match.group(1).replace(".", "").replace(",", "."))
                    items.append({
                        "source_type": "CART_IMPORT",
                        "title": current_title,
                        "unit_price": price,
                        "shipping_price": 0.0,
                        "total_price": price,
                        "availability": True,
                        "captured_at": datetime.now(timezone.utc).isoformat()
                    })
                    current_title = None
                except Exception:
                    pass
            elif len(line) > 5 and not price_match:
                # Linha de texto comum representa o título do produto
                current_title = line

        return items

    def normalize_result(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        price_str = str(raw_item.get("price", "0")).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            price = float(re.sub(r"[^\d.]", "", price_str))
        except ValueError:
            price = 0.0

        shipping_str = str(raw_item.get("delivery", "0")).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            shipping = float(re.sub(r"[^\d.]", "", shipping_str))
        except ValueError:
            shipping = 0.0

        return {
            "source_type": "EXTERNAL_MARKET",
            "store_name": raw_item.get("source", "Loja Externa"),
            "seller_name": raw_item.get("merchant", raw_item.get("source", "Vendedor Externo")),
            "title": raw_item.get("title", "Produto sem título"),
            "brand": raw_item.get("brand"),
            "model": raw_item.get("model"),
            "image_url": raw_item.get("thumbnail"),
            "product_url": raw_item.get("link"),
            "unit_price": price,
            "shipping_price": shipping,
            "total_price": price + shipping,
            "delivery_estimate": raw_item.get("delivery", "Entrega padrão"),
            "availability": True,
            "rating": float(raw_item.get("rating", 0.0)) or None,
            "review_count": int(raw_item.get("reviews", 0)) or None,
            "specifications": raw_item.get("snippet"),
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "raw_source_metadata": raw_item
        }

    def health_check(self) -> bool:
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# Provedor de Mock: Usado para testes locais e fallback de desenvolvimento
# ---------------------------------------------------------------------------
class MockProductSearchProvider(ExternalProductSearchProvider):
    def search_products(self, query: str, constraints: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        # Retorna produtos simulados realistas com base na busca
        clean_q = query.lower()
        
        # Mocks para itens de exemplo comuns
        if "memoria" in clean_q or "ram" in clean_q or "ddr" in clean_q:
            return [
                {
                    "source_type": "EXTERNAL_MARKET",
                    "store_name": "TerabyteShop",
                    "seller_name": "TerabyteShop",
                    "title": "Memória Kingston Fury Beast 8GB DDR4 3200MHz",
                    "brand": "Kingston",
                    "model": "Fury Beast 8GB",
                    "image_url": "https://images.kabum.com.br/produtos/fotos/193918/memoria-kingston-fury-beast-8gb-3200mhz-ddr4-cl16-preto-kf432c16bb-8_1632743818_g.jpg",
                    "product_url": "https://www.terabyteshop.com.br/produto/12345/memoria-kingston-fury-8gb-ddr4",
                    "unit_price": 112.90,
                    "shipping_price": 0.0,
                    "total_price": 112.90,
                    "delivery_estimate": "2 a 3 dias úteis (Sul e SP)",
                    "availability": True,
                    "rating": 4.8,
                    "review_count": 1234,
                    "specifications": "Frequência 3200MHz, DDR4, CL16, cor preto",
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "raw_source_metadata": {"mocked": True}
                },
                {
                    "source_type": "EXTERNAL_MARKET",
                    "store_name": "Kabum!",
                    "seller_name": "Kabum!",
                    "title": "Memória Crucial 8GB DDR4 2666MHz CL19",
                    "brand": "Crucial",
                    "model": "Crucial 8GB",
                    "image_url": "https://images.kabum.com.br/produtos/fotos/102558/memoria-crucial-8gb-2666mhz-ddr4-cl19-ct8g4dfra266_1600783307_g.jpg",
                    "product_url": "https://www.kabum.com.br/produto/102558/memoria-crucial-8gb-2666mhz-ddr4",
                    "unit_price": 119.90,
                    "shipping_price": 12.90,
                    "total_price": 132.80,
                    "delivery_estimate": "3 a 5 dias úteis (Sul e SP)",
                    "availability": True,
                    "rating": 4.7,
                    "review_count": 3456,
                    "specifications": "Frequência 2666MHz, DDR4, CL19, cor verde/padrão",
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "raw_source_metadata": {"mocked": True}
                },
                {
                    "source_type": "EXTERNAL_MARKET",
                    "store_name": "Pichau",
                    "seller_name": "Pichau",
                    "title": "Memória HyperX DDR4 8GB 3200MHz CL16",
                    "brand": "HyperX",
                    "model": "HyperX 8GB",
                    "image_url": "",
                    "product_url": "https://www.pichau.com.br/produto/hyperx-8gb-ddr4",
                    "unit_price": 124.90,
                    "shipping_price": 15.90,
                    "total_price": 140.80,
                    "delivery_estimate": "4 a 6 dias úteis",
                    "availability": True,
                    "rating": 4.6,
                    "review_count": 987,
                    "specifications": "Frequência 3200MHz, DDR4, CL16, com dissipador de calor",
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "raw_source_metadata": {"mocked": True}
                }
            ]
            
        # Mock padrão genérico
        return [
            {
                "source_type": "EXTERNAL_MARKET",
                "store_name": "Loja Mock A",
                "seller_name": "Loja Mock A",
                "title": f"{query.capitalize()} - Opção Premium",
                "brand": "BrandMock",
                "model": "ModelPremium",
                "image_url": "",
                "product_url": "https://example.com/premium-item",
                "unit_price": 150.00,
                "shipping_price": 15.00,
                "total_price": 165.00,
                "delivery_estimate": "3 a 5 dias",
                "availability": True,
                "rating": 4.9,
                "review_count": 89,
                "specifications": f"Especificações simuladas de {query}",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "raw_source_metadata": {"mocked": True}
            },
            {
                "source_type": "EXTERNAL_MARKET",
                "store_name": "Loja Mock B (Melhor Preço)",
                "seller_name": "Loja Mock B",
                "title": f"{query.capitalize()} - Opção Econômica",
                "brand": "BrandMock",
                "model": "ModelEco",
                "image_url": "",
                "product_url": "https://example.com/eco-item",
                "unit_price": 110.00,
                "shipping_price": 20.00,
                "total_price": 130.00,
                "delivery_estimate": "6 a 8 dias",
                "availability": True,
                "rating": 4.3,
                "review_count": 412,
                "specifications": f"Opção de custo reduzido para {query}",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "raw_source_metadata": {"mocked": True}
            }
        ]

    def fetch_product_url(self, url: str) -> Dict[str, Any]:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace("www.", "").lower()
        name = domain.split(".")[0].capitalize()
        return {
            "source_type": "MANUAL_LINK",
            "store_name": name,
            "seller_name": domain,
            "title": f"Produto importado de {name}",
            "brand": "Genérico",
            "model": "Externo",
            "image_url": "",
            "product_url": url,
            "unit_price": 250.00,
            "shipping_price": 10.00,
            "total_price": 260.00,
            "delivery_estimate": "4 a 7 dias",
            "availability": True,
            "rating": 4.5,
            "review_count": 23,
            "specifications": "Extraído via simulação segura.",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "raw_source_metadata": {"mocked": True}
        }

    def import_cart(self, url_or_text: str) -> List[Dict[str, Any]]:
        if url_or_text.startswith("http://") or url_or_text.startswith("https://"):
            return [
                {
                    "source_type": "CART_IMPORT",
                    "title": "Item de Carrinho Importado A",
                    "unit_price": 199.90,
                    "shipping_price": 0.0,
                    "total_price": 199.90,
                    "availability": True,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "raw_source_metadata": {"mocked": True}
                },
                {
                    "source_type": "CART_IMPORT",
                    "title": "Item de Carrinho Importado B",
                    "unit_price": 49.90,
                    "shipping_price": 9.90,
                    "total_price": 59.80,
                    "availability": True,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "raw_source_metadata": {"mocked": True}
                }
            ]
        else:
            return [
                {
                    "source_type": "CART_IMPORT",
                    "title": "Item Copiado A",
                    "unit_price": 89.90,
                    "shipping_price": 0.0,
                    "total_price": 89.90,
                    "availability": True,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "raw_source_metadata": {"mocked": True}
                }
            ]

    def normalize_result(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        return raw_item

    def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fábrica de Provedores de Busca
# ---------------------------------------------------------------------------
def get_search_provider() -> ExternalProductSearchProvider:
    """
    Retorna o provedor de busca ativa configurado.
    Em ambiente de teste ou caso configurado explicitamente por USE_SEARCH_MOCK=true,
    retorna o MockProductSearchProvider. No runtime comum, credencial ausente deve
    aparecer como pesquisa externa nao configurada, sem inventar lojas, precos ou frete.
    """
    use_mock = os.environ.get("USE_SEARCH_MOCK", "false").lower() == "true"
    force_real = os.environ.get("PURCHASES_SEARCH_FORCE_REAL", "false").lower() == "true"
    is_pytest = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
    
    if use_mock or (is_pytest and not force_real):
        return MockProductSearchProvider()
        
    return SerpApiProductSearchProvider()
