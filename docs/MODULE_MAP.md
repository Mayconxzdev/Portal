# Mapa Integrado dos Módulos

## 1. Visão geral

O Portal Vesper funciona como uma rede. Cada módulo possui uma responsabilidade clara, mas nenhum processo importante deve terminar isolado.

| Módulo | Responsabilidade principal | Entrega para outros módulos |
|---|---|---|
| Dashboard / Hoje | Priorizar o que exige ação agora | Abre ação no módulo responsável |
| Administração | Pessoas, perfis, acessos e políticas | Autorizações, contas e auditoria |
| Estoque & Catálogo | Produto, código, variação, saldo, preço e fornecedor | Item confiável para Compras e Produção |
| Compras | Necessidade, pesquisa, comparação, aquisição e acompanhamento | Opções para Aprovações, preço para Estoque, dependência para Kanban |
| Aprovações | Decisão humana por item, opção, valor e risco | Decisão ao módulo de origem |
| Propostas | Documento comercial, versões, envio e aceite | Rascunho de OP para Kanban |
| Kanban / Produção / Projetos | Execução, etapas, bloqueios, prazo e WIP | Eventos operacionais para Hoje e BI |
| TI | Ativo, chamado, acesso, credencial, certificado e contexto técnico | Compatibilidade e contexto para Administração e Compras |
| Knowledge | Documento, versão, busca e vínculo contextual | Template, manual, desenho e evidência |
| Chat / Koda | Conversa, intenção e preview de ação | Action Intent para qualquer módulo autorizado |
| Monitoramento | Observar fontes e separar o que exige ação | Sugestão estruturada ao módulo correto |
| Automações / n8n | Executar integrações externas autorizadas | Resultado e callback rastreável |
| BI / Relatórios | Interpretar eventos e gargalos | Recomendação de ação |

## 2. Jornadas ponta a ponta

### Compra de item conhecido

Estoque identifica item → Compras recebe produto preenchido → fornecedor e histórico são sugeridos → Monitoramento acompanha respostas → Aprovações decide → Compras executa → Estoque atualiza preço e histórico.

### Compra de mercado aberto

Usuário descreve necessidade → Koda ou Compras entende → TI fornece compatibilidade quando aplicável → Compras pesquisa e normaliza opções → Aprovações escolhe → Compras executa → TI ou Estoque recebe o resultado.

### Proposta até produção

Monitoramento identifica pedido → Propostas preenche cliente e template → documento é enviado → possível aceite é detectado → usuário confirma → Kanban recebe OP → Estoque verifica material → Compras trata faltas → Knowledge vincula anexos.

### Onboarding

Administração cria pessoa e sugere perfil → TI prepara máquina e acessos → Knowledge fornece guias → Dashboard mostra pendências → auditoria registra conclusão.

### OP bloqueada por material

Kanban identifica bloqueio → Estoque confirma saldo → Compras abre necessidade → Aprovações decide quando necessário → entrega remove bloqueio → BI mede impacto.

## 3. Regras de fronteira

- Compras não é dona do catálogo.
- Administração não mostra senhas em lista.
- TI não despeja JSON técnico para usuário comum.
- Koda não executa regra paralela fora do módulo de destino.
- Monitoramento não vira caixa de e-mail.
- n8n não decide e não escreve diretamente no banco.
- BI não altera estado operacional sozinho.
- Knowledge não é explorador de pasta.
- Dashboard não duplica todos os módulos.

## 4. Contratos que precisam existir cedo

Mesmo quando um módulo for desenvolvido depois, estes contratos precisam estar definidos:

- identidade de usuário e perfil;
- permissão por ação;
- Action Intent;
- evento operacional;
- vínculo entre entidades;
- histórico/auditoria;
- erro humano padronizado;
- arquivo/documento contextual;
- notificação e pendência;
- pesquisa e busca global.
