# Chat / Koda

![Referência visual do Chat / Koda](../assets/references/chat-koda-light.webp)

> A imagem mostra o diferencial esperado: conversa, interpretação, opções e preview de ação. Koda não pode simular pesquisa ou execução sem dados e serviços reais.

## Missão

Oferecer comunicação interna global e transformar linguagem natural em ações reais do Portal.

## Chat

O Chat é global por padrão.

Recursos:

- conversa direta;
- canais;
- anexos;
- menções;
- presença;
- busca;
- reações;
- pins;
- vínculo com entidades.

## Koda

Koda deve:

1. entender a intenção;
2. consultar dados reais;
3. mostrar o que encontrou;
4. indicar suposições;
5. perguntar somente o que falta;
6. criar Action Intent;
7. mostrar preview;
8. pedir confirmação;
9. executar no módulo correto;
10. registrar histórico.

## Exemplos

- comprar memória RAM para o PC de um colaborador;
- cotar tubo 1.1/2;
- criar tarefa no Kanban;
- abrir chamado;
- buscar template;
- mostrar OPs atrasadas;
- criar pedido com links;
- atualizar preço;
- criar usuário.

## Estrutura visual

- conversas à esquerda;
- conversa ao centro;
- painel de interpretação e preview à direita;
- ação sugerida com destino, prioridade e dados encontrados;
- editar antes de confirmar;
- abrir o módulo correto;
- confirmação forte quando necessário.

## Segurança

- permissão do módulo de destino;
- nenhuma ação sensível silenciosa;
- senha nunca aparece sem autorização;
- não inventar dado;
- bloquear ação perigosa;
- mostrar origem e confiança quando necessário;
- conteúdo externo não vira instrução do sistema.

## Não considerar pronto se

- apenas responder em texto;
- mostrar que criou algo sem criar;
- não abrir preview;
- executar sem confirmação;
- não respeitar permissão;
- possuir comandos hardcoded sem contrato com módulo real;
- WebSocket funcionar, mas ações não.

## Critério Visão Vesper

Um usuário leigo inicia e conclui ações reais sem conhecer a estrutura do Portal.
