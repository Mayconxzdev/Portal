# Decisões arquiteturais

Este documento resume as decisões que mais ajudam a compreender o raciocínio técnico do Portal Vesper.

## ADR-001 — Monólito modular

**Decisão:** manter uma aplicação backend única com domínios separados.

**Contexto:** o produto possui muitos módulos, porém suas fronteiras ainda evoluem e compartilham autenticação, pessoas, arquivos, eventos e auditoria.

**Consequências:**

- transações e desenvolvimento local mais simples;
- menos custo operacional;
- necessidade de disciplina para impedir acoplamento entre módulos;
- possibilidade de extrair serviços apenas quando houver evidência real.

## ADR-002 — PostgreSQL como fonte da verdade

**Decisão:** integrações, planilhas e n8n não mantêm o estado oficial do processo.

**Consequências:**

- entidades centrais podem ser reutilizadas;
- eventos e auditoria ficam vinculados ao dado operacional;
- importadores precisam ser idempotentes e preservar a origem.

## ADR-003 — Action Intent antes de ação sensível

**Decisão:** chat, IA, dashboard e automações criam intenções, não comandos diretos.

**Consequências:**

- preview e confirmação ficam explícitos;
- o módulo de destino continua responsável pela autorização;
- a mesma regra funciona para UI, Koda e n8n.

## ADR-004 — Transactional outbox

**Decisão:** eventos relevantes são persistidos na mesma transação da alteração de estado.

**Consequências:**

- reduz risco de alteração sem evento correspondente;
- exige dispatcher, retry e idempotência;
- permite WebSockets, notificações e integrações assíncronas.

## ADR-005 — n8n como executor externo

**Decisão:** workflows chamam APIs autenticadas e não escrevem diretamente no PostgreSQL.

**Consequências:**

- regras e permissões permanecem no Portal;
- workflows podem evoluir sem duplicar o domínio;
- callbacks precisam de assinatura, timestamp e proteção contra replay.

## ADR-006 — Cofre com criptografia autenticada

**Decisão:** segredos de TI são cifrados com Fernet e revelados somente sob permissão.

**Consequências:**

- a chave precisa ficar fora do banco;
- desenvolvimento pode derivar uma chave local, mas produção não;
- toda revelação deve gerar atividade de auditoria.

## ADR-007 — Design tokens e CSS próprio

**Decisão:** construir a interface sobre tokens e componentes internos.

**Consequências:**

- consistência entre módulos e temas;
- controle sobre alta densidade de dados;
- maior responsabilidade sobre acessibilidade e manutenção dos componentes.

## ADR-008 — Templates públicos sem credenciais

**Decisão:** exports do n8n são versionados desativados, sem IDs de instância, webhooks persistidos ou referências de credenciais.

**Consequências:**

- o repositório pode ser público com menor risco;
- quem importar precisa configurar credenciais e revisar cada workflow;
- templates não devem ser ativados diretamente em produção.
