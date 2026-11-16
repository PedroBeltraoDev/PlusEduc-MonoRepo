# Sprint 09 — Testes completos

Verificação completa do sistema rodando (API + MongoDB + interface), registro dos bugs achados e corrigidos e atualização da documentação.
Tudo foi executado contra um banco descartável (`pluseduc_sprint9_eval`, cópia do `escola_db`); o `escola_db` não foi alterado.

## Resultado em números

| Conjunto | Casos | Antes das correções | Depois |
|---|---:|---:|---:|
| Testes funcionais e de validação da API (`resultados/testes_funcionais_*.txt`) | 92 | 80 aprovados, 12 reprovados | 92 aprovados |
| Navegação pela interface (`resultados/testes_navegacao_*.json`) | 90 | 88 aprovados, 2 reprovados | 90 aprovados |
| Validação pela interface (`resultados/testes_validacao_ui*.json`) | 15 | 14 casos executados; em VAL-UI-05 a tela mostrava a mensagem genérica "Erro de validação da requisição" | 15 aprovados |
| Suíte automatizada do backend (`pytest`) | 158 | 138 | 158 aprovados |
| Desempenho das consultas (`resultados/desempenho.txt`) | 9 consultas | — | todas abaixo de 61 ms (limite do plano: 2 s) |
| Responsividade em 390 px (`resultados/responsividade*.json`) | 5 telas | 1 com rolagem lateral | nenhuma |

## Bugs encontrados e corrigidos

| ID | Bug | Casos que acusaram | Gravidade |
|---|---|---|---|
| BUG-01 | E-mail sem validação de formato (`abc` virava conta) no cadastro e na criação de aluno e de professor | AUT-08, AUT-12, ALU-03, PRO-03 | média |
| BUG-02 | `POST /api/teachers` gravava a senha em **texto puro** e não criava o login do professor | PRO-01 | alta |
| BUG-03 | Professor podia ser criado sem senha | PRO-04 | média |
| BUG-04 | Turma criada com professor responsável inexistente | TUR-05 | média |
| BUG-05 | Aluno excluído continuava conseguindo entrar | ALU-12 | alta |
| BUG-06 | Aluno excluído continuava na lista da turma e impedia a exclusão dela | ALU-14 | média |
| BUG-07 | Atividade podia ser atribuída a aluno de outra turma (RN10 documentada, mas não aplicada) | ATI-04 | média |
| BUG-08 | Excluir uma atividade deixava as respostas dos alunos órfãs no banco | SUB-08 | média |
| BUG-09 | Portal do aluno mostrava o e-mail dos colegas (dados de menores) | POR-02 | média |
| BUG-10 | Endereço inexistente mostrava a tela técnica do React Router | NAV-R01, NAV-SR01 | baixa |
| BUG-11 | Mensagens de validação do servidor chegavam genéricas ("Erro de validação da requisição") em vez de explicar o campo | VAL-UI-05 | baixa |
| BUG-12 | Dashboard tinha rolagem horizontal no celular | responsividade | baixa |

Quatro divergências inicialmente apontadas pelo catálogo eram erros do próprio teste e foram corrigidas no catálogo, não no sistema: nomes dos parâmetros dos filtros do
dashboard (`from`, `to`, `classroomId`), exclusão lógica de turma e de professor (o registro continua consultável por id, mas sai das listas e não pode ser usado) e a escolha
de um aluno com colegas para o caso POR-02.

## Pendências (registradas, não corrigidas)

Cadastro público de professor sem aprovação; sem escopo por turma; predição, clustering e otimização de grupos; refresh token sem rota de renovação;
testes automatizados de frontend e integração contínua; turmas com 40 alunos não foram testadas (a maior do banco tem 7).

## Como reproduzir

Subir o backend (`:8091`) e o frontend (`:5183`, com `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8091`) apontando para o banco descartável, definir `PLUSEDUC_EVAL_PASSWORD`
e `PLUSEDUC_EVAL_DB`, preparar as contas com `docs/sprint-08/scripts/preparar_usuarios.py` e rodar, de dentro de `PlusEduc-BE-Python`:

```powershell
python ..\docs\sprint-09\scripts\testes_funcionais.py http://127.0.0.1:8091 pluseduc_sprint9_eval saida.json
python ..\docs\sprint-09\scripts\testes_navegacao.py saida_nav.json          # Chrome + Selenium
python ..\docs\sprint-09\scripts\testes_validacao_ui.py saida_val.json       # Chrome + Selenium
python ..\docs\sprint-09\scripts\medir_desempenho.py http://127.0.0.1:8091 pluseduc_sprint9_eval saida_perf.json
```

`gerar_modelo_dados.py` regera `docs/MODELO_DE_DADOS.md` a partir do banco.
