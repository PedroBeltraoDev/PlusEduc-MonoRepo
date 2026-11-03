# Situação dos requisitos (Sprint 09)

Rastreabilidade entre o plano de projeto (`PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md`) e o sistema como está hoje.
"Evidência" aponta o caso de teste que exercita o requisito (catálogo em `docs/sprint-09/resultados/`) ou o documento da sprint em que foi demonstrado.

## Requisitos funcionais

| RF | Requisito | Situação | Evidência / observação |
|---|---|---|---|
| RF01 | Login com JWT e refresh token | **Parcial** | Login e JWT: AUT-01 a AUT-05, AUT-18. O refresh token é emitido, mas não existe rota para renová-lo e o frontend não o usa. |
| RF02 | Perfis ADMIN, PROFESSOR, ALUNO com autorização por rota e por tela | Concluído | Matriz de 94 rotas (Sprint 08) e testes de navegação NAV-A/P/S. Não há conta ADMIN no seed. |
| RF03 | Edição de perfil e troca de senha pelo próprio usuário | **Parcial** | Perfil: AUT-13, AUT-14. A senha só muda pela recuperação por código (AUT-15 a AUT-17); não há "trocar senha" logado. |
| RF04 | Cadastro público de professores com aprovação/ativação | **Parcial** | Cadastro funciona (AUT-10 a AUT-12), mas a conta é ativada na hora, sem aprovação. |
| RF05 | CRUD de alunos, professores e turmas | Concluído | TUR-01 a TUR-14, ALU-01 a ALU-14, PRO-01 a PRO-05 |
| RF06 | Matrícula e remanejamento | Concluído | TUR-10, TUR-11, TUR-13, ALU-14 |
| RF07 | Catálogo de componentes por série (BNCC); turma exibe só os compatíveis | Concluído | MAT-01 a MAT-04; regras em `services/curriculum.py` e testes `test_curriculum_rules.py` |
| RF08 | No máximo um professor por componente em cada turma | Concluído | `test_subject_assignment_real.py` e tela da turma ("Matérias e professores") |
| RF09 | Lacunas de aprendizagem por aluno | Concluído | campo `learning_gaps` do aluno (criação e edição de aluno) |
| RF10 | Notas por aluno e turma; média individual e por componente | Concluído | NOT-01 a NOT-10 |
| RF11 | Registro e consulta de frequência | Concluído | NOT-07, NOT-09 |
| RF12 | CRUD de atividades (objetivas e discursivas) | Concluído | ATI-01 a ATI-08, SUB-07 |
| RF13 | Geração assistida de atividades com alternativa determinística | Concluído | ATI-06 (sem chave do Gemini a alternativa determinística responde) |
| RF14 | Submissão pelo aluno no portal | Concluído | SUB-01 a SUB-05 |
| RF15 | Correção automática e manual, com feedback e professor | Concluído | SUB-03, SUB-07 |
| RF16 | Exportação de atividade em PDF | Concluído | ATI-07 |
| RF17 | Painel de desempenho por turma | **Parcial** | Desempenho por turma e dashboard com filtros (REL-01, REL-03); faltam ordenação por nota e a visão de alunos sem turma no mesmo painel |
| RF18 | Painel por aluno com evolução temporal e pontos fortes/fracos | **Parcial** | Desempenho por disciplina e frequência (POR-01); a evolução no tempo existe só no dashboard geral |
| RF19 | Predição de risco acadêmico | **Não implementado** | sem modelo preditivo |
| RF20 | Recomendação pedagógica priorizada e explicável | **Parcial** | escore determinístico em `GET /api/students/{id}/pedagogical-recommendation`, sem modelo e sem tela própria |
| RF21 | Agrupamento por perfil de dificuldade | **Não implementado** | |
| RF22 | Grupos e horários de reforço otimizados | **Não implementado** | |
| RF23 | Recálculo em lote com tempo e speedup | **Parcial** | estatísticas de notas em OpenCL e consultas paralelas (Sprint 08, seção 2.1); sem recálculo agendado e sem atingir 4x |
| RF24 | Dashboard inicial com estatísticas e alertas | Concluído | REL-01, REL-02 |
| RF25 | Histórico de submissões, correções e recomendações por aluno | **Parcial** | submissões e correções ficam gravadas e o professor vê as respostas (SUB-06); não há tela de histórico por aluno nem de recomendações |
| RF26 | Log de ações sensíveis | Concluído | HIS-01, HIS-02 |

