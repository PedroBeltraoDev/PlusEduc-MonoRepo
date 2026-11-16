# Sprint 10 — Versão release candidate (14/11/2026)

**Versão:** PlusEduc **1.0.0-rc.1** · Grupo 08 · executada e verificada em 11/11/2026

A release candidate é a versão que segue para validação, apresentação e entrega final. Nesta sprint o sistema foi
estabilizado sobre a Sprint 09: as pendências de autenticação registradas desde a Sprint 08 foram fechadas, os bugs
encontrados na revisão foram corrigidos, a interface perdeu os dados fictícios que restavam, o banco ganhou uma
verificação de consistência e a API, o modelo de dados e o README chegaram à versão final.

Todas as verificações rodaram com o sistema em execução (API + MongoDB + interface) contra um banco descartável
(`pluseduc_sprint10_eval`, cópia do `escola_db`). O `escola_db` só foi **lido** (verificação de consistência).

## Resultado em números

| Verificação | Casos | Resultado |
|---|---:|---|
| Suíte automatizada do backend (`pytest`) | 171 | 171 aprovados (eram 158 na Sprint 09) |
| Regressão funcional da API (`resultados/regressao_api.txt`): 92 casos da Sprint 09 + 12 novos | 104 | 104 aprovados |
| Navegação pela interface com Selenium (`resultados/regressao_navegacao.json`) | 91 | 91 aprovados |
| Validação pela interface (`resultados/regressao_validacao_ui.json`) | 15 | 15 aprovados |
| Revisão das telas finais (`resultados/revisao_interface.json`): 35 telas, 3 perfis, desktop e celular | 35 | nenhuma rolagem lateral; nenhum erro de console além do 403 esperado no login pendente |
| Consistência do banco (`resultados/banco_*.txt`) | 22 verificações | `escola_db`: 2 com erro e 1 aviso; depois do reparo (banco descartável): 0 erros, 1 aviso |
| Frontend: `npm run type-check` e `npm run build` | — | sem erros |

A regressão da API e as capturas de tela foram executadas antes de duas correções finais (matrícula ao criar aluno e
aviso duplicado no login); essas duas estão cobertas pela suíte `pytest` e pela verificação de tipos/build, refeitas
depois delas.

## 1. Sistema estável — correções e ajustes

### Pendências das sprints anteriores que foram fechadas

| Requisito | Antes | Agora |
|---|---|---|
| **RF01** — refresh token | Emitido, mas sem rota de renovação; com o token de acesso vencido, o usuário era mandado ao login | `POST /api/auth/refresh` troca o refresh token por um novo par; a interface renova sozinha quando o token vence ou a API responde 401. Token de acesso não renova e o refresh token continua sem abrir a API |
| **RF03** — troca de senha | Só pela recuperação por código; o botão "Alterar senha" das Configurações mostrava um aviso falso ("um link foi enviado") | `POST /api/auth/change-password` (exige a senha atual) e cartão "Alterar senha" nas Configurações do professor, do administrador e do aluno |
| **RF04** — aprovação de professor | O cadastro público ativava a conta na hora e dava acesso aos dados de todos os alunos | A conta nasce pendente: o login responde 403 com aviso (só para quem acertou a senha). O ADMIN aprova ou recusa em Configurações (`/api/teachers/pending`, `/approve`, `/reject`). O primeiro ADMIN é criado com `scripts/create_admin.py` |

### Bugs encontrados e corrigidos nesta sprint

| ID | Bug | Gravidade | Correção |
|---|---|---|---|
| RC-01 | ADMIN não conseguia criar turma pela tela: o formulário enviava "o professor logado" e o administrador não tem cadastro de professor (400) | alta | Para o ADMIN, o formulário pede o **professor responsável** |
| RC-02 | Turma aceitava professor excluído ou pendente; a edição aceitava até professor inexistente | média | Criar e editar turma exigem professor existente e ativo (400) |
| RC-03 | Aluno criado já com turma ficava fora da lista da turma (matrícula gravada só de um lado) | média | A criação grava a matrícula nos dois lados |
| RC-04 | A tela de Turmas imprimia no console do navegador nome, e-mail e data de nascimento dos alunos (53 mensagens de depuração), contra o RNF04 (LGPD) | média | Mensagens de depuração removidas |
| RC-05 | Configurações mostravam dados fixos ("Último acesso 15/04/2026", "Chrome - Windows 11", função "Professora" para qualquer pessoa) | baixa | Mostra o início real da sessão e a função correta |
| RC-06 | Falha ao baixar o PDF de uma atividade não avisava o usuário | baixa | Mensagem de erro na tela |
| RC-07 | Banco com 3 atividades e 3 respostas órfãs (turma, aluno ou atividade já inexistentes) | baixa | `check_database.py --repair` remove os órfãos (aplicado no banco descartável) |

O caso NAV-SS01 da Sprint 09 ("token inválido volta ao login") mudou de propósito: com a renovação de sessão, token
de acesso inválido + refresh token válido mantém o usuário na tela (NAV-SS01); com os dois inválidos a sessão termina
(NAV-SS02). O caso AUT-10 também mudou: o cadastro público de professor agora responde 202 e fica pendente.

## 2. Interface final

44 capturas em `evidencias/` (relação completa em `evidencias/manifest_rc.json`):

