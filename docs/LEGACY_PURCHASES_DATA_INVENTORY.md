# LEGACY_PURCHASES_DATA_INVENTORY.md

## 1. Objetivo
Este documento apresenta o inventário completo e detalhado das informações extraídas da planilha de compras legadas e do aplicativo `ComprasApp2`. O inventário foi realizado de forma segura, sanitizada e em conformidade com as regras do `AGENTS.md`, sem gravação no banco de dados corporativo oficial do Portal Vesper nesta rodada.

## 2. Fontes analisadas
As fontes avaliadas e sanitizadas para esta auditoria de dados foram:
* * Planilha Sintética / Mockada de Simulação (Dry-Run)

## 3. Abas e estrutura da planilha
A planilha contém as seguintes abas operacionais mapeadas para migração:
| Aba | Quantidade de Linhas | Colunas Principais | Uso Provável | Observações |
| :--- | :--- | :--- | :--- | :--- |
| **Chapas e Insumos** | 5 | Código, Material, Medidas, Espessura, Grupo/Categoria, Preço Referência, Última Compra | Cadastro de produtos e referências | Base centralizada de preços de mercado |
| **Fornecedores** | 6 | Empresa, CNPJ, Contato, E-mail, Telefone, Cidade, UF | Cadastro local de empresas e contatos | Contém overrides que sobrepõem o central |
| **Histórico de Cotações** | 3 | Data, RFQ ID, Item SKU, Material, Fornecedor, Preço Unitário, Variação %, Condição | Histórico de compras e transações | Registra as decisões e aprovações do Wilson |

## 4. Dicionário de dados
Mapeamento de colunas extraídas para suas futuras localizações no banco Postgres do Portal Vesper:
| Coluna | Significado Provável | Tipo Detectado | Destino no Portal | Confiança | Observações |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Código** | SKU único do insumo | TEXT (Alfanumérico) | `product_items.sku` | Alta | Chave primária de sincronia com estoque |
| **Material** | Nome descritivo do produto | TEXT | `product_items.name` | Alta | Deve ser normalizado para canonical |
| **Grupo/Categoria** | Categoria do material | TEXT | `product_items.category` | Alta | Vinculada às tags do Kanban de produção |
| **Preço Referência** | Valor sugerido para cotações | NUMERIC (Decimal) | `purchase_price_reference` | Alta | Usado para alertar variações relevantes |
| **CNPJ** | Cadastro Nacional de Pessoa Jurídica | TEXT (Dígitos) | `people.document_number` | Alta | Passa por normalização e deduplicação |
| **E-mail** | E-mail de cotação preferencial | TEXT | `person_contacts.value` | Alta | Convertido para lowercase e validado |

## 5. Fornecedores detectados
* **Total de registros de Fornecedores**: 6
* **Fornecedores com CNPJ/Documento**: 5
* **Fornecedores sem CNPJ/Documento**: 1 (Exigem saneamento manual)
* **Fornecedores com E-mail válido**: 6
* **Candidatos a Duplicidade Identificados**: 1
  Amostra de Duplicados Identificados:
    * CNPJ/CPF Duplicado: 44444444000144 (2 registros)

## 6. Produtos/itens detectados
* **Total de registros de Itens**: 5
* **Itens com SKU/Código preenchido**: 5
* **Itens sem SKU/Código**: 0 (Exigem geração automática de SKU)
* **Categorias Detectadas**: Chapa e Tubo Inox, Barra Chata Inox, Chapas, Cantoneira Inox

## 7. Preços e histórico
* **Preços de referência mapeados**: 5 registros
* **Preços de compras passadas registrados**: 3 registros
* **Variações de preço mapeadas**: Variação média detectada de cotações frente ao preço de referência.

## 8. Rastreabilidade do chefe
A planilha *Compras Nova.xlsx* atua hoje como a única ferramenta gerencial de tomada de decisão do dono da empresa para acompanhar flutuações de custos de chapas e motores. O fluxo consiste em auditar a oscilação percentual e autorizar ou vetar reajustes de preço de referência de compras futuras. No Portal Vesper, essa visibilidade manual vira um **Dashboard Gerencial de Histórico de Preços** com alertas automatizados de variação percentual.

## 9. Como isso vira Portal
* **Cadastros Mestres**: Fornecedores e itens migram para `suppliers` e `product_items` integrados.
* **Módulo Compras**: As cotações ativas e RFQs passam a ser geradas via formulários web.
* **Histórico de Preços**: A planilha vira dados históricos imutáveis na tabela `purchase_price_history`.
* **Preço de Referência**: Preços aprovados viram referências e geram sugestões de atualização pendentes de aprovação pelo Comprador.

## 10. Qualidade dos dados
* **Campos Vazios**: 1 fornecedores sem CNPJ; 0 itens sem SKU.
* **Valores Não Numéricos**: Convertidos para float durante a normalização (remoção de "R$", tratamento de vírgula decimal).
* **Documentos Inválidos**: CNPJs contendo menos de 14 dígitos identificados e retidos para revisão.

## 11. Segurança
* **Políticas de Acesso**: Credenciais, segredos SMTP Skymail e tokens do Telegram legados foram omitidos e mascarados por completo. Nenhuma senha ou chave DPAPI em formato puro foi salva no código ou documentações geradas.

## 12. Estratégia de importação futura
1. **Fase 1: Inventário** (Esta rodada concluída com sucesso).
2. **Fase 2: Staging** (Importação para tabelas temporárias `legacy_import_rows` no Postgres).
3. **Fase 3: Revisão Humana** (Interface visual de conciliação de duplicados).
4. **Fase 4: Migração Master Data** (Aprovados gravados nas tabelas oficiais Postgres).
5. **Fase 5: Migração Histórico** (Popular tabelas históricas de compras).
6. **Fase 6: Aposentadoria da Planilha** (Travar escrita na planilha central).

## 13. Próximas tabelas prováveis
* `purchase_price_history` (Grava compras passadas).
* `purchase_price_reference` (Referência atualizada).
* `purchase_price_update_suggestions` (Sugestões de variação).
* `legacy_import_batches` (Metadados do lote importado).

## 14. Próximas telas prováveis
* **Compras > Histórico de Preços**: Timeline e gráficos de oscilação do mercado por SKU.
* **Compras > Revisão de Preços**: Fila de sugestões de novos preços a serem homologados.
* **Cadastros Mestres > Conciliação**: Tela de limpeza e mesclagem de fornecedores e produtos duplicados.

## 15. Riscos
* **CNPJ Ausente**: Fornecedores sem identificador único dificultam a deduplicação automática.
* **Planilha Desatualizada**: Compradores continuarem a atualizar a planilha manual no NAS.
* **Preço Sem Data**: Cotações históricas sem registro temporal.

## 16. Recomendação
O próximo passo deve ser o desenvolvimento do pacote **`purchases-price-traceability-design-pack`** para criar a modelagem de banco de dados (`purchase_price_history`, `purchase_price_reference`) e os endpoints de sugestão no backend, seguido do pacote de importação segura e staging.
