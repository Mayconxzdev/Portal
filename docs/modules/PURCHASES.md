# Compras

![Referência visual de Compras](../assets/references/purchases-light.webp)

> A imagem representa a direção desejada: necessidade, pesquisa, comparação, aprovação e execução. O módulo não deve virar formulário de e-mail nem inventar pesquisa externa que não exista.

## Missão

Transformar uma necessidade em aquisição pesquisada, comparada, aprovada, executada e rastreada.

Compras não é um cliente de e-mail.

## Entradas

- item do Estoque;
- pedido falado ou digitado;
- e-mail classificado;
- pedido interno;
- OP bloqueada;
- link ou carrinho;
- comando do Koda;
- alerta;
- necessidade de TI;
- serviço ou compra administrativa.

## Estrutura visual

- indicadores de necessidades, respostas, aprovadas, negociação e economia;
- fluxo visível: Necessidade → Pesquisa → Comparativo → Aprovação → Compra;
- lista de necessidades à esquerda;
- área central de pesquisa e comparação;
- painel lateral de aguardando resposta e aprovadas;
- resumo da melhor opção e próxima ação no rodapé;
- nenhuma composição manual de e-mail como centro da tela.

## Trilhas de aquisição

### Item conhecido

Usa catálogo, saldo, histórico e fornecedores. Pode gerar RFQ, comparar respostas e atualizar preço.

### Fornecedor homologado

Sugere cobertura, rascunho, preview, confirmação, follow-up e resposta estruturada.

### Mercado aberto

Exemplo: memória RAM 8 GB DDR4.

1. entender necessidade;
2. consultar TI quando aplicável;
3. pedir somente especificação faltante;
4. pesquisar fontes autorizadas;
5. eliminar incompatíveis;
6. agrupar duplicados;
7. mostrar até cinco opções relevantes;
8. comparar total, frete, prazo, garantia, reputação e compatibilidade;
9. enviar opções para Aprovações;
10. receber a opção escolhida;
11. abrir execução;
12. registrar compra, entrega e resultado.

### Link ou carrinho

Extrair dados permitidos, organizar itens, buscar alternativa e pedir apenas o que faltar.

### Serviço

Registrar escopo, prazo, fornecedor, orçamento, condição, anexo e aprovação. Não transformar serviço em SKU.

### Emergência

Trilha reduzida com motivo, impacto, alçada, auditoria e revisão posterior da causa.

## Comparação

Considerar:

- preço unitário e total;
- frete;
- prazo;
- pagamento;
- garantia;
- compatibilidade;
- reputação;
- histórico;
- confiança;
- diferença para referência.

O Portal sugere. A pessoa decide.

## Pós-compra

- pedido;
- status;
- entrega;
- recebimento;
- comprovante;
- vínculo com ativo ou estoque;
- atualização de preço;
- avaliação;
- aprendizado.

## Inteligência

- fornecedor provável;
- melhor distribuição por fornecedor;
- item equivalente;
- compra consolidada;
- preço fora do padrão;
- repetição de item avulso;
- follow-up;
- aprovação técnica;
- detecção de resposta pelo Monitoramento.

## Integrações

- Estoque fornece item;
- TI fornece compatibilidade;
- Aprovações escolhe;
- Monitoramento captura resposta;
- Knowledge guarda evidência;
- Kanban recebe dependência;
- BI mede prazo e economia.

## Não considerar pronto se

- o comprador ainda precisar pesquisar tudo manualmente;
- a tela começar por destinatário e texto de e-mail;
- só funcionar para fornecedores com e-mail cadastrado;
- não suportar item avulso, serviço, link ou mercado aberto;
- aprovação não devolver a opção escolhida;
- não existir acompanhamento pós-compra.

## Critério Visão Vesper

O comprador revisa uma aquisição preparada em vez de pesquisar, copiar, escrever e comparar tudo manualmente.

## Motor de Inteligencia de Compras

Estado implementado nesta rodada:

- `PurchaseResearchPlanner`: interpreta necessidade, categoria, destino e orcamento e cria subtarefas por categoria.
- `CompatibilityResolver`: usa especificacao, destino textual e ativos de TI quando houver ativo vinculado ao texto informado.
- `OfferVerificationEngine`: separa descoberta de confirmacao e grava evidencia por campo da oferta.
- `PurchaseRecommendationAgent`: gera resumo humano, destaques e pendencias sem inventar preco, frete, vendedor, avaliacao, disponibilidade ou link.

Persistencia:

- `purchase_search_sessions`;
- `purchase_research_tasks`;
- `purchase_search_sources`;
- `purchase_offer_field_evidence`;
- `purchase_canonical_products`;
- extensoes em `purchase_item_options` para sessao, produto canonico, compatibilidade, confianca, origem, frete, prazo, nota fiscal, garantia e verificacao.

Provedores:

