# Walkthrough - Sprint 2 Compras PR 4/PR 5

## Fluxo PR 3 mantido

1. Abrir Compras.
2. Confirmar que a Central mostra cards operacionais sem destaque para aprovacao.
3. Confirmar navegacao principal: Central, Nova cotacao, Cotacoes, Respostas, Comparativo, Pedidos, Entregas e Historico.
4. Confirmar que `Mais opcoes` aparece apenas para Admin/Messias e agrupa telas tecnicas.
5. Criar ou abrir uma cotacao.
6. Adicionar produto do Catalogo, item manual ou lista colada.
7. Avancar para Fornecedores.
8. Selecionar fornecedor sugerido e distribuir itens.
9. Salvar distribuicao.
10. Avancar para Revisar e enviar.
11. Confirmar que cada fornecedor tem uma mensagem persistida.
12. Ver conta remetente Vesper/Ventrio, destinatario, BCC e assinatura.
13. Desmarcar BCC e confirmar que a mensagem atualiza.
14. Editar assunto ou mensagem e salvar.
15. Trocar conta remetente e confirmar assinatura/conta atualizada.
16. Ver o preview em fundo claro como o fornecedor recebera.
17. Confirmar que PDF opcional aparece como estado honesto ainda desabilitado.
18. Em `ENVIRONMENT=testing`, enviar e confirmar status `sent` fake.
19. Tentar enviar novamente e confirmar bloqueio de duplicidade por idempotencia.
20. No Estoque & Catalogo, clicar `Cotar` em um item e confirmar abertura de `/purchases?quote=<id>&step=products`.

## Fluxo PR 4 validado

1. n8n ou teste envia callback para `/api/v1/purchases/monitoring/email/callback`.
2. Portal valida HMAC, timestamp, webhook id, origem e conta.
3. Callback duplicado nao cria mensagem repetida.
4. Mensagem inbound aparece em `purchase_email_inbound_messages`.
5. Anexos aparecem com hash, tipo, tamanho e status de seguranca.
6. Executavel/script/macro detectavel fica bloqueado ou marcado como risco.
7. Portal cria candidato em `purchase_response_candidates`.
8. Central mostra resposta para revisar.
9. Abrir aba `Respostas`.
10. Conferir cards de alta, media e baixa confianca.
11. Abrir drawer de resposta.
12. Conferir resumo, mensagem segura, anexos e motivos.
13. Admin/Messias ve detalhes tecnicos; usuario comum nao ve payload/HMAC/JSON.
14. Confirmar vinculo, rejeitar, ignorar ou vincular manualmente.

## Fluxo PR 5 validado

1. Abrir resposta candidata.
2. Acionar extracao assistida.
3. Conferir campos encontrados no corpo/HTML/texto seguro de anexo.
4. Conferir confianca de preco, prazo, frete, pagamento, validade ou disponibilidade.
5. Abrir origem/evidencia textual do campo.
6. Corrigir valor quando necessario.
7. Confirmar revisao.
8. Confirmar que nada foi aplicado automaticamente em comparativo, Catalogo, pedido, estoque ou Cybersul.

## Nao executado neste ciclo

- Envio SMTP real.
- Leitura real de credenciais no Vault.
- Workflow n8n real conectado ao IMAP.
- PDF real anexado.
- Parsing binario direto de PDF/Excel; PR5 usa `text_preview` seguro ou revisao manual.
- Aplicacao dos dados revisados em quote lines/comparativo.
- Pedido de compra.
- Recebimento.
- Entrada real em estoque.
