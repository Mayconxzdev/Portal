# Contribuindo

Obrigado pelo interesse no Portal Vesper.

## Antes de começar

- leia [`AGENTS.md`](AGENTS.md);
- consulte o documento do módulo afetado;
- confirme o estado em [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md);
- não use dados, credenciais ou arquivos reais.

## Ambiente

```bash
cp .env.example .env
./scripts/dev.sh
```

No Windows, use `INICIAR_PORTAL.bat`.

## Padrão de mudança

1. descreva o problema de usuário ou engenharia;
2. mantenha a alteração pequena e focada;
3. valide permissões no backend;
4. preserve compatibilidade de API quando possível;
5. inclua migration para mudanças persistentes;
6. atualize testes e documentação;
7. não introduza dependência sem justificativa.

## Validação

```bash
./scripts/check.sh
```

Ou execute separadamente:

```bash
cd backend
ruff check app tests
ENVIRONMENT=testing PYTHONPATH=. pytest -q

cd ../apps/web
npm run lint
npm run test:run
npm run build
```

## Pull requests

A descrição deve conter:

- contexto;
- arquivos e fluxos alterados;
- testes executados;
- riscos e limitações;
- screenshots quando houver mudança visual;
- plano de rollback quando houver migration ou integração.

## Segurança

Não publique vulnerabilidades, credenciais ou dados pessoais em issues. Consulte [`SECURITY.md`](SECURITY.md).
