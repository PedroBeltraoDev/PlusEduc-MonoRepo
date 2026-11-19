# Sprint 11 — Preparação para entrega (21/11/2026)

**Versão:** PlusEduc 1.0.0-rc.1 (com a atualização de segurança) · Grupo 08 · executada em 19/11/2026

A Sprint 11 organizou e fechou a documentação e o código para a entrega final:

- dois manuais novos: [Manual do Usuário](../MANUAL_DO_USUARIO.md) e [Manual Técnico](../MANUAL_TECNICO.md);
- documentação consolidada, com índice em [`docs/README.md`](../README.md);
- revisão completa do código;
- repositório organizado.

A revisão encontrou e corrigiu **três defeitos de funcionamento** e removeu código, componentes e dependências sem uso.

Toda a verificação rodou contra bancos descartáveis (cópias do `escola_db`). O `escola_db` só foi lido.

## 1. Manuais e documentação final

| Documento | O que mudou nesta sprint |
|---|---|
| [`MANUAL_DO_USUARIO.md`](../MANUAL_DO_USUARIO.md) | **novo.** Apresentação, público-alvo, acesso e autenticação, telas, passo a passo dos fluxos de professor, administrador e aluno, mensagens e validações, perguntas frequentes. 35 imagens do sistema em execução |
| [`MANUAL_TECNICO.md`](../MANUAL_TECNICO.md) | **novo.** Arquitetura, tecnologias, módulos, banco, ambiente, instalação, variáveis de ambiente (sem credenciais), execução, APIs, componente de IA e processamento, segurança, testes e manutenção |
| [`REGRAS_DE_NEGOCIO.md`](../REGRAS_DE_NEGOCIO.md) | **novo.** RN01 a RN29 das Sprints 05 a 08, relidas contra o código, e RN30 a RN44 das Sprints 10 e 11, cada uma com a forma de verificação |
| [`README.md`](../README.md) (docs) | **novo.** Índice da documentação final |
| [`PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md`](../PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md) | casos de uso com a situação real (implementado, parcial, não implementado); UC19 a UC23 acrescentados; cronograma das Sprints 10 e 11 com o escopo real |
| [`ARQUITETURA.md`](../ARQUITETURA.md) | perfis e segurança atualizados (escopo do professor, limite de tentativas), módulos novos, desktop na `main`; o escopo por turma saiu de "fora do escopo" |
| [`REQUISITOS_STATUS.md`](../REQUISITOS_STATUS.md) | contagem de testes, RNF01 e backlog atualizados |
| [`DEMO_AND_PRESENTATION.md`](../DEMO_AND_PRESENTATION.md) | **reescrito.** Antes falava em 8 alunos e em OpenCL "fora do escopo", e trazia caminhos de uma máquina. Agora tem os números reais do banco, a preparação (backup, migração, reparo e criação do administrador), um roteiro de 10 minutos e o checklist |
| READMEs da raiz e do backend | testes, instalação com `requirements-dev.txt`, estrutura com o desktop e `motion/`, links dos manuais |

As imagens dos manuais vêm de dois roteiros: `scripts/capturas_manual.py` (fluxos completos, em `docs/manuais/imagens/`)
e as capturas da entrega da Sprint 10 (`docs/sprint-10/entrega/evidencias/`). O primeiro cria uma atividade de
demonstração, o aluno responde, o professor corrige e lança a nota, e o aluno vê o resultado. No fim, o roteiro remove
o que criou.

## 2. Revisão do código

