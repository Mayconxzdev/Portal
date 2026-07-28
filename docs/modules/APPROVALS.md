# Aprovações

![Referência visual de Aprovações](../assets/references/approvals-light.webp)

> A imagem define a decisão rápida com contexto, imagem, preço e histórico. Os itens exibidos são ilustrativos.

## Missão

Transformar pedidos, alternativas e ações sensíveis em decisões simples, granulares e auditáveis.

## Entradas

- pedido interno;
- opção de compra;
- carrinho ou link convertido;
- aprovação técnica;
- aprovação financeira;
- exceção;
- ação sensível;
- envio externo;
- alteração crítica.

## Modelo de decisão

Um pedido possui itens. Cada item pode possuir várias opções.

Exemplo: Memória RAM 8 GB DDR4 com cinco opções. O chefe escolhe uma opção para o item; não aprova cinco pedidos separados.

## Decisões possíveis

- aprovar;
- recusar;
- pedir alternativa;
- pedir preço menor;
- pedir informação;
- encaminhar para validação técnica;
- aprovar parcialmente;
- escolher opção;
- justificar.

## Links e carrinhos

O Portal tenta extrair:

- produto;
- imagem;
- preço;
- loja;
- frete;
- prazo;
- variação;
- quantidade;
- URL.

Quando não conseguir, pede somente o dado faltante.

## Estrutura visual

- tabs de pendentes, aprovadas, recusadas e aguardando informação;
- indicadores compactos;
- cada solicitação com imagem, solicitante, departamento, fornecedor, preço e histórico;
- ações visíveis: Aprovar, Recusar, Pedir mais barato e Pedir informação;
- comentário por item;
- comparação acessível sem abrir vários links;
- painel lateral com atividade e resumo útil.

## Alçadas

- por valor;
- por módulo;
- por risco;
- sequencial;
- paralela;
- técnica + financeira;
- substituto temporário.

## Integrações

- recebe de Compras;
- recebe pedido do Koda;
- recebe ação sensível;
- devolve decisão ao módulo de origem;
- alimenta Dashboard e BI.

## Segurança

- decisão validada no backend;
- aprovador precisa ter alçada real;
- opção escolhida e justificativa ficam vinculadas ao item;
- toda decisão registra antes, depois, ator e horário;
- link externo não executa script nem contorna segurança.

## Não considerar pronto se

- só houver aprovar/recusar o pedido inteiro;
- exigir abrir cada link externamente para entender;
- não permitir comentário por item;
- não devolver a escolha para Compras;
- mostrar payload ou metadado técnico;
- não existir trilha de auditoria.

## Critério Visão Vesper

O aprovador entende o contexto e decide sem depender de prints, planilhas ou várias abas externas.
