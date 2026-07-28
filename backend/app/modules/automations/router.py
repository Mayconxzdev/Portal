from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_automations_status():
    """
    Retorna os fluxos ativos de automação vinculados ao n8n (Placeholder de desenvolvimento).
    """
    return {
        "status": "success",
        "module": "automations",
        "workflows": [
            {"id": "wf_1", "name": "Alerta de Compra Alta", "engine": "n8n", "active": True},
            {"id": "wf_2", "name": "Sincronização de Estoque MinIO", "engine": "n8n", "active": False}
        ]
    }
