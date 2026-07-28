# Qualidade, Maturidade e Critérios de Aceitação

## 1. Três níveis de maturidade

### Pronto técnico

- compila;
- testes passam;
- API responde;
- banco e migration estão consistentes;
- tela abre.

### Pronto funcional

- usuário conclui uma tarefa real;
- dados reais;
- erros e permissões corretos;
- jornada completa;
- sem depender de mock.

### Pronto Visão Vesper

- reduz trabalho manual;
- entende contexto;
- sugere;
- preenche;
- mostra preview;
- confirma;
- executa;
- registra histórico;
- integra-se aos módulos relacionados;
- é melhor que o processo antigo.

Nunca usar “pronto” sem informar o nível.

## 2. Definition of Done global

Uma entrega só está concluída quando:

- regra de negócio validada;
- UX para leigo validada;
- tema claro e escuro validados;
- permissão backend validada;
- erro humano validado;
- estado vazio e loading validados;
- auditoria validada;
- integração validada;
- testes automatizados;
- jornada no navegador;
- sem mock parecendo produção;
- documentação canônica atualizada;
- sem regressão de performance relevante.

## 3. Validações técnicas

Backend:

- `pytest -q`;
- `ruff check app`;
- `python -m compileall -q app`;
- `alembic heads`;
- `alembic current`;
- checagem de migration quando aplicável.

Frontend:

- testes;
- lint;
- typecheck;
- build;
- console sem erros importantes.

## 4. Jornadas de navegador

Usar Playwright ou equivalente para:

- login;
- permissões;
- criação e edição;
- erro de validação;
- busca;
- modal/drawer;
- ação principal;
- confirmação;
- histórico;
- tema claro;
- tema escuro.

## 5. Performance

Validar com volume realista:

- busca;
- listas grandes;
- árvore;
- drawer;
- importação;
- sincronização;
- WebSocket;
- TV.

## 6. Evidências

Uma validação deve gerar:

- resultado dos testes;
- jornada executada;
- prints quando necessário;
- erro encontrado;
- correção;
- risco pendente.

## 7. Proibições

- declarar módulo pronto apenas por teste unitário;
- aceitar timeout como “sem erro de lógica” sem investigar estabilidade;
- esconder falha atrás de fallback genérico;
- validar com dado fake e chamar de produção;
- misturar documento histórico com especificação canônica;
- usar sprint ou PR como definição permanente de comportamento.

## 8. Revisão por módulo

Cada documento em `modules/` possui critérios próprios. A auditoria deve comparar:

- objetivo canônico;
- comportamento real;
- lacuna;
- risco;
- prioridade;
- evidência.

## 9. Aceitação visual por referência

Para módulos que possuem imagem canônica:

- comparar a implementação com a referência lado a lado;
- validar mesma prioridade de informação, não apenas cores;
- confirmar que a tarefa principal aparece sem rolagem excessiva;
- confirmar que não existe hero grande ou espaço decorativo;
- validar contraste no tema claro e escuro;
- verificar consistência do shell global;
- registrar divergências justificadas;
- impedir dados ilustrativos ou métricas fake.

A imagem não substitui teste funcional. Uma tela visualmente parecida sem jornada real continua incompleta.