| Verificação | Ferramenta | Resultado |
|---|---|---|
| Imports e variáveis sem uso no backend | `pyflakes` | 27 avisos em 18 arquivos → 0 |
| Código morto no backend | `vulture` + busca manual de cada nome | 15 funções e classes nunca chamadas, removidas: `require_admin` e `filter_activities` (sobra do `/api/admin`), `deactivate_by_email`, `insert_admin_user`, `unset_fields`, `add_student`, `remove_student`, `find_by_matricula`, `count_active`, `find_by_name_normalized`, `find_by_subject`, `GradeAverageResponse`, `classroom_id_not_in` e o pacote `app/models` (`StudentDocument` e `TeacherDocument`) |
| Arquivos sem uso no frontend | grafo de imports a partir de `main.tsx` | 43 componentes da biblioteca shadcn/ui copiada no início do projeto, que nenhuma tela usava, removidos (restaram 5) |
| Dependências sem uso | busca de cada pacote do `package.json` no código | 42 dependências removidas (Material UI, Emotion, 23 pacotes Radix, carrossel, calendário, formulários etc.). O lockfile caiu de 358 para 246 pacotes. A instalação limpa (`npm ci`) foi conferida com type-check e build |
| Tipagem | TypeScript estrito + busca de `any` | 5 `any` → 0 |
| Logs e depuração | busca de `print`, `console.log`, `TODO` | nenhum `print` na API; nenhum `console.log`, `debug` ou `TODO` na interface. Os `console.error` em blocos de erro foram mantidos |
| Informação sensível | busca no código e em **todo o histórico do Git** (72 commits) por chaves de API, URIs com senha, chaves privadas e segredos com valor | nada encontrado. O único achado é o modelo `JWT_SECRET={secret}` do instalador, sem valor real. `.env` fora do Git |
| Dependências do backend | leitura dos imports | `pytest` e `pypdf` só servem aos testes: passaram para o novo `requirements-dev.txt` |
| Fluxos de uso | revisão manual ao capturar as telas dos manuais | 3 defeitos encontrados (seção 3) |

Saldo no código-fonte da aplicação (backend e frontend): 4.732 linhas removidas e 161 acrescentadas (as correções da
seção 3). Fora essas correções, o comportamento não mudou.

## 3. Correções e melhorias

| ID | Problema encontrado | Gravidade | Correção |
|---|---|---|---|
| S11-01 | **Aluno cadastrado pela escola não conseguia entrar no portal.** A rota de liberação de acesso existia na API, mas nenhuma tela a usava; o autocadastro com o mesmo e-mail criava um **segundo registro de aluno**, fora da turma. | alta | Botão **Liberar acesso ao portal** no detalhe do aluno (Turmas), com a senha inicial definida pela equipe; a resposta de aluno informa `hasPortalAccess`; o autocadastro com o e-mail de um aluno da escola é recusado com orientação (409). Teste: `test_sprint11_regressions_real.py` |
| S11-02 | **Data de nascimento aparecia um dia antes** (14/08/2012 mostrado como 13/08/2012): `new Date("2012-08-14")` é meia-noite UTC, que no Brasil ainda é o dia anterior. | média | `formatDate` trata datas sem hora como data local (`parseDateValue`) |
| S11-03 | **PDF de atividade com adaptação para baixa visão** dizia "fonte ampliada", mas usava o tamanho normal. | média | Fonte 30% maior em todo o conteúdo do PDF quando a atividade tem essa adaptação. Teste confere os tamanhos dentro do PDF |
| S11-04 | Código morto, componentes e dependências sem uso | baixa | removidos (seção 2) |
| S11-05 | Dependências de teste no `requirements.txt` de execução | baixa | `requirements-dev.txt` |
| S11-06 | `ATTRIBUTIONS.md` citava Material UI (removido) e omitia bibliotecas em uso | baixa | atualizado |
| S11-07 | Documentação com informações antigas (8 h de token, desktop fora da `main`, escopo por turma como pendência, 8 alunos) | baixa | documentos revisados (seção 1) |

## 4. Verificação

| Conjunto | Resultado |
|---|---|
| `pytest` (backend) | **192 aprovados**: 190 + 2 testes novos (`resultados/testes_backend.txt`) |
| Regressão da API com o sistema em execução (`regressao_entrega.py`) | **111/111** (`resultados/regressao_api.txt`) |
| Navegação pela interface (Selenium) | **91/91** |
| Validação pela interface | **15/15** |
| Frontend | `type-check` sem erros; `build` ok; instalação limpa só com as 13 dependências diretas |
| Fluxo completo dos manuais | atividade criada → respondida → corrigida → nota lançada → vista pelo aluno; acesso ao portal liberado e login do aluno novo conferido |

