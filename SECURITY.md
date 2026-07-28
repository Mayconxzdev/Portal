# Política de segurança

## Relato responsável

Não abra issue pública para vulnerabilidades, credenciais expostas ou dados sensíveis.

Envie o relato para **mayconxz00dev@gmail.com** com:

- descrição do problema;
- passos mínimos para reprodução;
- impacto observado;
- versão ou commit afetado;
- sugestão de mitigação, quando possível.

Evite incluir segredos reais no corpo da mensagem. Use valores redigidos e combine um canal seguro quando necessário.

## Escopo

A política cobre o código deste repositório. Infraestrutura, contas de terceiros e ambientes privados não estão incluídos sem autorização explícita.

## Compromissos do projeto

- nenhum `.env` ou upload operacional deve ser versionado;
- workflows públicos do n8n devem permanecer sem credenciais;
- permissões são validadas no backend;
- segredos do cofre são cifrados em repouso;
- callbacks externos precisam de autenticação e proteção contra replay;
- ações sensíveis devem exigir confirmação ou aprovação.

A documentação detalhada está em [`docs/SECURITY.md`](docs/SECURITY.md).
