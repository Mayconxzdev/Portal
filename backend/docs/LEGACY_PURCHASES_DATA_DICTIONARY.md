# LEGACY_PURCHASES_DATA_DICTIONARY.md

## 1. Dicionário de Dados de Compras Legados

A tabela abaixo define os campos identificados na planilha de compras legadas e no banco SQLite de cotações, com seu tipo detectado, destino mapeado e nível de confiança:

| Fonte | Aba / Tabela | Coluna / Campo | Tipo Detectado | Destino Proposto | Confiança | Observações |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Planilha | Chapas e Insumos | Código | TEXT | `product_items.sku` | Alta | Usado como chave única do produto |
| Planilha | Chapas e Insumos | Material | TEXT | `product_items.name` | Alta | Nome descritivo do material |
| Planilha | Chapas e Insumos | Grupo/Categoria | TEXT | `product_items.category` | Alta | Categoria para Kanban de Produção |
| Planilha | Chapas e Insumos | Preço Referência (R$) | NUMERIC | `purchase_price_reference.current_price` | Alta | Preço base de cotação |
| Planilha | Fornecedores | Empresa | TEXT | `people.name` | Alta | Razão social ou nome fantasia |
| Planilha | Fornecedores | CNPJ | TEXT | `people.document_number` | Alta | CNPJ único normalizado |
| Planilha | Fornecedores | E-mail | TEXT | `person_contacts.value` | Alta | Contato de e-mail |
| Planilha | Fornecedores | Telefone | TEXT | `person_contacts.value` | Alta | Contato telefônico |
| Planilha | Histórico de Cotações | Data | DATE | `purchase_price_history.purchase_date` | Alta | Data de fechamento da compra |
| Planilha | Histórico de Cotações | Preço Unitário (R$) | NUMERIC | `purchase_price_history.price_paid` | Alta | Preço unitário pago de fato |
| Planilha | Histórico de Cotações | Variação % | NUMERIC | `purchase_price_update_suggestions.pct_variation` | Alta | Percentual de variação de mercado |
| Planilha | Histórico de Cotações | Evidência/Anexo | TEXT | `purchase_price_history.evidence_file_id` | Média | Nome físico do arquivo proposta no NAS |
| SQLite | local_suppliers | local_supplier_id | INTEGER | N/A (Substituído por UUID) | Alta | Chave primária antiga do SQLite |
| SQLite | local_suppliers | obs | TEXT | `suppliers.notes` | Alta | Observações cadastrais |
| SQLite | local_supplier_items | serv_corte | BOOLEAN | `suppliers.provides_cutting` | Alta | Flag de serviço adicional |
