# Segurança e Governança — Portal Vesper

## 1. Princípios

- privilégio mínimo;
- negação por padrão;
- validação no backend em toda ação;
- separação entre visualizar, criar, editar, executar, aprovar e administrar;
- confirmação proporcional ao risco;
- auditoria obrigatória de ações sensíveis;
- segredos fora de logs, telas comuns e automações;
- dados técnicos ocultos do usuário comum.

## 2. Autenticação e sessão

- JWT ou sessão equivalente com cookie HttpOnly;
- `Secure=True` em produção;
- política de SameSite adequada;
- renovação e expiração controladas;
- encerramento de sessão;
- possibilidade de revogar sessões;
- proteção adicional contra CSRF em operações sensíveis;
- erros de autenticação sem revelar detalhes internos.

A criação de usuário não deve exigir e-mail quando a regra de negócio não exigir. A senha inicial não deve possuir regra arbitrária hardcoded na interface. Recomenda-se geração segura, troca posterior e política configurável.

## 3. Autorização

O Chat pode ser global, mas as ações originadas nele respeitam a permissão do módulo de destino.

Permissões precisam existir no backend para:

- módulo;
- ação;
- quadro;
- registro quando necessário;
- aprovação;
- importação;
- atualização de preço;
- revelação de segredo;
- conta monitorada;
- execução de automação.

Ocultar botão no frontend não é controle de acesso.

## 4. Administração

Ações críticas:

- criar e desativar usuário;
- redefinir acesso;
- copiar perfil;
- liberar Cofre;
- alterar alçada;
- autorizar conta monitorada;
- encerrar sessões;
- conceder acesso temporário.

O Portal deve mostrar preview humano e registrar histórico.

## 5. Cofre e segredos

- criptografia forte em repouso;
- chave fora do banco;
- mascaramento por padrão;
- revelação temporária;
- permissão explícita;
- auditoria de revelação;
- nenhuma senha em listagem;
- nenhum segredo em screenshot, log, JSON exportado ou callback;
- rotação quando pessoa ou contexto mudar.

## 6. Contas monitoradas e e-mail

- somente Admin/Messias autoriza;
- credenciais ficam no Cofre;
- permissões de ler e enviar são separadas;
- pastas monitoradas são configuráveis;
- conteúdo recebido é tratado como não confiável;
- anexos passam por validação;
- envio real exige preview e confirmação;
- ações detectadas não são executadas automaticamente.

## 7. Arquivos

- nome sanitizado;
- tipo e tamanho validados;
- executáveis bloqueados;
- hash registrado;
- acesso autorizado pelo contexto;
- preview seguro;
- conteúdo de documentos externos não pode virar instrução do sistema;
- versão e origem preservadas.

## 8. Integrações e n8n

- n8n usa APIs autenticadas;
- n8n não escreve diretamente no banco;
- callbacks possuem assinatura, timestamp e proteção contra replay;
- idempotência;
- retry controlado;
- segredo em credencial protegida;
- retorno registrado no Portal;
- workflow técnico oculto do usuário comum.

## 9. Koda e IA

- não inventar dado;
- citar a origem interna quando possível;
- mostrar suposição;
- pedir informação faltante;
- preview antes da ação;
- autorização validada pelo módulo;
- comandos sensíveis bloqueados ou confirmados;
- entrada externa tratada como conteúdo, não como instrução confiável.

## 10. Logs e auditoria

Registrar:

- autenticação relevante;
- falha de autorização;
- alteração de permissão;
- revelação de segredo;
- decisão de aprovação;
- envio;
- importação;
- execução de automação;
- mudança de preço;
- alteração de item;
- erro crítico de integração.

Não registrar:

- senha;
- token;
- conteúdo secreto;
- cookie;
- chave privada;
- documento sensível completo.

## 11. Produção

Antes de publicar:

- revisar CORS e CSRF;
- ativar cookies seguros;
- revisar segredos;
- validar backups;
- testar restauração;
- revisar permissões;
- confirmar migrations;
- executar testes;
- verificar logs sem dados sensíveis;
- validar tema e mensagens de erro;
- confirmar que mocks e envios fake não aparecem como produção.
