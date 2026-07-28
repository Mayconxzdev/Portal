# Arquitetura Canônica do Portal Vesper

## 1. Estilo arquitetural

O Portal Vesper adota um **monólito modular**, com domínios separados por responsabilidade e comunicação explícita por serviços, eventos internos e Action Intents.

A separação modular deve impedir que:

- Compras seja dona do catálogo;
- TI misture dados técnicos em Estoque;
- n8n vire fonte da verdade;
- Koda execute lógica paralela fora dos módulos;
- Knowledge seja apenas um navegador de pastas;
- um módulo altere dados de outro sem contrato claro.

## 2. Pilha principal

- **Backend:** FastAPI, Python, Pydantic e SQLAlchemy 2.0.
- **Banco:** PostgreSQL.
- **Migrações:** Alembic.
- **Frontend:** React, Vite e TypeScript.
- **Cache e eventos rápidos:** Redis.
- **Arquivos:** MinIO ou storage configurado.
- **Desktop:** Tauri.
- **Automações externas:** n8n.
- **Busca contextual:** índice textual e, quando necessário, busca híbrida.
- **Copiloto:** Koda, sempre apoiado por dados e permissões reais.

## 3. Fonte da verdade

O PostgreSQL é a fonte da verdade.

Fontes externas entram por importação ou sincronização:

- Compras Nova;
- exportação do Cybersul;
- NAS;
- Belarc e coletores;
- caixas de e-mail autorizadas;
- sistemas antigos;
- catálogos e pesquisas externas autorizadas.

Nenhuma fonte externa deve ser consultada repetidamente durante a navegação comum quando o dado pode ser processado e persistido.

## 4. Módulos e fronteiras

### Dashboard / Hoje

Dono da apresentação de pendências, riscos e próximas ações por perfil. Não é dono dos dados de negócio.

### Administração

Dona de usuários, perfis, módulos, permissões, políticas, contas autorizadas e auditoria administrativa.

### Estoque & Catálogo

Dono de item, identidade, código, variação, saldo, fornecedor por item, oferta, preço e histórico comercial do item.

### Compras

Dona de necessidade de aquisição, pesquisa, RFQ, opção, comparativo, decisão de compra, execução e acompanhamento.

### Aprovações

Dona da decisão humana, alçada, comentário, aprovação parcial, opção escolhida e justificativa.

### Propostas

Dona do documento comercial, template, versão, envio, resposta e sinal de aceite.

### Kanban / Produção / Projetos

Dono da execução do trabalho, etapas, responsáveis, bloqueios, prazos, WIP, OP e progresso.

### TI / HelpDesk / Cofre / Acessos

Dono de ativo, máquina, chamado, inventário, acesso, credencial, certificado, manutenção e contexto técnico.

### Knowledge / Arquivos / NAS

Dono da indexação documental, versão, contexto, origem, vínculo e permissões de arquivo.

### Chat / Koda

Dono da conversa e da interpretação inicial. Não é dono da regra de negócio do módulo de destino.

### Central de Monitoramento

Dona da ingestão autorizada de eventos externos, classificação e criação de sugestões de ação.

### Automações / n8n

Dona da orquestração de execução externa. Não decide regra de negócio e não escreve diretamente no banco.

### BI / Relatórios

Dono de métricas, snapshots e leitura analítica. Não altera o estado operacional diretamente.

## 5. Camada Universal de Ações

Uma Action Intent deve conter, no mínimo:

- intenção;
- módulo de destino;
- origem;
- usuário solicitante;
- dados encontrados;
- dados faltantes;
- nível de risco;
- preview humano;
- permissões necessárias;
- confirmação;
- resultado;
- histórico de execução.

O módulo de destino valida e executa. Koda, Dashboard, Monitoramento e alertas apenas criam ou apresentam a intenção.

## 6. Eventos internos

Eventos devem representar fatos, não comandos vagos.

Exemplos:

- `stock.low_detected`;
- `purchase.research_ready`;
- `approval.option_selected`;
- `proposal.acceptance_detected`;
- `kanban.card_blocked`;
- `it.asset_upgrade_required`;
- `knowledge.document_indexed`;
- `monitoring.message_classified`.

Cada evento deve ter:

- identificador;
- tipo;
- origem;
- entidade relacionada;
- data;
- ator;
- payload mínimo;
- idempotency key quando necessário.

## 7. Sincronia ponta a ponta

### Necessidade de compra aberta

Koda ou Compras entende a necessidade → TI enriquece compatibilidade → Compras pesquisa e normaliza opções → Aprovações recebe alternativas → opção escolhida volta para Compras → entrega e instalação atualizam TI ou Estoque → BI registra resultado.

### Estoque baixo

Estoque detecta risco → considera demanda de OP → cria sugestão de compra → Compras usa fornecedores e histórico → Monitoramento acompanha respostas → decisão atualiza histórico → Kanban deixa de exibir bloqueio quando resolvido.

### Proposta aceita

Monitoramento detecta possível aceite → Propostas apresenta confirmação → Kanban recebe OP preenchida → Estoque verifica material → Compras recebe faltas → Knowledge vincula arquivos.

## 8. Performance

Metas de produto:

- tela operacional inicial em até 1 segundo em ambiente local adequado;
- busca após debounce em até 300 ms;
- abertura de drawer em até 500 ms;
- nenhuma releitura de Excel ou NAS em busca comum;
- paginação e virtualização quando necessário;
- índices adequados;
- cache invalidado por evento, não por tempo arbitrário;
- operações pesadas em background com status visível.

## 9. Evolução segura

- toda alteração de schema usa migration;
- não apagar tabela legada sem inventário, migração e evidência;
- não manter tabela duplicada como solução permanente;
- imports devem ser idempotentes;
- integrações devem possuir retry controlado;
- toda mudança relevante deve ter teste e auditoria;
- documentos canônicos não devem conter números de sprint ou afirmações de conclusão não verificadas.
