# Administração

![Referência visual da Administração](../assets/references/administration-light.webp)

> A imagem define o padrão desejado de lista compacta, navegação interna e criação guiada. E-mail, fotos e valores mostrados são ilustrativos; o produto segue as regras abaixo.

## Missão

Permitir que Admin e Messias gerenciem pessoas, acessos, segurança e políticas em linguagem humana.

## Escopo

- usuários;
- perfis;
- permissões por módulo e ação;
- acesso por quadro;
- Cofre e ações especiais;
- contas monitoradas autorizadas;
- sessões;
- auditoria;
- políticas e configurações.

Não pertence à Administração:

- inventário detalhado de TI;
- senha exposta em lista;
- produtos;
- cotações;
- propostas;
- arquivos do NAS.

## Tela principal

Navegação interna:

- Usuários;
- Perfis;
- Acessos;
- Contas monitoradas;
- Auditoria;
- Configurações.

A lista de usuários mostra somente:

- nome;
- login;
- função/setor;
- perfil principal;
- status;
- resumo humano de acesso;
- ações.

Sem UUID, código interno, `permission_key`, payload ou timestamp bruto.

## Criação de usuário em três etapas

### 1. Dados da pessoa

- nome;
- nome de usuário;
- função/setor;
- senha inicial ou gerar senha;
- ativo ou ainda não.

E-mail é opcional.

A política de senha é configurável. A interface não deve impor regra arbitrária diferente do backend.

### 2. Perfil sugerido

Perfis iniciais:

- usuário comum;
- Compras;
- Produção;
- TI;
- Aprovador;
- Diretoria;
- Admin;
- personalizado.

O Portal sugere permissões e explica o efeito.

O Chat é global por padrão e não deve aparecer como ajuste comum.

Ajustes avançados ficam recolhidos:

- módulo adicional;
- ação crítica;
- quadro específico;
- Cofre;
- aprovação;
- importação;
- conta monitorada;
- duração temporária.

### 3. Revisão

Exemplo de resumo:

> Um comprador poderá criar cotações, consultar Estoque e criar pedidos internos. Não poderá aprovar pedidos nem acessar o Cofre.

Botões: Voltar e Criar usuário.

Após criar, mostrar sucesso explícito e a próxima ação possível.

## Edição e ciclo da pessoa

Drawer com:

- Resumo;
- Acessos;
- Segurança;
- Sessões;
- Histórico.

### Onboarding

Sugere conta, módulos, máquina, acessos e tarefas.

### Mudança de função

Compara acesso atual com o recomendado e mostra o que será adicionado ou removido.

### Férias ou substituição

Acesso temporário com expiração e responsável substituto.

### Desligamento

- encerrar sessões;
- bloquear acessos;
- redistribuir cards, chamados e aprovações;
- revisar contas monitoradas;
- preservar histórico;
- sugerir rotação de credenciais compartilhadas.

## UX obrigatória

- sem hero grande;
- criação guiada, não modal gigante;
- erro dentro da etapa atual;
- dados preservados em erro;
- voltar sem perder informação;
- sucesso explícito;
- perfil explicado em linguagem humana;
- tema claro e escuro equivalentes.

## Segurança e auditoria

- autorização real no backend;
- proteção especial do perfil Messias;
- confirmação para acesso crítico;
- nenhuma senha em log;
- toda alteração de acesso registra quem, quando, antes, depois e justificativa.

## Não considerar pronto se

- ainda houver `[object Object]`;
- erro aparecer atrás do modal;
- usuário precisar marcar dezenas de permissões sem sugestão;
- a UI mostrar códigos técnicos;
- desativar alguém não revisar sessões e responsabilidades;
- tema claro esconder texto ou estado.

## Critério Visão Vesper

Admin escolhe a pessoa e a função; o Portal sugere acessos, explica o efeito, confirma e registra tudo.
