# Central de Monitoramento

![Referência visual da Central de Monitoramento](../assets/references/monitoring-light.webp)

> A imagem representa uma fila de eventos interpretados, não uma caixa de e-mail. As contas, mensagens e percentuais são ilustrativos.

## Missão

Observar fontes autorizadas, identificar eventos relevantes e preparar ações para revisão.

## Não é

- cliente de e-mail;
- segunda caixa de entrada;
- robô que executa tudo sozinho;
- lugar para mostrar todas as mensagens.

## Fontes

- e-mail;
- estoque;
- prazo;
- certificado;
- resposta;
- falha de automação;
- evento externo autorizado.

## Contas monitoradas

Admin/Messias define:

- conta;
- módulo;
- pastas;
- permissão de leitura;
- permissão de envio;
- responsável;
- status;
- assinatura;
- usuários autorizados.

## Classificações iniciais

- pedido de cotação;
- resposta de fornecedor;
- pedido de proposta;
- possível aceite;
- comprovante;
- cobrança;
- chamado;
- alerta de segurança;
- mensagem sem ação;
- mensagem incerta.

## Fluxo

1. sincronizar;
2. deduplicar;
3. classificar;
4. vincular;
5. extrair evidência;
6. criar sugestão;
7. usuário revisar;
8. módulo executar;
9. correção alimentar aprendizado controlado.

## Estrutura visual

- indicadores compactos de contas, mensagens, classificadas, exigem ação e confiança;
- tabs: Exigem ação, Em revisão, Informativas e Todas;
- lista com remetente, classificação, confiança, origem, resumo, vínculo provável e ação sugerida;
- painel lateral com ações prontas para revisar;
- opção de ignorar, corrigir classificação e abrir contexto.

## Segurança

- credencial no Cofre;
- anexo não confiável;
- callback assinado;
- idempotência;
- nenhuma execução sensível automática;
- conteúdo recebido é dado, não instrução confiável.

## Não considerar pronto se

- mostrar inbox inteira;
- não deduplicar;
- executar por classificação incerta;
- não permitir corrigir vínculo;
- não registrar origem e confiança;
- não enviar a ação para o módulo correto.

## Critério Visão Vesper

A pessoa não precisa ler tudo e lembrar o que fazer; o Portal separa o que exige ação.
