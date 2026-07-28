# Propostas

![Referência visual de Propostas](../assets/references/proposals-light.webp)

> A imagem representa o alvo: pedido, cliente, itens, preview, versões e resposta em uma única história. Não criar PDF fake ou botão de envio sem backend real.

## Missão

Responder o cliente com proposta pronta, versionada, rastreável e conectada à produção.

## Entradas

- e-mail monitorado;
- pedido recebido manualmente;
- WhatsApp registrado;
- Koda;
- cliente e produto selecionados.

## Fluxo canônico

1. identificar cliente e necessidade;
2. sugerir template;
3. preencher dados existentes;
4. aplicar produtos, quantidade e condições;
5. permitir ajustes;
6. gerar preview;
7. salvar versão;
8. preparar e-mail;
9. confirmar envio;
10. acompanhar resposta;
11. detectar possível aceite;
12. usuário confirmar;
13. sugerir OP preenchida.

## Estrutura visual

- cabeçalho com número, status e ações;
- stepper curto;
- pedido do cliente;
- dados do cliente preenchidos;
- itens da proposta;
- template sugerido;
- preview do documento;
- preview do e-mail;
- versões v1, v2 e v3;
- status da resposta e atividades.

## Casos

- produto padrão;
- vários produtos;
- opcionais;
- serviço;
- desconto;
- condição especial;
- prazo especial;
- anexos técnicos;
- revisão;
- exceção que exige aprovação.

## Templates

Templates pertencem ao Knowledge. Propostas registra:

- template usado;
- versão;
- campos;
- documento gerado;
- vínculo com cliente e produto.

## Aceite e OP

O Monitoramento pode sugerir aceite, mas a pessoa confirma.

Depois o Portal:

- cria rascunho de OP;
- leva cliente, itens, prazo e anexos;
- verifica Estoque;
- sinaliza Compras;
- mantém vínculo com a proposta e versão aceita.

## Não considerar pronto se

- o documento só existir no frontend;
- não houver rascunho e versão no banco;
- a pessoa precisar editar PDF manualmente;
- envio não tiver preview e confirmação;
- aceite não continuar para OP;
- resposta não ficar vinculada.

## Critério Visão Vesper

Do pedido do cliente à OP, os dados continuam na mesma história sem redigitação.
