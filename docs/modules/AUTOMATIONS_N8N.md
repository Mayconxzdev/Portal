# Automações / n8n

![Referência visual de Automações / n8n](../assets/references/automations-n8n-light.webp)

> A imagem define uma interface humana de automações. Os exemplos de workflows são ilustrativos e só podem aparecer como ativos quando realmente conectados.

## Missão

Executar integrações externas decididas pelo Portal e devolver resultado rastreável.

> **Portal decide. n8n executa. Portal registra.**

## Exemplos

- enviar notificação;
- chamar API;
- programar follow-up;
- sincronizar serviço;
- enviar documento;
- coletar informação;
- reagir a aprovação.

## Estrutura visual

Mostrar:

- nome;
- finalidade;
- gatilho;
- estado;
- última execução;
- sucesso;
- erro;
- responsável;
- pausar;
- histórico;
- impacto e destino.

O workflow técnico fica oculto do usuário comum.

## Contrato

- API autenticada;
- callback assinado;
- idempotência;
- retry controlado;
- timeout;
- correlação;
- log seguro;
- nenhum acesso direto ao banco.

## Governança

- ativação autorizada;
- versão;
- ambiente;
- credencial protegida;
- teste em sandbox;
- rollback;
- auditoria;
- dono e finalidade humana.

## UX

- status real, nunca placeholder;
- erro humano com próxima ação;
- logs técnicos restritos;
- pausar com confirmação quando houver impacto;
- diferenciar automação ativa, pausada, falhando e ainda não configurada.

## Não considerar pronto se

- workflow contiver MOCK/TODO e aparecer como ativo;
- não houver callback;
- escrever diretamente no banco;
- usuário comum precisar abrir n8n;
- não existir responsável, histórico ou finalidade;
- falha ficar invisível.

## Critério Visão Vesper

A automação pertence a um processo compreensível e nunca vira fluxo solto sem dono.
