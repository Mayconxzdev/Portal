# AGENTS.md — Portal Vesper

## Identidade do projeto

Você está trabalhando no Portal Vesper, sistema operacional interno corporativo da Vesper/Ventrio.

O objetivo do Portal Vesper não é ser apenas uma interface bonita para apps antigos. O objetivo é substituir apps legados com uma plataforma única, inteligente, rápida, automática, auditável e simples para usuários leigos.

O usuário deve fazer ações simples, enquanto o Portal prepara o processo completo por trás.

Frase guia:
“O usuário pede uma coisa simples; o Portal entende o contexto, prepara tudo, executa o que é seguro e pede confirmação no que é sensível.”

## Regra principal

Não implemente tela bonita sem automação real.
Não copie apps antigos literalmente.
Não crie botão falso.
Não crie dados fake em módulo real.
Não quebre módulos funcionando.
Não apague código sem justificar.
Não exponha credenciais.
Não escreva direto no banco fora da API.
Não deixe IA/n8n serem fonte da verdade.

PostgreSQL é sempre a fonte oficial da verdade.

## Estado atual conhecido

O Portal já possui base real com:

* Auth e permissões;
* Dashboard;
* Kanban;
* TI / Help Desk;
* Chat;
* Aprovações;
* Administração;
* Tauri parcial;
* n8n rodando, mas sem workflows reais integrados.

Módulos ainda parciais ou planejados:

* Compras;
* Propostas;
* Estoque;
* Arquivos / Knowledge / NAS;
* Automações;
* Koda multi-agente.

## Stack oficial

Backend:

* Python;
* FastAPI;
* SQLAlchemy 2;
* Alembic;
* PostgreSQL;
* Redis;
* MinIO;
* n8n;
* LibreOffice headless futuro;
* SearXNG futuro.

Frontend:

* React;
* Vite;
* TypeScript;
* CSS Vanilla com tokens;
* Lucide React;
* Tauri Desktop.

Arquitetura:

* Monolito modular;
* PostgreSQL como fonte da verdade;
* Event Engine com Outbox Pattern;
* Redis Pub/Sub;
* WebSocket;
* Reaction Engine;
* Action Intent;
* Koda como agente operacional;
* n8n como executor, nunca como fonte da verdade.

## Comportamento obrigatório do agente

Antes de implementar:

1. Leia este AGENTS.md.
2. Leia docs/AI_HANDOFF.md, se existir.
3. Leia docs/STATE_OF_PROJECT.md, se existir.
4. Leia documentação do módulo afetado.
5. Analise o código real antes de propor alteração.
6. Explique o plano antes de editar.
7. Divida tarefas grandes em PRs pequenas.

Durante implementação:

1. Altere o mínimo necessário.
2. Preserve APIs existentes quando possível.
3. Mantenha permissões no backend.
4. Mantenha UI honesta.
5. Use nomes humanos na interface.
6. Nunca mostre JSON, payload, enum técnico ou ID cru para usuário comum.
7. Não use alert() nativo.
8. Não crie simulação como se fosse dado real.
9. Não introduza dependência nova sem justificar.
10. Não tocar em produção, banco real, NAS real ou credenciais reais.

Depois de implementar:

1. Rode ou indique testes necessários.
2. Rode typecheck/build quando a tarefa tocar frontend.
3. Atualize documentação se mudar arquitetura, fluxo ou módulo.
4. Entregue resumo do que mudou.
5. Liste arquivos alterados.
6. Liste riscos.
7. Liste validações feitas e não feitas.

## Níveis de automação

Todo módulo deve evoluir em 4 níveis:

1. Manual:
   O usuário consegue fazer tudo sozinho se IA/n8n estiverem fora.

2. Assistido:
   O Portal sugere, classifica, preenche, calcula, resume e organiza.

3. Automático com confirmação:
   O Portal prepara tudo e o usuário só revisa/confirma.

4. Automático seguro:
   Ações sem risco podem rodar sozinhas.

## Ações sensíveis

Sempre exigir confirmação ou aprovação formal para:

* enviar e-mail para fornecedor ou cliente;
* comprar;
* alterar estoque;
* aprovar gasto;
* revelar, copiar ou editar credencial;
* alterar permissão;
* apagar arquivo;
* alterar dado financeiro;
* responder cliente;
* criar pedido de compra;
* executar ação de IA/n8n com impacto real.

## Ações seguras

Podem ser automáticas:

* classificar;
* resumir;
* sugerir;
* preencher rascunho;
* criar rascunho;
* notificar;
* indexar;
* detectar duplicidade;
* vincular entidade;
* montar comparação preliminar;
* gerar preview;
* criar sugestão de ação.

## Modelo central sem duplicidade

Evite duplicar dados entre módulos. As entidades centrais devem ser reutilizadas:

* Pessoa;
* Usuário;
* Setor;
* Cargo/Função;
* Perfil de permissão;
* Computador/Ativo;
* Conta/E-mail;
* Acesso;
* Credencial/Segredo;
* Sistema/Serviço;
* Fornecedor;
* Cliente;
* Produto/Item;
* Arquivo/Documento;
* Evento;
* Notificação;
* Action Intent;
* Aprovação;
* Auditoria.

Acesso e Cofre não são módulos duplicados:

* Acesso = permissão/conta que alguém possui;
* Credencial = segredo necessário para acessar algo;
* Conta/E-mail = identidade externa;
* Pessoa = quem usa;
* Ativo/PC = onde está configurado.

## Koda

Koda é agente operacional, não mascote decorativo.

Koda deve atuar como:

* balão global;
* ajuda contextual;
* agente silencioso;
* supervisor de Action Intents;
* ponte com n8n;
* ponte com Knowledge/RAG.

Koda pode ler, entender, sugerir e preparar.
Koda só executa sozinho ações seguras.
Koda pede confirmação/aprovação para ações sensíveis.

## n8n

n8n é executor de automações.
n8n nunca escreve direto no banco.
n8n chama APIs oficiais do Portal.
n8n deve ser usado inicialmente para:

* IMAP;
* monitoramento de e-mails;
* notificações;
* relatórios;
* workflows pós-aprovação;
* integrações externas.

## Tauri Desktop

Tauri deve alimentar TI/Ativos automaticamente, coletando quando possível:

* nome do PC;
* usuário logado;
* IP;
* Windows;
* CPU;
* RAM;
* disco;
* programas instalados;
* impressoras;
* monitores;
* número de série;
* status básico;
* última sincronização.

## Modo de trabalho

Nunca faça “big bang”.
Sempre trabalhar em PRs pequenas.

Formato ideal de PR:

1. diagnóstico;
2. plano;
3. implementação mínima;
4. testes;
5. documentação;
6. relatório final.

## Proibição de comandos perigosos

Nunca execute comandos destrutivos sem aprovação explícita:

* rm -rf;
* del /s /q;
* format;
* drop database;
* truncate;
* delete massivo;
* mover/apagar diretórios grandes;
* limpar cache fora da pasta do projeto;
* alterar NAS;
* alterar .env real;
* enviar e-mail real;
* rodar workflow real em produção.

Para qualquer comando perigoso:

1. explique o comando;
2. explique o risco;
3. peça aprovação;
4. ofereça alternativa segura.

## Saída padrão esperada

Ao final de qualquer tarefa, responda com:

1. Resumo do que foi feito.
2. Arquivos alterados.
3. Testes/validações executados.
4. Testes/validações não executados.
5. Riscos restantes.
6. Próximo PR recomendado.
