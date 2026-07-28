# Estoque & Catálogo

![Referência visual do Estoque & Catálogo](../assets/references/stock-catalog-light.webp)

> Esta é a principal referência de densidade e organização do Portal. Os valores da imagem são ilustrativos; o banco real define produtos, saldos, fornecedores e preços.

## Missão

Ser o Google interno de produtos, códigos, variações, saldos, fornecedores, preços e histórico.

## Fontes

- Cybersul: código, descrição, unidade, saldo, custo, NCM, grupo e status;
- Compras Nova: estrutura comercial, variação, fornecedor, contato, oferta e histórico;
- atualização manual autorizada;
- resultado de compras;
- evidências.

O PostgreSQL é a fonte de consulta comum. Excel e rede só entram por importação e sincronização.

## Identidade do item

A identidade deve considerar:

- origem;
- aba e caminho;
- família;
- produto;
- variação;
- especificação;
- medida;
- código;
- bloco de origem.

Nunca fundir itens apenas porque a descrição principal é igual.

## Busca

Encontrar por:

- código;
- nome;
- erro de digitação;
- apelido;
- medida equivalente;
- especificação;
- fornecedor;
- NCM;
- grupo;
- descrição antiga;
- equivalente.

Exemplos: tubo 1.1/2, 38,1 mm, 9,53 mm, Atuador DA100, Papel Velumoid e Bico Conemang.

## Estrutura visual

- cabeçalho compacto;
- indicadores úteis;
- famílias e categorias à esquerda;
- busca e lista no centro;
- drawer do item à direita;
- abas de detalhes, variações, fornecedores e histórico;
- ação principal `Cotar Produto`;
- filtros e paginação;
- alertas visíveis sem poluição.

## Regras críticas

- variações reais são itens separados;
- fornecedor nunca entra no nome;
- Preço é principal quando existir;
- Valor Final é metadado;
- total, média e fórmula não viram oferta;
- atualizar preço afeta somente item e fornecedor corretos;
- reprocessamento preserva histórico manual e evidências;
- item inativo não aparece na busca comum;
- nenhum Excel é lido durante busca ou navegação.

## Inteligência

- estoque baixo;
- item sem fornecedor;
- preço antigo;
- fornecedor único;
- equivalente;
- demanda futura de OP;
- compra já em andamento;
- quantidade sugerida;
- promoção de compra avulsa para item recorrente.

## Integrações

- abre Compras preenchido;
- informa disponibilidade ao Kanban;
- recebe preço vencedor de Compras;
- usa documentos do Knowledge;
- envia eventos ao Dashboard e BI.

## Performance

- tela inicial em até 1 segundo no ambiente alvo;
- busca após debounce em até 300 ms;
- drawer em até 500 ms;
- índice persistente;
- cache invalidado por evento;
- paginação e virtualização quando necessário.

## Não considerar pronto se

- variações se misturarem;
- um drawer mostrar preço de item irmão;
- fornecedor virar produto;
- produto com preço aparecer como sem preço;
- busca depender de Excel;
- Cotar Produto não levar dados reais para Compras.

## Critério Visão Vesper

A pessoa encontra e entende o item mais rápido que no Excel e inicia a próxima ação sem redigitar dados.
