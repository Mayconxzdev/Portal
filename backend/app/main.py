import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import engine, Base
from app.api.router import api_router

# Configura logs estruturados
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Garante a criação de tabelas básicas no banco de dados na inicialização
    como um fallback de segurança caso as migrações do Alembic ainda não tenham rodado.
    """
    try:
        Base.metadata.create_all(bind=engine)
        
        # Semeia as regras de reacao iniciais no startup
        from app.core.database import SessionLocal
        from app.modules.reactions.service import seed_initial_reaction_rules
        db = SessionLocal()
        try:
            seed_initial_reaction_rules(db)
        finally:
            db.close()
        # Registra o callback de notificações em tempo real para aprovações
        from app.modules.approvals.service import register_ws_callback
        from app.core.ws import ws_approval_callback
        register_ws_callback(ws_approval_callback)
        print("[WS] Callback WebSocket de aprovacoes registrado com sucesso!")
        
        # Salva o loop principal para o websocket do chat
        import asyncio
        from app.modules.chat.events import chat_ws_manager
        chat_ws_manager.loop = asyncio.get_running_loop()
        print(f"[WS] Event loop principal do chat registrado com sucesso: {chat_ws_manager.loop}")
        
        # Inicializa o scheduler do event dispatcher
        from app.core.events import start_event_dispatcher_scheduler
        await start_event_dispatcher_scheduler()
    except Exception as e:
        print(f"Erro ao inicializar tabelas em tempo de startup: {str(e)}")
    yield
    # Shutdown do scheduler do event dispatcher
    try:
        from app.core.events import stop_event_dispatcher_scheduler
        await stop_event_dispatcher_scheduler()
    except Exception as e:
        print(f"Erro ao finalizar o loop do scheduler: {str(e)}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend oficial de serviços e APIs do Portal Vesper",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    if not settings.SECURITY_HEADERS_ENABLED:
        return response

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    if request.url.path not in {"/docs", "/redoc", "/openapi.json"}:
        response.headers.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)

    if settings.COOKIE_SECURE:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    return response

# Configuração de CORS (Cross-Origin Resource Sharing)
# Permite que o frontend local (normalmente rodando em localhost:5173 ou 3000) se conecte à API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rota de healthcheck básica (requisito obrigatório)
@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

# Monta o agregador de rotas oficiais v1
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    # Roda o servidor local de desenvolvimento na porta 8000
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )
