# Ordem Recomendada de Evolução

## 1. Decisão principal

O primeiro módulo a ser concluído sob a nova Visão Vesper deve ser **Administração**.

A razão não é visual. Administração define quem pode visualizar, criar, editar, aprovar, importar, revelar segredo, configurar conta monitorada e executar ações em todos os demais módulos.

Sem essa base, qualquer evolução de Compras, Koda, Monitoramento ou Propostas nasce com permissões, auditoria e experiência inconsistentes.

## 2. Bloco inicial obrigatório — Fundação global curta

Antes do primeiro módulo, executar um bloco pequeno e objetivo:

- confirmar branch e worktree;
- validar migrations e head do Alembic;
- consolidar `humanizeApiError` em todos os componentes compartilhados;
- validar tokens de tema claro e escuro;
- consolidar stepper, drawer, modal, confirmação, loading e estado vazio;
- remover exposição técnica global óbvia;
- impedir `alert()` e mensagens fora do contexto;
- executar testes, lint, typecheck e build.

Este bloco não deve virar outra auditoria longa.

## 3. Ordem principal

### 1. Administração

Entregar:

- criação de usuário em três etapas;
- perfis sugeridos;
- ajustes avançados recolhidos;
- revisão em linguagem humana;
- edição por drawer;
- acesso temporário;
- onboarding, mudança de função e desligamento;
- auditoria humana;
- tema claro e escuro equivalentes.

**Portão de saída:** criar, editar, desativar e revisar acessos sem termo técnico, sem perder dados e sem `[object Object]`.

### 2. Estoque & Catálogo — validação e fechamento

Não reconstruir automaticamente o que já funciona. Revalidar:

- busca e variações;
- saldo, preço e fornecedor;
- histórico isolado por item;
- performance;
- nenhum Excel em runtime comum;
- Cotar Produto abrindo Compras preenchido;
- visual alinhado à referência.

**Portão de saída:** item correto abre a ação seguinte sem redigitação.

### 3. Compras + Aprovações

Devem evoluir juntas porque a jornada de compra termina em decisão.

Cobrir:

- item conhecido;
- fornecedor homologado;
- mercado aberto;
- link ou carrinho;
- serviço;
- emergência;
- cinco opções comparáveis;
- aprovação por item e opção;
- pedido de preço menor ou informação;
- execução e pós-compra.

**Portão de saída:** comprar memória RAM ou um item catalogado sem pesquisar, copiar e comparar manualmente em várias ferramentas.

### 4. Chat / Koda conectado a ações reais

Koda só deve prometer ações que os módulos já executam.

Começar com:

- criar usuário;
- cotar produto;
- pesquisar compra;
- criar pedido interno;
- abrir chamado;
- criar card;
- buscar arquivo;
- mostrar pendências.

**Portão de saída:** comando gera Action Intent, preview, confirmação e histórico real.

### 5. Central de Monitoramento

Implementar depois que os módulos de destino tiverem contratos reais.

Primeiras classificações:

- solicitação de cotação;
- resposta de fornecedor;
- pedido de proposta;
- possível aceite;
- alerta de TI;
- mensagem sem ação.

**Portão de saída:** separar o que exige ação sem virar outra caixa de entrada.

### 6. Propostas + Knowledge + Kanban ponta a ponta

Construir a jornada:

pedido do cliente → proposta versionada → envio → resposta → aceite confirmado → OP → arquivos → materiais → produção.

**Portão de saída:** não editar PDF manualmente e não redigitar proposta para criar OP.

### 7. TI integrado aos processos

O TI pode ser desenvolvido em paralelo por outra pessoa, mas deve respeitar contratos comuns desde cedo.

Entregar integração com:

- Administração para onboarding e desligamento;
- Compras para compatibilidade e upgrade;
- Monitoramento para alertas;
- Knowledge para manuais;
- BI para recorrência e risco.

### 8. Dashboard / Hoje + BI

Somente depois que existirem eventos e pendências confiáveis.

Dashboard mostra o que fazer agora. BI mostra padrão, impacto e ação recomendada.

### 9. Automações / n8n

Entrar como executor de processos já consolidados.

> Portal decide → n8n executa → Portal recebe resultado → histórico é atualizado.

## 4. Trilha paralela de TI

| Momento | Contrato de TI necessário |
|---|---|
| Administração | pessoa, máquina, perfil, acesso e tarefa de onboarding |
| Compras | endpoint/serviço de compatibilidade e contexto do ativo |
| Monitoramento | evento de alerta, certificado e falha |
| Propostas/Kanban | suporte a anexos, manutenção e dependência técnica |
| BI | eventos de chamado, ativo, acesso e segurança |

## 5. Como escolher o próximo pacote real

Antes de iniciar cada pacote, verificar:

1. qual jornada manual será eliminada;
2. quais dados reais existem;
3. quais módulos dependem dela;
4. qual risco de segurança existe;
5. quais estados e erros precisam ser tratados;
6. qual imagem visual é a referência;
7. qual critério prova valor para usuário leigo.

## 6. Proibição

Não iniciar um módulo apenas porque sua tela parece mais incompleta. A ordem deve seguir dependência, valor operacional e capacidade de concluir uma jornada real.