| Grupo | Arquivos | O que mostra |
|---|---|---|
| Fluxos novos | `c01` a `c13` | cadastro de professor pendente, login recusado com aviso, ADMIN aprovando, ADMIN criando turma, troca de senha (erro e sucesso) e login com a senha nova |
| Professor | `t01` a `t13` | dashboard, turmas, atividades, nova atividade, geração com IA, notas e frequência, relatórios, histórico, pesquisa, matérias, tópicos e configurações |
| Aluno | `a01` a `a08` | início, atividades, atividade sem gabarito, turma sem e-mail dos colegas, professores, notas, desempenho e configurações |
| Sessão | `n04`, `n05` | sessão renovada pelo refresh token e sessão encerrada |
| Modo escuro e celular | `e01`, `e02`, `m01` a `m06` | modo escuro e telas em 390 px, sem rolagem lateral |
| Documentação | `d01`, `d02` | Swagger (`/docs`) e ReDoc (`/redoc`) servidos pela API |

## 3. Banco de dados final

Estrutura final em [`../MODELO_DE_DADOS.md`](../MODELO_DE_DADOS.md): 10 coleções, diagrama de relacionamento,
chaves e índices (criados pela API ao iniciar), regras de integridade e débitos conhecidos. A Sprint 10 só
acrescentou campos (`users.pendingApproval`, `teachers.approval_status`, `approved_by`, `approved_at`), então
nenhum banco existente precisa de migração.

`PlusEduc-BE-Python/scripts/check_database.py` faz 22 verificações (referências entre coleções, duplicidades, faixas
de valores, senhas em bcrypt e índices). No `escola_db` (somente leitura) encontrou:

* **REF-09** — 3 atividades de março e abril apontando para uma turma e um aluno que não existem mais;
* **REF-10** — 2 respostas de aluno a atividades que não existem mais;
* **DOM-04** (aviso) — um professor com 12 turmas ativas, acima do limite de 5 (dado anterior à regra).

Com `--repair` no banco descartável sobram 0 erros (o aviso continua: a decisão sobre essas turmas é da escola).

## 4. APIs documentadas

| Onde | Conteúdo |
|---|---|
| [`../API.md`](../API.md) | 99 rotas em 18 grupos: autenticação, perfis, formato de erro, 7 exemplos com `curl`, parâmetros, corpos, respostas e todos os esquemas |
| `/docs` e `/redoc` (com a API em execução) | Swagger e ReDoc em português, com o perfil exigido em cada rota e o botão **Authorize** |
| [`../api/openapi.json`](../api/openapi.json) | esquema OpenAPI 3.1 importável no Postman ou Insomnia |

A documentação é gerada do código (`scripts/export_api_docs.py`) e `tests/test_openapi_docs.py` reprova o build se
alguma rota ficar sem resumo, grupo ou perfil, ou se o perfil documentado divergir da matriz de permissões.

## 5. README atualizado

[`../../README.md`](../../README.md): nome e descrição, objetivo, equipe, tecnologias, requisitos, instalação e
configuração, banco de dados (MongoDB, administrador, dados de demonstração e verificação), execução, testes,
documentação da API e estrutura do projeto. Repositório: <https://github.com/PedroBeltraoDev/PlusEduc-MonoRepo>.

## Pendências e próximos passos

| Pendência | Situação | Plano |
|---|---|---|
| Predição de risco, agrupamento por perfil e otimização de grupos de reforço (RF19, RF21, RF22) | não implementados | Sprint 11: modelo de risco com scikit-learn sobre notas, frequência e lacunas, exibido no painel do aluno; agrupamento K-Means se houver tempo; a otimização fica registrada como trabalho futuro |
| Escopo de dados por turma (qualquer professor vê e lança notas em qualquer turma) | não implementado | decisão de produto: manter assim (coordenação única) ou restringir por `subjectTeachers` |
| Integração contínua | não implementada | cerca de 40 testes dependem de dados já existentes no banco; é preciso um seed mínimo próprio para os testes antes de ligar o GitHub Actions |
| Dados antigos no `escola_db` (atividades e respostas órfãs, professor com 12 turmas) | identificados | rodar `check_database.py --repair` após backup e redistribuir as turmas antes da gravação dos vídeos |
| Speedup de 4× (RNF07) | não atingido | registrado na Sprint 08; sem mudança |

Sprint 11 (21/11): documentação final, roteiro de demonstração e ensaio. Sprint 12 (28/11): versão congelada para os vídeos.

## Como reproduzir

Com o MongoDB local, de dentro de `PlusEduc-BE-Python` (`PY` = `.venv\Scripts\python.exe`):

```powershell
$PY ..\docs\sprint-08\scripts\clonar_banco.py pluseduc_sprint10_eval      # cópia descartável do escola_db
$env:PLUSEDUC_EVAL_PASSWORD = "<senha de teste>"; $env:PLUSEDUC_EVAL_DB = "pluseduc_sprint10_eval"
$PY ..\docs\sprint-08\scripts\preparar_usuarios.py
$env:MONGODB_DATABASE = "pluseduc_sprint10_eval"; $env:PLUSEDUC_ADMIN_PASSWORD = $env:PLUSEDUC_EVAL_PASSWORD
$PY scripts\create_admin.py --email coordenacao@pluseduc.local --name "Coordenação Pedagógica"
# API em :8093 e interface em :5193 (VITE_DEV_PROXY_TARGET=http://127.0.0.1:8093), ambas com MONGODB_DATABASE acima
$PY ..\docs\sprint-10\scripts\regressao_api.py http://127.0.0.1:8093 pluseduc_sprint10_eval saida.json
python ..\docs\sprint-10\scripts\regressao_ui.py testes_navegacao.py saida_nav.json      # Chrome + Selenium
python ..\docs\sprint-10\scripts\regressao_ui.py testes_validacao_ui.py saida_val.json
python ..\docs\sprint-10\scripts\capturas_rc.py
$PY scripts\check_database.py --database escola_db                                      # somente leitura
```
