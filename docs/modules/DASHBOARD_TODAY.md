# Dashboard / Hoje

![Referência visual do Dashboard / Hoje](../assets/references/dashboard-today-light.webp)

> Referência de hierarquia e densidade. Os números e nomes da imagem são ilustrativos. O Dashboard real só pode mostrar dados existentes e autorizados.

## Missão

Mostrar a cada pessoa **o que precisa ser resolvido agora**, por que importa e qual é a próxima ação.

Não é página de boas-vindas, coleção de gráficos ou repetição de todos os módulos.

## Usuários e personalização

A tela é individual por perfil, permissão, responsabilidade e contexto.

Exemplos:

- Compras: cotações sem resposta, pesquisas para revisar, itens críticos e compras aprovadas;
- Diretoria: aprovações, OPs em risco, compras paradas e propostas sem retorno;
- Produção: OPs do dia, bloqueios, material pendente e prazo;
- TI: chamados, certificados, ativos e acessos;
- usuário comum: tarefas, pedidos, mensagens e ações que dependem dele.

## Estrutura visual

- cabeçalho compacto;
- faixa curta de indicadores realmente acionáveis;
- pendências prioritárias em destaque;
- aprovações e ações rápidas;
- blocos menores para compras, produção, TI e propostas;
- sem hero grande;
- abrir o módulo já no item correto.

Cada card deve responder:

- o que aconteceu;
- por que importa;
- impacto;
- prazo;
- responsável;
- próxima ação.

## Inteligência

- ordenar por impacto, não apenas data;
- agrupar itens relacionados;
- explicar o motivo da prioridade;
- permitir resolver, delegar, adiar ou abrir o contexto;
- evitar notificação duplicada;
- aprender preferência de visualização sem esconder risco crítico.

## Integrações

Consome eventos e pendências de todos os módulos. Não altera dados de negócio diretamente. Pode abrir o módulo ou criar Action Intent.

## Segurança

- respeitar permissão e escopo;
- não revelar valores, clientes, chamados ou segredos sem autorização;
- não permitir que card agregado contorne a permissão do módulo de origem.

## Não considerar pronto se

- mostrar apenas números;
- exibir pendências que o usuário não pode resolver;
- exigir abrir vários módulos para descobrir contexto;
- usar dados fake;
- repetir cards decorativos;
- não explicar por que algo está prioritário.

## Critério Visão Vesper

O usuário entra e sabe o que fazer sem procurar manualmente em vários módulos.
