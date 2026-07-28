# Visão Consolidada do Portal Vesper

## 1. Propósito

O Portal Vesper é o sistema operacional interno da empresa. Ele existe para substituir processos manuais, planilhas, aplicativos antigos, e-mails soltos, pastas de rede, prints, conversas e dependência da memória das pessoas.

O Portal não é uma coleção de telas. Ele é uma rede de processos conectados.

## 2. Resultado esperado

O usuário informa uma necessidade imperfeita e o Portal transforma essa necessidade em uma ação organizada, segura e pronta para revisão.

Exemplos:

- “cotar tubo 1.1/2”;
- “comprar memória RAM para o PC de um colaborador”;
- “criar proposta S1000 para este cliente”;
- “abrir chamado para o computador da recepção”;
- “pedir aprovação destes links”;
- “mostrar OPs em risco”.

## 3. Regra de ouro

> **DETECTAR → ENTENDER → SUGERIR → PREENCHER → MOSTRAR PREVIEW → CONFIRMAR → EXECUTAR → REGISTRAR HISTÓRICO**

### Detectar

A necessidade pode vir de uma tela, busca, Koda, e-mail autorizado, estoque baixo, proposta aceita, link, evento do Kanban ou alerta de TI.

### Entender

O Portal reúne contexto de módulos relacionados antes de fazer perguntas.

### Sugerir

O sistema apresenta o próximo passo, alternativas, riscos e dados encontrados.

### Preencher

Tudo que já existe no Portal deve ser reaproveitado automaticamente.

### Mostrar preview

A pessoa vê em linguagem humana exatamente o que será criado, alterado, enviado ou aprovado.

### Confirmar

Ações importantes exigem confirmação adequada ao risco.

### Executar

O módulo responsável realiza a ação. Integrações externas podem ser executadas pelo n8n, mas a decisão continua no Portal.

### Registrar histórico

Toda ação importante registra autor, data, valores anteriores e novos, origem, justificativa, evidência e resultado.

## 4. Público

O Portal é construído para usuários comuns, leigos, lentos ou sem costume com sistemas.

O usuário comum não deve precisar entender:

- UUID;
- JSON;
- payload;
- endpoint;
- parser;
- schema;
- migration;
- enum técnico;
- query;
- nome interno de permissão;
- estrutura do banco;
- caminho físico de arquivo.

## 5. Capacidades globais

### Entrada universal

O usuário não deve precisar saber qual módulo abrir. A busca global e o Koda podem identificar a intenção e abrir o processo correto.

### Contexto compartilhado

Um módulo deve consultar outro quando isso eliminar trabalho.

Exemplo: uma compra de memória RAM pode consultar o TI para descobrir compatibilidade com o computador.

### Camada Universal de Ações

Toda intenção importante deve poder virar um rascunho estruturado, com origem, dados usados, campos faltantes, risco, preview e confirmação.

### Histórico conectado

A história de um processo deve continuar entre módulos.

Exemplo: necessidade → pesquisa de compra → aprovação → compra → entrega → instalação → atualização do ativo.

### Aprendizado operacional

O Portal deve reaproveitar decisões anteriores, sem inventar dados.

Exemplos:

- sugerir fornecedor já aprovado;
- reconhecer item comprado repetidamente;
- sugerir transformar compra avulsa em item recorrente;
- aprender correções de matching;
- destacar padrões de atraso.

## 6. Não negociáveis

- PostgreSQL é a fonte da verdade operacional.
- Excel, NAS e sistemas antigos são fontes de entrada, importação ou auditoria.
- Navegação comum não deve reler planilhas ou rede.
- Nenhum dado fake pode parecer produção.
- Nenhuma ação sensível é executada silenciosamente.
- Nenhum segredo aparece em listagem ou log.
- Erros devem ser humanos e aparecer no contexto certo.
- Tema claro e escuro devem ter legibilidade equivalente.
- Tela operacional não deve desperdiçar espaço com hero decorativo.
- Cada módulo deve ter uma função clara e uma ação principal evidente.
- Informações técnicas ficam ocultas por padrão.
- O Chat é global, mas toda ação segue autorização do módulo de destino.

## 7. Definição de valor

O Portal está no caminho certo quando:

- a pessoa encontra informações mais rápido que no Excel ou NAS;
- o comprador não precisa pesquisar e comparar tudo manualmente;
- o chefe decide com contexto, imagem, preço e alternativas;
- uma proposta aceita não precisa ser redigitada para virar OP;
- a produção enxerga dependências e riscos;
- TI encontra máquina, acesso e histórico rapidamente;
- Koda transforma conversa em ação;
- o Portal mostra o que precisa ser resolvido hoje;
- todos os módulos compartilham a mesma história operacional.

## 8. Antipadrões proibidos

- Thunderbird bonito;
- Excel bonito;
- NAS bonito;
- PDF bonito;
- Kanban bonito sem inteligência;
- chat bonito sem ação;
- CRUD bonito;
- dashboard decorativo;
- formulário enorme que pede tudo de uma vez;
- módulo isolado que obriga copiar e colar para outro.