- Estoque e fornecedores internos quando o item e interno;
- historico de compras como contexto;
- SearXNG via `PURCHASES_SEARXNG_URL`;
- SerpApi via provider existente e `SERPAPI_API_KEY`;
- Gemini Grounding opcional via `GEMINI_API_KEY` e `PURCHASES_GEMINI_MODEL` (default local: `gemini-3.5-flash`), apenas para expandir consulta e contexto, nunca para confirmar oferta;
- HTTPX para verificacao segura de URL quando permitido.

Regras obrigatorias:

- discovery nao e oferta confirmada;
- preco, frete e disponibilidade sem evidencia ficam como pendencia;
- nomes tecnicos de provedores nao aparecem no texto comum da recomendacao;
- a chave Gemini nao deve ser hardcoded, logada, commitada ou usada a partir de conversa.

Fluxos conectados:

- criar/consultar/atualizar sessao de pesquisa por item;
- verificar oferta por item;
- recomendacao por item;
- pedir aprovacao opcional por item/opcao;
- preparar RFQ de fornecedores cadastrados por item.

Ainda parcial:

- cache compartilhado entre sessoes de provedores externos;
- conectores oficiais de marketplaces;
- Playwright dinamico para lojas;
- calculo real de frete quando a loja bloqueia ou exige sessao;
- execucao assicrona longa em worker separado;
- UX completa de decisao de aprovador para escolher alternativa ou pedir outra marca alem do contrato ja existente de Approvals.

## Atualizacao operacional - Central unica de compras

Esta rodada consolida Compras como uma central operacional unica. A entrada principal continua sendo **Nova compra**; cotacao e apenas um caminho possivel quando o item interno ou fornecedor cadastrado pede essa jornada.

### Criacao idempotente

- `POST /api/v1/purchases/requests` aceita `idempotency_key` e `client_request_id`.
- O backend registra a chave em `purchase_request_idempotency_keys` por usuario.
- Reenvio com a mesma chave e o mesmo payload retorna a compra ja criada.
- Reenvio com a mesma chave e payload diferente e rejeitado para evitar duplicidade silenciosa.
- O frontend gera a chave antes do submit e consulta `/requests/by-idempotency/{key}` quando ocorre erro de rede apos persistencia.

### Revisao antes de persistir

- `POST /api/v1/purchases/analyze` cria um draft interpretado em `purchase_interpreted_drafts`.
- Os itens ficam em `purchase_interpreted_draft_items` com tipo `internal`, `external`, `ambiguous` ou `mixed`.
- O usuario pode editar quantidade, unidade, destino, orcamento, tipo e remover itens antes de clicar em **Criar compra**.
- Nada vira compra definitiva antes da revisao.

### Autossugestao

- `GET /api/v1/purchases/suggestions` consulta Catalogo, Estoque, variacoes, codigos, historico, fornecedores e ativos de TI.
- Sugestoes aparecem como apoio ao campo universal, sem substituir a revisao humana.

### Pesquisa assicrona

- Sessoes de pesquisa sao persistidas em `purchase_search_sessions`.
- `purchase_research_jobs` rastreia job, tentativas e erro humano.
- Dramatiq com Redis executa `app.modules.purchases.worker:run_purchase_research_session`.
- A UI acompanha por refetch/polling e mantem estado apos reload.
- Falha do worker deixa a sessao como erro recuperavel, sem apagar resultados ja persistidos.

### Extracao de ofertas

- `offer_extractor` separa extracao de preco da orquestracao da pesquisa.
- A ordem de confianca prioriza dados estruturados/API/JSON-LD, estado da aplicacao, OpenGraph, DOM semantico, heuristica visual e Playwright quando permitido.
- `purchase_offer_price_conditions` guarda preco anterior, preco atual, Pix, boleto, cartao, parcelamento, desconto, condicao recomendada e preco de comparacao.
- O comparativo nao escolhe preco maior automaticamente quando existe Pix confirmado.

### Produto canonico e recomendacao

- Ofertas sao agrupadas por produto canonico quando ha identidade suficiente.
- Nao fundir DDR4 com DDR5, capacidades diferentes, desktop com notebook, kit com unidade ou novo com usado.
- A recomendacao diferencia menor total, melhor opcao geral, entrega mais rapida, menor risco e melhor compatibilidade.
- Preco ou frete sem evidencia ficam como pendencia e nao entram como menor total confirmado.

### Operacao

- Aprovacao e opcional por item/opcao, salvo regra empresarial existente.
- Cotacao direta prepara fornecedores, valida contato, gera uma previa por vez e exige confirmacao humana antes de envio.
- Modo de homologacao envia apenas ao destinatario de teste configurado e nao muda o estado operacional como envio real.
- Compra registra pedido, valor final, fornecedor/loja, link, comprovante e previsao.
- Entrega suporta recebimento total, parcial, divergencia, avaria e cancelamento.
- Estoque so e atualizado para item interno quando ha contrato e confirmacao explicita.

### Limites conhecidos

- Conectores oficiais de marketplaces dependem de credenciais e contrato de API.
- Gemini e SerpApi sao opcionais e nao bloqueiam a compra.
- Lojas com CAPTCHA, login, sessao privada ou bloqueio de automacao ficam marcadas como bloqueadas pela loja.
- Frete sem confirmacao da fonte real permanece pendente.
