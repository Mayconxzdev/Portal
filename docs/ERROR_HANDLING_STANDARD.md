# Padrão Global de Tratamento de Erros

## 1. Objetivo

Nenhum usuário deve receber:

- `[object Object]`;
- traceback;
- erro SQL;
- objeto Pydantic cru;
- JSON de API;
- código interno sem explicação;
- mensagem fora do modal ou drawer de origem.

## 2. Contrato recomendado

```json
{
  "code": "USER_ALREADY_EXISTS",
  "message": "Este nome de usuário já está cadastrado.",
  "field_errors": {
    "username": "Escolha outro nome."
  },
  "request_id": "correlation-id"
}
```

Campos técnicos adicionais podem existir nos logs, não na interface comum.

## 3. Backend

O backend deve:

- normalizar `RequestValidationError`;
- traduzir conflito de unicidade;
- distinguir 401, 403, 404, 409, 422 e 500;
- usar códigos estáveis;
- não expor exception interna;
- registrar `request_id`;
- retornar erro por campo quando possível;
- preservar detalhes técnicos apenas no log seguro.

## 4. Frontend

Todos os clientes devem usar uma função compartilhada, como `humanizeApiError`.

Ela deve tratar:

- string;
- objeto;
- lista do Pydantic;
- `detail`;
- `message`;
- `field_errors`;
- erro de rede;
- timeout;
- sessão expirada;
- sem permissão;
- conflito;
- validação;
- erro inesperado.

## 5. Local do erro

- formulário em modal: erro no modal;
- drawer: erro no drawer;
- campo: erro abaixo do campo;
- operação global: banner ou toast;
- falha fatal: Error Boundary.

Nunca obrigar o usuário a fechar a interface para descobrir o erro.

## 6. Preservação

Em erro:

- modal não fecha;
- dados digitados permanecem;
- etapa permanece;
- campos com problema são destacados;
- foco vai para o primeiro erro;
- alterações não são descartadas.

## 7. Mensagens

Boas:

- “Este nome de usuário já está cadastrado.”
- “Você não tem permissão para alterar este usuário.”
- “Não foi possível conectar à conta. Confira as configurações.”
- “A planilha foi lida, mas 12 itens precisam de revisão.”

Ruins:

- “Erro 422.”
- “IntegrityError.”
- “[object Object].”
- “Falha desconhecida” sem próxima ação.

## 8. Alertas nativos

`alert()` não deve ser usado como padrão de produto. Substituir por componentes consistentes de confirmação, erro e sucesso.

## 9. Testes

Todo fluxo mutável deve testar:

- sucesso;
- campo ausente;
- conflito;
- sem permissão;
- erro do servidor;
- rede;
- preservação dos dados;
- mensagem humana;
- ausência de `[object Object]`;
- erro dentro do contexto correto.
