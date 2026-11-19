# Documentação final — PlusEduc

Índice da documentação consolidada na Sprint 11. Todos os documentos descrevem a versão da branch `main`
(1.0.0-rc.1 com a atualização de segurança); onde a implementação mudou em relação ao planejado, vale o que está aqui.

## Para usar e operar

| Documento | Conteúdo |
|---|---|
| [Manual do Usuário](MANUAL_DO_USUARIO.md) | uso do sistema por professor, administrador e aluno, com telas, passo a passo, mensagens e perguntas frequentes |
| [Manual Técnico](MANUAL_TECNICO.md) | arquitetura, tecnologias, módulos, banco, instalação, variáveis de ambiente, execução, APIs, IA e processamento, segurança, testes e manutenção |
| [Roteiro de demonstração](DEMO_AND_PRESENTATION.md) | preparação do banco de demonstração, roteiro de 10 minutos e checklist |
| [Dados de demonstração](DEMO_DATA_POPULATION.md) | seed reproduzível do ambiente local |

## Requisitos, casos de uso e regras

| Documento | Conteúdo |
|---|---|
| [Plano de projeto](PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md) | tema, problema, objetivos, público-alvo, requisitos funcionais e não funcionais, **casos de uso** (atores, tabela e diagrama), backlog e cronograma com o escopo real de cada sprint |
| [Situação dos requisitos](REQUISITOS_STATUS.md) | situação real de cada RF e RNF (concluído, parcial, não implementado) com a evidência |
| [Regras de negócio](REGRAS_DE_NEGOCIO.md) | RN01 a RN44, onde cada uma é aplicada e como é verificada |

## Arquitetura, dados e API

| Documento | Conteúdo |
|---|---|
| [Arquitetura](ARQUITETURA.md) | diagramas de componentes e camadas, segurança de uma requisição, frontend, execução e build |
| [Modelo de dados](MODELO_DE_DADOS.md) | 11 coleções, campos, relações, chaves, índices, diagrama e regras de integridade |
| [API](API.md) e [`api/openapi.json`](api/openapi.json) | 100 rotas com perfil de acesso, parâmetros, corpos, respostas e exemplos (gerados do código) |
| [Atualização de segurança e Ultra Motion](ATUALIZACAO_SEGURANCA_E_ULTRA_MOTION.md) | mudanças da revisão de segurança, migração de dados e sistema de animações |

## Registro das sprints (com evidências e scripts)

| Pasta | Conteúdo |
|---|---|
| [`sprint-08/`](sprint-08/README.md) | permissões verificadas por perfil, regras de negócio revisadas, benchmark OpenCL |
| [`sprint-09/`](sprint-09/README.md) | testes completos (API, navegação, validação) e 12 bugs corrigidos |
| [`sprint-10/`](sprint-10/README.md) | release candidate e, em [`sprint-10/entrega/`](sprint-10/entrega/README.md), a verificação da versão entregue |
| [`sprint-11/`](sprint-11/README.md) | revisão completa do código, correções, organização do repositório e manuais |

Os documentos das Sprints 01 a 07 (plano, documento técnico e módulos) foram entregues em PDF no Teams; o conteúdo
deles que continua válido está consolidado nos documentos acima.
