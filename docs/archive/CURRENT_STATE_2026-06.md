# Fotografia Conhecida do Estado Atual

> **Atenção:** este arquivo não é a fonte canônica de produto. Ele resume evidências presentes nos documentos e auditorias fornecidos em 17/06/2026. Revalidar sempre contra código, banco, migrations, APIs e navegador.

## 1. Base global

Conhecido:

- tratamento compartilhado de erros foi iniciado;
- criação e edição de usuário passaram a humanizar respostas estruturadas;
- e-mail de usuário foi tornado opcional em migration local;
- dados digitados são preservados em erro no fluxo tratado;
- clientes de API de Admin, Estoque, TI e Kanban receberam parte do padrão;
- screenshots em tema claro e escuro foram gerados;
- build, lint, typecheck e testes foram relatados como verdes.

Pendente de revalidação:

- aplicar migration no ambiente correto;
- eliminar padrões antigos de erro no restante do frontend;
- remover `alert()` nativo;
- validar jornadas mutativas em navegador e banco operacional;
- revisar worktree sujo e separar mudanças.

## 2. Maturidade conhecida

| Módulo | Técnico | Funcional | Visão Vesper | Observação |
|---|---|---|---|---|
| Dashboard / Hoje | Parcial | Parcial | Parcial | Ainda precisa virar fila de ação personalizada. |
| Administração | Bom | Parcial | Parcial | Erros melhoraram; wizard, perfis sugeridos e revisão ainda precisam ser concluídos. |
| Estoque & Catálogo | Avançado | Avançado | Parcial | Melhor referência visual; validar todas as jornadas e integração Cotar Produto. |
| Compras | Avançado em partes | Parcial alto | Parcial | Agora possui sessão persistente de pesquisa, evidência por campo, recomendação e aprovação opcional por item; ainda faltam conectores reais de lojas, worker assíncrono longo, Playwright de verificação e pós-compra completo. |
| Aprovações | Base existente | Parcial | Parcial | Validar item, opção, links, aprovação técnica e financeira. |
| Propostas | Protótipo | Protótipo | Desalinhado | Falta backend, versão, envio e aceite conectado. |
| Kanban | Forte | Bom | Parcial | Quadro e TV não provam integração com proposta, estoque, compras e Koda. |
| TI | Forte | Bom | Parcial | Cofre e ativos existem; categorias, contexto e integrações precisam de validação. |
| Knowledge | Parcial | Protótipo | Parcial | Não pode ficar apenas como upload e caminho. |
| Chat / Koda | Forte no chat | Parcial | Parcial | WebSocket não prova criação de ações reais em todos os módulos. |
| Monitoramento | Incerto | Incerto | Parcial/Ausente | Há documentos de callbacks de Compras, mas a Central genérica precisa ser confirmada no código. |
| Automações | Parcial | Parcial | Parcial | Workflows antigos contêm mocks/TODOs segundo auditoria. |
| BI | Inicial/planejado | Parcial | Parcial | Precisa ser acionável e baseado em eventos confiáveis. |

## 3. Contradições encontradas nos documentos antigos

- `stock_catalog_items` aparecia como implementada e também como órfã no mesmo `DATABASE.md`;
- `task.md` indicava Estoque em andamento enquanto outras partes diziam finalizado;
- `ARCHITECTURE.md` chamava módulos de implementados sem separar técnico, funcional e Visão Vesper;
- documentos de Compras diziam PRs implementados, mas o inventário de tabelas marcava entidades equivalentes como planejadas;
- havia duas auditorias globais semelhantes;
- documentos de sprint e PR definiam comportamento permanente;
- a visão de Compras estava estreita demais em RFQ por e-mail;
- relatórios antigos não cobriam integralmente compra de mercado aberto, serviço, emergência e pós-compra.

## 4. Próxima sequência recomendada

1. separar e revisar o conjunto atual de mudanças;
2. concluir Administração guiada;
3. completar tratamento global de erros e exposição técnica;
4. validar Estoque e Cotar Produto ponta a ponta;
5. consolidar Compras + Aprovações para item conhecido e mercado aberto;
6. conectar Koda a ações reais existentes;
7. consolidar Monitoramento como camada genérica;
8. construir Propostas → Aceite → OP;
9. ligar TI e Knowledge aos fluxos;
10. criar Hoje e BI a partir de eventos confiáveis.

## 5. Organização canônica adotada

A documentação agora possui:

- referência visual separada por módulo em `assets/references/`;
- regra visual global em `VISUAL_REFERENCE_GUIDE.md`;
- mapa de dependências em `MODULE_MAP.md`;
- ordem recomendada em `IMPLEMENTATION_ORDER.md`;
- critério de não pronto dentro de cada documento de módulo.

A decisão de planejamento atual é iniciar por **Administração**, após uma estabilização global curta. Em seguida, validar Estoque e concluir a jornada Compras + Aprovações.

## Atualizacao em 22/06/2026 - Compras Inteligente

Estado tecnico apos a rodada de implementacao:

- Central de Compras consolidada como entrada principal, sem abas globais antigas no render principal.
- Nova compra usa campo universal com sugestoes, analise previa e revisao antes de persistir.
- Criacao de compra recebeu idempotencia para evitar duplicidade e falso erro de rede.
- Pesquisa por item ganhou worker Dramatiq/Redis, job persistente e estado recuperavel.
- Ofertas ganharam extrator dedicado e condicoes de preco, incluindo preco anterior, Pix, boleto, cartao e parcelamento.
- Recomendacao usa produtos canonicos, evidencia por campo e pendencias quando preco/frete nao estao confirmados.
- Aprovacao por item, cotacao por fornecedor, pedido e entrega possuem endpoints/fluxos operacionais conectados ao request.

Validado nesta rodada:

- suite backend completa: `pytest -q` com 284 testes;
- compile Python: `python -m compileall -q app`;
- frontend: `npm run test:run`, `npm run lint`, `npx tsc --noEmit` e `npm run build`;
- Alembic local: `upgrade head`, `heads` e `current` em `c9f2b6a1d4e7`;
- Playwright autenticado com evidencias em `output/playwright/purchases-intelligent-final/`.

Ainda precisa de evidencia dedicada:

- downgrade/upgrade em banco QA isolado;
- `ruff check app`, pois `ruff` nao esta instalado no ambiente atual;
- envio real de e-mail somente com conta SMTP de homologacao/operacional configurada;
- conectores externos pagos ou oficiais conforme credenciais;
- cenarios reais de pedido, entrega parcial, modo homologacao e loja bloqueada.

Status Visao Vesper: parcial alto com base operacional validada; ainda nao classificar como 100% concluido enquanto conectores externos e estados reais de pos-compra nao tiverem evidencia completa.
