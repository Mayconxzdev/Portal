# Integrações, Fontes Externas e Eventos

## 1. Regra geral

Fontes externas fornecem dados. O Portal trata, normaliza, valida e persiste. O uso comum consulta o banco do Portal.

## 2. Compras Nova

Uso:

- famílias;
- produtos;
- variações;
- especificações;
- fornecedores;
- contatos;
- preços;
- histórico e evidências.

Regras:

- ler estrutura visual;
- não alterar arquivo original;
- não executar macro;
- Preço é principal quando existir;
- Valor Final é metadado;
- consolidado não vira oferta;
- importação gera snapshot e revisão.

## 3. Cybersul

Uso inicial:

- código;
- descrição;
- unidade;
- complemento;
- saldo;
- custo;
- fornecedor;
- NCM;
- grupo;
- ativo/inativo.

O Portal não envia de volta sem confirmação, alçada e integração validada.

## 4. Belarc e coletores de TI

Uso:

- máquina;
- usuário;
- hardware;
- software;
- IP;
- hostname;
- AnyDesk;
- certificados;
- contas detectadas;
- alertas técnicos.

A origem e manutenção pertencem ao TI. Outros módulos consomem apenas dados autorizados.

## 5. NAS

Knowledge indexa:

- metadados;
- hash;
- texto;
- versão;
- contexto;
- permissões.

O NAS não deve ser lido em cada busca comum.

## 6. E-mail

Admin/Messias autoriza contas e escopos.

Monitoramento:

- lê pastas configuradas;
- cria eventos;
- classifica;
- vincula quando houver confiança;
- envia dúvida para revisão;
- não executa ação sensível sozinho.

Envio:

- usa conta autorizada;
- assinatura configurada;
- preview;
- confirmação;
- cópias configuráveis;
- histórico e idempotência.

## 7. Pesquisa de mercado

Usada para item não catalogado, compra avulsa, equipamento, serviço ou alternativa.

O Portal deve:

- entender especificação;
- enriquecer contexto;
- usar fontes autorizadas;
- registrar data e origem;
- remover duplicidades;
- comparar total, prazo, garantia e compatibilidade;
- mostrar incerteza;
- enviar opções para Aprovações;
- não tratar preço externo como permanente.

### Motor de Compras

O fluxo de pesquisa de Compras usa provedores em fases:

1. planejamento da necessidade;
2. fontes internas do Portal;
3. descoberta externa;
4. verificação por campo;
5. agrupamento canônico;
6. recomendação explicável.

Provedores suportados:

- Estoque e Catálogo;
- fornecedores internos;
- histórico de compras;
- SearXNG por `PURCHASES_SEARXNG_URL`;
- SerpApi por `SERPAPI_API_KEY`;
- Gemini Grounding por `GEMINI_API_KEY`;
- HTTPX seguro para verificação de URL.

Gemini e SerpApi são opcionais. Ausência de credencial não bloqueia a compra.
Gemini nunca confirma preço, frete, vendedor, nota fiscal, disponibilidade ou link final.

Eventos adicionados:

- `purchase.research.started`;
- `purchase.research.updated`;
- `purchase.offer.verified`;
- `purchase.recommendation.updated`;
- `purchase.item.approval_requested`;
- `purchase.item.approval_decided`;
- `purchase.rfq.ready`;
- `purchase.order.placed`;
- `purchase.delivery.received`.

## 8. Links e carrinhos

Ao receber link:

- extrair somente o que for permitido;
- validar URL;
- não executar script externo;
- registrar fonte;
- pedir manualmente o que não puder extrair;
- não depender de login privado;
- permitir print ou preenchimento assistido.

## 9. n8n

n8n:

- recebe evento;
- executa integração;
- devolve resultado;
- não altera banco diretamente;
- não decide aprovação;
- não guarda regra central;
- usa idempotência e retry;
- possui workflow vinculado a uma finalidade humana.

## 10. Eventos e Action Intents

Evento é fato. Action Intent é ação proposta.

Exemplo:

`stock.low_detected` → Action Intent “Criar cotação para o item X”.

A Action Intent precisa de:

- origem;
- contexto;
- módulo;
- preview;
- risco;
- permissão;
- confirmação;
- execução;
- histórico.

## 11. Falhas

Integrações devem exibir:

- última sincronização;
- estado;
- erro humano;
- retry;
- impacto;
- opção de pausar;
- logs técnicos restritos.

## Compras - pesquisa, worker e eventos operacionais

Compras usa PostgreSQL como fonte de verdade e Redis/Dramatiq apenas como execucao assicrona.

Fluxo:

1. usuario cria ou revisa uma compra;
2. item externo ou interno abre `purchase_search_sessions`;
3. `purchase_research_jobs` enfileira a execucao;
4. o worker consulta provedores disponiveis e grava tarefas, fontes, produtos canonicos, opcoes e evidencias;
5. a UI acompanha por refetch/polling e nao depende do worker para manter estado persistido;
6. aprovacao, cotacao, pedido e entrega emitem eventos humanos e auditaveis.

Eventos de Compras:

- `purchase.research.started`;
- `purchase.research.updated`;
- `purchase.offer.verified`;
- `purchase.recommendation.updated`;
- `purchase.item.approval_requested`;
- `purchase.item.approval_decided`;
- `purchase.rfq.ready`;
- `purchase.order.placed`;
- `purchase.delivery.received`.

Provedores externos sao opcionais. `SERPAPI_API_KEY`, `GEMINI_API_KEY`, SMTP e credenciais de marketplace devem vir de ambiente ou Cofre, nunca de codigo-fonte, migration, fixture, log ou screenshot.

Notificacoes devem ser geradas somente quando houver acao humana real: revisar comparativo, responder aprovacao, executar compra, tratar entrega divergente ou corrigir pesquisa bloqueada. Eventos internos de progresso nao devem criar notificacao comum.
