# Portal Vesper — case de produto e engenharia

## Resumo

O Portal Vesper nasceu da necessidade de organizar processos corporativos que normalmente ficam distribuídos entre planilhas, e-mails, mensagens, sistemas legados e automações isoladas.

O projeto foi concebido como uma plataforma modular capaz de conectar operações sem transformar cada módulo em um produto independente. A solução combina uma SPA em React, uma API FastAPI, PostgreSQL, eventos internos, WebSockets, automações n8n e um shell desktop em Tauri.

## Papel do desenvolvedor

**Maycon da Silva Ferreira** atuou na concepção do produto, modelagem dos módulos, desenho da arquitetura, implementação full-stack, criação do sistema visual, automações, testes e documentação.

As principais responsabilidades do projeto incluem:

- traduzir fluxos corporativos em entidades e jornadas de produto;
- definir fronteiras entre compras, estoque, aprovações, TI e execução;
- implementar APIs, serviços, permissões e migrações;
- construir a experiência web e componentes reutilizáveis;
- integrar eventos, WebSockets e workers;
- criar testes e critérios de aceitação;
- documentar limitações, riscos e decisões técnicas.

## Problema

Os fluxos observados tinham quatro características recorrentes:

1. **dados duplicados:** o mesmo fornecedor, produto ou usuário aparecia em fontes diferentes;
2. **baixa rastreabilidade:** decisões e aprovações não permaneciam ligadas ao processo de origem;
3. **regras fora do produto:** planilhas e automações externas concentravam lógica crítica;
4. **experiência fragmentada:** usuários precisavam alternar entre ferramentas e interpretar detalhes técnicos.

## Estratégia de solução

### Monólito modular

O projeto evita microserviços prematuros, mas mantém fronteiras explícitas entre domínios. Cada módulo possui rotas, serviços, schemas e modelos próprios.

### Action Intents

Solicitações feitas por chat, dashboard, Koda ou automações não executam operações sensíveis diretamente. Elas geram uma intenção estruturada, que é validada pelo módulo responsável.

### Eventos e outbox

Mudanças importantes registram eventos na mesma transação do dado de negócio. Isso permite reações assíncronas, notificações e integrações sem perder rastreabilidade.

### PostgreSQL como fonte da verdade

Planilhas, e-mails, n8n e conectores externos entram como fontes ou executores. O estado operacional permanece no banco principal.

## Fluxos representativos

### Compras

- entrada por item conhecido, descrição livre ou planilha;
- normalização e vínculo com o catálogo;
- pesquisa de ofertas e evidência por campo;
- distribuição por fornecedor e mensagens de cotação;
- ingestão de respostas, anexos e extração assistida;
- comparação, aprovação, pedido e entrega.

### Kanban

- quadros com permissões próprias;
- visualização em cards, lista e TV;
- campos personalizados, etiquetas e checklists;
- eventos de movimentação e atualização em tempo real;
- vínculo com bloqueios, materiais e responsáveis.

### TI

- ativos, inventário, certificados e manutenção;
- chamados com prioridade, SLA e atividades;
- catálogo de acessos e solicitações;
- cofre de credenciais com revelação auditada.

### Administração

- criação e ciclo de vida de usuários;
- perfis, módulos e permissões;
- acessos temporários e encerramento de sessões;
- histórico administrativo e revisão de segurança.

## Evidências técnicas

- backend organizado em domínios com SQLAlchemy e Alembic;
- frontend com páginas, componentes de domínio e biblioteca de UI própria;
- suites de testes de backend e frontend;
- CI com lint, testes e build;
- CodeQL para Python e JavaScript/TypeScript;
- templates n8n sanitizados e desativados por padrão;
- documentação de arquitetura, banco, segurança, integrações e UX.

## Trade-offs

### Por que não microserviços?

O domínio é amplo, mas o contexto operacional ainda evolui. Um monólito modular permite refatorar fronteiras sem multiplicar deploys, observabilidade e consistência distribuída.

### Por que CSS próprio?

A interface exige alta densidade de informação e identidade visual consistente. Design tokens e componentes próprios mantêm controle sobre layout, acessibilidade e modo TV.

### Por que n8n não escreve no banco?

Workflows mudam com frequência e têm credenciais externas. Restringi-los às APIs oficiais mantém permissão, validação e auditoria dentro do produto.

### Por que publicar limitações?

O projeto é amplo e nem todos os módulos têm a mesma maturidade. A transparência evita confundir protótipos, integrações condicionais e fluxos validados com uma implantação de produção.

## Próximos passos

- consolidar a experiência de Propostas e Knowledge;
- ampliar evidências E2E de compras e integrações;
- completar observabilidade e métricas operacionais;
- reduzir pontos legados e consolidar padrões de erro;
- preparar uma demo hospedada com dados totalmente sintéticos;
- aumentar cobertura de testes nos fluxos críticos de sincronização e permissão.
