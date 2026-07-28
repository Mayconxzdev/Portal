# Templates n8n

Os arquivos em `workflows/` são **templates públicos e sanitizados**. Eles foram exportados sem credenciais, IDs de instância, dados estáticos, pin data ou webhooks persistidos.

## Regras de uso

1. importe o workflow em uma instância de desenvolvimento;
2. revise todos os nós antes de ativar;
3. configure credenciais por meio do gerenciador do n8n;
4. substitua URLs e segredos por variáveis de ambiente;
5. valide os callbacks e permissões do Portal;
6. execute primeiro em modo de teste;
7. nunca permita escrita direta no PostgreSQL.

## Pastas

- `core/` — gateway, aprovações, observabilidade e tratamento de falhas;
- `ai/` — agentes especializados e roteamento assistido;
- `legacy/` — referências históricas mantidas para comparação e migração.

## Importante

Todos os workflows são publicados com `active: false`. A presença de um template não significa que a integração esteja homologada ou pronta para produção.
