# Estado público do projeto

## Classificação

O Portal Vesper é uma **implementação de portfólio e referência técnica**. O repositório demonstra arquitetura, produto e engenharia em um domínio corporativo amplo, mas não deve ser interpretado como uma implantação pronta para uso empresarial sem homologação adicional.

## Matriz de maturidade

| Módulo | Backend | Frontend | Integração | Estado |
|---|---:|---:|---:|---|
| Autenticação e RBAC | Avançado | Funcional | Local | Base avançada |
| Administração | Avançado | Avançado | Interna | Base avançada |
| Kanban | Avançado | Avançado | WebSocket/eventos | Base avançada |
| TI / Help Desk | Avançado | Avançado | Importadores e cofre | Base avançada |
| Chat | Funcional | Avançado | WebSocket | Base funcional |
| Aprovações | Funcional | Funcional | Eventos/notificações | Base funcional |
| Estoque e catálogo | Avançado | Avançado | Importação e histórico | Avançado |
| Compras | Avançado em partes | Avançado em partes | Pesquisa, e-mail e worker condicionais | Parcial avançado |
| Dashboard | Funcional em partes | Funcional | Consolidação parcial | Parcial |
| Propostas | Inicial | Protótipo | Não concluída | Protótipo |
| Arquivos / Knowledge | Parcial | Parcial | Storage local | Parcial |
| Automações / n8n | Callbacks e ponte | Monitoramento parcial | Templates | Parcial |
| BI / Monitoramento | Contratos iniciais | Referência visual | Não consolidada | Planejado/parcial |
| Tauri Desktop | Estrutura inicial | Shell parcial | Coleta futura | Parcial |

## Validado no repositório

- estrutura modular de backend e frontend;
- migrações Alembic;
- autenticação, permissões e sessões;
- eventos, Action Intents e notificações;
- testes automatizados em múltiplos domínios;
- lint, compilação e build configurados no CI;
- headers de segurança e validações de ambiente;
- exclusão de uploads, bancos e segredos da distribuição pública.

## Dependente de ambiente

- PostgreSQL, Redis, MinIO, n8n e SearXNG;
- SMTP/IMAP e contas monitoradas;
- APIs de pesquisa e IA;
- conectores de catálogos e lojas;
- coleta de inventário de máquinas;
- dados legados e arquivos de empresa.

## Não comprovado como produção

- capacidade, disponibilidade e recuperação sob carga real;
- operação multiempresa;
- backup e restauração em ambiente gerenciado;
- compliance formal ou certificação;
- entrega real de e-mails e pedidos comerciais;
- segurança ofensiva independente;
- cobertura E2E de todas as jornadas.

## Critérios para uma release de produção

1. ambiente de homologação isolado;
2. segredos em gerenciador dedicado;
3. cookies seguros, HTTPS, CORS e CSP revisados;
4. migrations testadas em upgrade e rollback;
5. backup e restauração comprovados;
6. testes E2E dos fluxos críticos;
7. análise de dependências e pentest;
8. logs sem dados sensíveis;
9. monitoramento e alertas;
10. revisão de permissões por perfil.