## Requisitos não funcionais

| RNF | Requisito | Situação | Evidência / observação |
|---|---|---|---|
| RNF01 | Senhas com bcrypt | Concluído | **Bug corrigido na Sprint 09:** `POST /api/teachers` gravava a senha em texto puro (PRO-01 confere o hash no banco) |
| RNF02 | JWT Bearer, expiração configurável | Concluído | AUT-18; refresh token não abre a API (Sprint 08) |
| RNF03 | RBAC no backend | Concluído | matriz de permissões (Sprint 08) |
| RNF04 | LGPD: sem dados de menores em URLs, logs ou repositório; segredos só no `.env` | **Parcial** | código de recuperação fora do log e da resposta (Sprint 08); e-mail dos colegas removido do portal (POR-02); dados de demonstração fictícios no repositório; a LGPD não foi auditada além disso |
| RNF05 | CORS restrito | Concluído | verificação G da Sprint 08 |
| RNF06 | Processamento vetorizado e paralelo | **Parcial** | NumPy/OpenCL nas estatísticas e consultas paralelas; sem processamento em lote da escola |
| RNF07 | Speedup mínimo de 4x no recálculo de 1.000 alunos | **Não atingido** | OpenCL chega a 1,2x com 1 milhão de registros (Sprint 08) |
| RNF08 | Consultas de desempenho em até 2 s para turma típica | Concluído (no porte atual) | `resultados/desempenho.txt`: medianas de 5 a 16 ms; a maior turma do banco tem 7 alunos, sem teste com 40 |
| RNF09 | Treino assíncrono dos modelos | Não se aplica ainda | não há modelos |
| RNF10 | Interface responsiva e modo claro/escuro | Concluído | `resultados/responsividade.json` e capturas r01 a r07 (um estouro lateral no dashboard foi corrigido) |
| RNF11 | Recomendação sempre com justificativa | Parcial | a recomendação existente traz as evidências; não há tela |
| RNF12 | Mensagens de erro claras; modo alternativo da IA sinalizado | Concluído | VAL-UI-01 a VAL-UI-15; mensagens de validação traduzidas na Sprint 09 |
| RNF13 | Arquitetura em camadas | Concluído | `docs/ARQUITETURA.md` |
| RNF14 | Testes de backend e verificação de tipos e build do frontend a cada sprint | Concluído | 158 testes de backend; `type-check` e `build` sem erros |
| RNF15 | Health check e OpenAPI publicados automaticamente | **Parcial** | `/health`, `/docs` e `/redoc` existem; não há publicação automática (sem CI) |
| RNF16 | Configuração por ambiente | Concluído | `.env.example` |
| RNF17 | Windows e Linux, Python 3.11+, MongoDB local, Node 18+ | Parcial | validado só no Windows 11 (Python 3.12, Node 22) |
| RNF18 | Instruções de execução do banco e do sistema | Concluído | READMEs atualizados na Sprint 09 |

## Backlog de entrega (resumo)

B01 a B14 concluídos, **exceto B07** (repositório e ambiente existem, mas o CI de testes não foi implementado: os testes rodam manualmente);
B15 (predição) pendente; B16 parcial; B17 e B18 pendentes; B19 parcial; B20 a B24 concluídos (B24 com 158 testes);
B25: documentação atualizada nesta sprint, vídeos pendentes (entrega final).