## 5. Organização do GitHub

- **Estrutura:** `PlusEduc-BE-Python/` (API), `PlusEduc-UI/` (interface), `PlusEduc-Desktop/` (aplicativo Windows) e
  `docs/` (documentação, manuais e uma pasta por sprint com README, resultados, evidências e scripts).
- **README da raiz:** nome e descrição, objetivo, **equipe** (nomes, matrículas e papéis), tecnologias, requisitos,
  instalação, banco, execução, testes, API, estrutura, documentação e pendências.
- **Configuração:** `.env.example` no backend e na interface; `requirements.txt`, `requirements-dev.txt`,
  `requirements-compile.txt`, `package.json` e `package-lock.json` versionados.
- **`.gitignore`** cobre `.env`, `.venv`, `node_modules`, `dist`, caches, logs e chaves. Nenhum desses arquivos está no
  repositório.
- **Histórico:** 72 commits, no padrão `tipo(escopo): descrição`; cada sprint numa branch, integrada por pull request
  (PRs #11 a #16).
- **Branches:** 10 branches remotas já estão integradas à `main` e podem ser apagadas:
  `claude/elastic-williamson-a7d096`, `claude/entrega-sprint-10`, `claude/integra-correcao-geral-ultra-motion`,
  `claude/software-factory-project-plan-986915`, `claude/sprint-09-testes`, `claude/sprint-10-release-candidate-b2b088`,
  `feat/correcao-geral-ultra-motion`, `feat/nuitka-api-standalone`, `feat/nuitka-main-backend` e
  `parallel/opencl-radeon-rx580`. A limpeza fica para a equipe decidir.

## 6. Pendências e próximos passos

| Pendência | Situação | Próximo passo |
|---|---|---|
| Predição de risco, agrupamento por perfil e grupos de reforço otimizados (RF19, RF21, RF22) | não implementados | registrados como trabalho futuro no Manual Técnico (seção 10.4) |
| Banco de demonstração | sem administrador; migração e reparo ainda não aplicados | seguir a preparação de [`DEMO_AND_PRESENTATION.md`](../DEMO_AND_PRESENTATION.md) antes da gravação dos vídeos |
| Integração contínua e testes automatizados de frontend | não implementados | seed mínimo para os testes e GitHub Actions |
| Aplicativo de desktop | incluído, sem verificação do instalador | gerar e testar o instalador antes de decidir se entra na apresentação |
| Speedup de 4× (RNF07) | não atingido | registrado desde a Sprint 08 |
| Sprint 12 (28/11) | — | congelar a versão e gravar os vídeos |
| Entrega final (05/12) | — | vídeos (horizontal e vertical) e banca |

## 7. Como reproduzir

Com o MongoDB local, a partir de `PlusEduc-BE-Python` (`PY` = `.venv\Scripts\python.exe`), com a API em `:8093` e a
interface em `:5193` apontando para o banco de avaliação preparado por `docs/sprint-10/scripts/preparar_entrega.py`:

```powershell
$env:PLUSEDUC_EVAL_PASSWORD = "<senha de teste>"; $env:MONGODB_DATABASE = "<cópia descartável>"
$PY -m pytest -q
$PY ..\docs\sprint-10\scripts\regressao_entrega.py http://127.0.0.1:8093 pluseduc_sprint10_entrega ..\docs\sprint-11\resultados\regressao_api.json
$env:PLUSEDUC_EVID_DIR = "..\docs\manuais\imagens"
python ..\docs\sprint-11\scripts\capturas_manual.py
python ..\docs\sprint-11\scripts\gerar_pdf_sprint11.py <PDF das Sprints 01-10> <PDF de saída 01-11>
```
