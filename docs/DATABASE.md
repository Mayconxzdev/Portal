# Dados, Persistência e Propriedade — Portal Vesper

## 1. Princípio

O PostgreSQL é a fonte da verdade operacional. Esta documentação define **propriedade, invariantes e regras de evolução**, não substitui a introspecção real do banco.

Um inventário físico de tabelas deve ser gerado a partir de:

- models SQLAlchemy;
- migrations Alembic;
- `information_schema`;
- catálogos do PostgreSQL;
- uso real por serviços e endpoints.

## 2. Convenções

- tabelas em `snake_case` e plural;
- colunas em `snake_case`;
- timestamps com timezone quando aplicável;
- chaves estrangeiras indexadas;
- estados com enums controlados ou tabelas de domínio;
- `created_at`, `updated_at` e ator quando a entidade for auditável;
- soft delete apenas quando houver razão de negócio;
- JSONB para metadados variáveis, nunca como desculpa para evitar modelagem de dados críticos.

## 3. Propriedade de dados

### Core / Administração

Entidades esperadas:

- usuários;
- papéis;
- módulos;
- acesso por módulo;
- permissão por ação;
- sessões;
- auditoria;
- configurações e políticas.

### Estoque & Catálogo

Entidades esperadas:

- famílias;
- itens compráveis;
- árvore;
- especificações;
- fornecedores;
- ofertas;
- preços;
- histórico;
- importações;
- vínculos Cybersul x Compras Nova;
- índice de busca;
- fila de revisão;
- alertas.

A identidade do item nunca pode depender somente da descrição. Deve considerar caminho, família, produto, variação, especificação, medida, código e origem.

### Compras

Entidades esperadas:

- necessidade de compra;
- item solicitado;
- trilha de aquisição;
- RFQ;
- fornecedor convidado;
- mensagem e rascunho;
- resposta;
- linha de proposta;
- evidência;
- pesquisa de mercado;
- opção de compra;
- comparativo;
- decisão;
- pedido;
- entrega;
- recebimento;
- follow-up.

### Aprovações

Entidades esperadas:

- solicitação;
- item;
- opção por item;
- aprovador;
- comentário;
- decisão;
- alçada;
- histórico;
- link externo;
- metadado extraído;
- justificativa.

### Propostas

Entidades esperadas:

- cliente;
- template;
- proposta;
- versão;
- item;
- documento gerado;
- rascunho de e-mail;
- evento;
- envio;
- resposta;
- sinal de aceite;
- vínculo com OP.

### Kanban / Produção / Projetos

Entidades esperadas:

- quadro;
- coluna;
- card;
- responsável;
- checklist;
- comentário;
- anexo;
- etiqueta;
- bloqueio;
- dependência;
- visualização;
- configuração de TV;
- vínculo com proposta, compra, estoque e OP.

### TI / HelpDesk / Cofre

Entidades esperadas:

- chamado;
- ativo;
- inventário;
- software;
- conta;
- categoria de acesso;
- credencial;
- revelação de segredo;
- certificado;
- rede;
- manutenção;
- histórico;
- vínculo pessoa-máquina;
- AnyDesk;
- acesso NAS.

### Knowledge

Entidades esperadas:

- fonte;
- documento;
- versão;
- hash;
- índice textual;
- embedding quando adotado;
- tag;
- vínculo de contexto;
- permissão;
- evento de indexação.

### Chat / Koda

Entidades esperadas:

- conversa;
- participante;
- mensagem;
- anexo;
- menção;
- reação;
- presença;
- Action Intent relacionada;
- auditoria de ação do Koda.

### Monitoramento

Entidades esperadas:

- conta monitorada;
- pasta;
- regra;
- mensagem externa;
- evento;
- classificação;
- anexo;
- erro de sincronização;
- sugestão de ação;
- checkpoint de sincronização.

### Automações

Entidades esperadas:

- regra;
- evento de disparo;
- execução;
- callback;
- retry;
- falha;
- correlação com Action Intent;
- workflow externo vinculado.

### BI / Hoje

Entidades esperadas:

- evento operacional;
- ação pendente;
- snapshot;
- métrica;
- agregação;
- preferência de painel;
- cartão por usuário.

## 4. Regras críticas de dados

### Item de catálogo

- variações reais são registros separados;
- fornecedores nunca entram no nome do item;
- a coluna Preço é a oferta principal quando existir;
- Valor Final é metadado ou cálculo;
- linhas de total, média e fórmula não viram oferta;
- atualização manual preserva histórico;
- reprocessamento não apaga evidência ou atualização humana.

### Pesquisa de mercado

Cada opção deve registrar:

- fonte;
- URL;
- título bruto;
- descrição normalizada;
- preço;
- frete;
- total;
- prazo;
- vendedor;
- garantia;
- compatibilidade;
- confiança;
- data da coleta;
- evidência.

Preço externo é fotografia temporal, não verdade permanente.

### Aprovação

A decisão precisa apontar para o item e, quando houver alternativas, para a opção escolhida.

### Segredo

Credencial criptografada nunca deve ser copiada para logs, auditoria comum, eventos ou payloads de integração.

## 5. Busca

A busca operacional deve combinar, conforme o domínio:

- normalização;
- aliases;
- trigramas;
- full-text;
- filtros estruturados;
- busca semântica quando necessária;
- ranking por contexto e histórico.

O índice deve ser persistido e atualizado por evento.

## 6. Importações

Toda importação precisa registrar:

- fonte;
- arquivo ou versão;
- hash;
- horário;
- usuário;
- quantidade;
- avisos;
- erros;
- linhas em revisão;
- resultado;
- idempotency key.

Importar não significa alterar a fonte original.

## 7. Migrations e legado

- deve existir um único head Alembic por linha principal de evolução;
- qualquer merge de heads precisa ser intencional e testado;
- tabela sem model deve ser classificada;
- model sem migration é erro;
- tabela legada não pode ser apagada apenas porque parece sem uso;
- o status físico atual deve ficar em `CURRENT_STATE.md`, nunca misturado à especificação canônica.

## 8. Auditoria

Alterações críticas devem registrar:

- ator;
- ação;
- entidade;
- valor anterior;
- valor novo;
- origem;
- justificativa;
- IP ou contexto de sessão quando aplicável;
- correlação com Action Intent, aprovação ou automação.
