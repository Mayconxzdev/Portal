# Guia Canônico de Referência Visual

## 1. Objetivo

As imagens em `assets/references/` definem a **direção visual e operacional** esperada para cada módulo em tema claro.

Elas devem orientar:

- densidade de informação;
- hierarquia;
- aproveitamento de espaço;
- foco na tarefa;
- distribuição entre lista, área principal e drawer;
- clareza das ações;
- consistência do shell global.

Elas não são mock de banco, contrato de API nem prova de que o módulo existe.

## 2. O que deve ser reproduzido

- cabeçalho compacto;
- sidebar global consistente;
- título e descrição curta;
- ações principais no topo direito;
- ausência de hero grande em telas operacionais;
- área de trabalho ocupando a maior parte da tela;
- cards com função real;
- contraste alto no tema claro;
- bordas suaves e visíveis;
- tipografia legível;
- uso moderado de cor para indicar estado;
- drawer ou painel lateral para detalhe;
- uma ação principal evidente;
- linguagem humana.

## 3. O que não deve ser copiado cegamente

Os nomes, valores, pessoas, quantidades, logos, datas e exemplos das imagens são ilustrativos. Não devem ser transformados em dados fake no ambiente real.

Também não copiar:

- menus laterais inconsistentes entre imagens;
- rótulos que não existam na visão canônica;
- métricas sem fonte real;
- funcionalidades sem backend ou contrato definido;
- integrações que ainda não existem;
- campos que exponham segredo ou informação técnica.

A imagem define **forma e prioridade visual**, enquanto o documento do módulo define **regra e comportamento**.

## 4. Shell global obrigatório

Todos os módulos devem compartilhar:

- mesma sidebar;
- mesma barra superior;
- busca global;
- indicador de ambiente/conectividade;
- Supervisor IA/Koda conforme permissão;
- tokens de cor;
- escala de espaçamento;
- botões, campos, badges, tabelas e drawers consistentes;
- comportamento equivalente em tema claro e escuro.

Não criar um Portal diferente dentro de cada módulo.

## 5. Linguagem visual

### Cor

- roxo: ação primária ou inteligência;
- verde: sucesso, disponível, aprovado;
- amarelo/laranja: atenção, prazo, informação pendente;
- vermelho: risco, erro, bloqueio;
- azul: informação e navegação contextual.

Cor nunca deve ser o único meio de comunicação. Usar texto e ícone.

### Densidade

A referência de Estoque & Catálogo é o padrão de densidade:

- cabeçalho curto;
- resumo compacto;
- busca e operação visíveis sem rolagem;
- detalhe lateral;
- poucos espaços vazios inúteis.

Cada módulo adapta essa densidade ao próprio trabalho.

## 6. Imagem por módulo

| Módulo | Arquivo |
|---|---|
| Dashboard / Hoje | `assets/references/dashboard-today-light.webp` |
| Administração | `assets/references/administration-light.webp` |
| Estoque & Catálogo | `assets/references/stock-catalog-light.webp` |
| Compras | `assets/references/purchases-light.webp` |
| Aprovações | `assets/references/approvals-light.webp` |
| Propostas | `assets/references/proposals-light.webp` |
| Kanban / Produção / Projetos | `assets/references/kanban-production-projects-light.webp` |
| TI / HelpDesk / Cofre / Acessos | `assets/references/it-helpdesk-vault-access-light.webp` |
| Knowledge / Arquivos | `assets/references/knowledge-files-light.webp` |
| Chat / Koda | `assets/references/chat-koda-light.webp` |
| Central de Monitoramento | `assets/references/monitoring-light.webp` |
| Automações / n8n | `assets/references/automations-n8n-light.webp` |
| BI / Relatórios | `assets/references/bi-reports-light.webp` |

## 7. Validação visual obrigatória

Para cada módulo:

- comparar lado a lado com a referência;
- validar tema claro e escuro;
- validar em resolução desktop real;
- verificar conteúdo inicial sem rolagem excessiva;
- confirmar que ação principal está evidente;
- confirmar que texto secundário permanece legível;
- validar loading, vazio, erro, sucesso e sem permissão;
- verificar que drawer não esconde ação importante;
- confirmar que não há hero ou mascote consumindo área operacional.

## 8. Regra final

A implementação deve ficar **tão clara, compacta e operacional quanto a referência**, mas nunca sacrificar regra real, acessibilidade ou segurança para imitar uma imagem.
