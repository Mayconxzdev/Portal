# Padrões de UX e Interface — Portal Vesper

## 1. Objetivo

A interface deve permitir que uma pessoa leiga conclua a tarefa sem entender a arquitetura do sistema.

O módulo Estoque & Catálogo é referência de **densidade, foco e aproveitamento de espaço**, mas seu layout não deve ser copiado literalmente para todos os módulos.

## 2. Princípios

- mostrar primeiro o essencial;
- uma ação principal por contexto;
- reduzir campos e cliques;
- reaproveitar dados;
- progressive disclosure;
- detalhes em drawer;
- formulário longo em etapas;
- feedback no local da ação;
- linguagem humana;
- consistência entre temas;
- nenhuma informação útil escondida por baixo contraste.

## 3. Tela operacional

Evitar:

- hero grande;
- mascote ocupando área de trabalho;
- cards decorativos;
- texto institucional repetido;
- dez botões competindo;
- espaço vazio que empurra a tarefa para baixo.

Preferir:

- cabeçalho compacto;
- busca e ações no topo;
- resumo pequeno;
- área operacional ocupando a maior parte da tela;
- drawer para detalhe;
- filtros úteis;
- estados claros.

## 4. Tema claro e escuro

Ambos devem possuir:

- contraste de texto;
- bordas visíveis;
- ícones legíveis;
- estados de erro, sucesso e aviso equivalentes;
- placeholders visíveis;
- foco do teclado;
- chips e badges legíveis;
- elementos desabilitados identificáveis.

Nunca usar uma cor que funcione apenas sobre fundo escuro.

## 5. Formulários

### Quando usar etapas

Usar stepper quando houver grupos mentais diferentes ou muita informação.

Exemplo de usuário:

1. Dados básicos.
2. Perfil e acessos sugeridos.
3. Revisão e criação.

Ajustes avançados podem ficar dentro da segunda etapa, recolhidos por padrão.

### Regras

- não apagar campos após erro;
- erro dentro do modal ou drawer;
- erro perto do campo;
- resumo no topo do contexto;
- sucesso explícito;
- voltar sem perder dados;
- confirmação antes de ação sensível;
- campos técnicos escondidos.

## 6. Listas e tabelas

Mostrar o que ajuda a decidir.

Exemplo de usuários:

- nome;
- login;
- função;
- perfil;
- status;
- ações.

Não mostrar UUID, código interno ou timestamp bruto quando uma frase humana resolve.

## 7. Drawers e modais

- modal: decisão curta, criação guiada ou confirmação;
- drawer: detalhe e edição contextual;
- página: operação principal;
- não usar modal gigante com rolagem excessiva;
- não mostrar erro no fundo da página quando o modal está aberto;
- foco e teclado devem funcionar;
- fechar exige confirmação se houver alterações não salvas.

## 8. Estados

Toda tela precisa de:

- loading;
- vazio;
- erro;
- sucesso;
- sem permissão;
- indisponível;
- sincronizando;
- aguardando confirmação.

O estado deve dizer o que aconteceu e qual é a próxima ação.

## 9. Linguagem

Usar:

- “Pode criar cotações”;
- “Sem acesso ao Cofre”;
- “Aguardando resposta”;
- “Encontramos 5 opções”.

Evitar:

- `permission_key`;
- `payload`;
- `source`;
- `raw_data`;
- `role_id`;
- `Item UUID`;
- `Usuário #12`.

## 10. Koda

Koda aparece quando ajuda:

- estado vazio;
- sugestão;
- preview;
- explicação;
- ação contextual.

Não repetir mascote ou banner grande em todas as telas.

## 11. Busca

- aceitar erro de digitação;
- sugerir durante digitação;
- destacar o motivo do resultado;
- agrupar resultados;
- permitir abrir ação;
- não criar dados automaticamente durante busca;
- indicar quando resultado é exato, semelhante ou histórico.

## 12. Responsividade

O Portal é desktop-first, mas deve funcionar em larguras menores sem esconder ação importante.

- filtros podem recolher;
- painel lateral pode virar drawer;
- tabela pode virar lista;
- botões críticos permanecem visíveis;
- modo TV não exibe navegação do Portal.

## 13. Referências visuais canônicas

Cada módulo possui uma imagem em `assets/references/` e uma seção visual no documento correspondente em `modules/`.

A implementação deve:

- preservar o shell global;
- atingir densidade e clareza equivalentes;
- usar a imagem para hierarquia e composição;
- usar o documento para regra de negócio;
- substituir todo dado ilustrativo por dado real;
- não implementar botão ou métrica sem backend e permissão;
- validar tema escuro com a mesma qualidade do tema claro.

Consulte `VISUAL_REFERENCE_GUIDE.md` antes de redesenhar uma página.
