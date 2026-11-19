# Regras de negócio — PlusEduc

Catálogo consolidado na Sprint 11. As regras RN01 a RN29 vêm dos documentos das Sprints 05 a 08 (numeração original
mantida) e foram relidas contra o código atual. As regras a partir da RN30 entraram na Sprint 10, na atualização de
segurança e na Sprint 11. Todas são aplicadas pela **API**: a interface repete algumas validações só para avisar mais
cedo.

Siglas de verificação: casos da regressão funcional (`docs/sprint-09` e `docs/sprint-10/entrega`), como `ATI-04`, e
testes automatizados em `PlusEduc-BE-Python/tests/`.

## Portal do aluno e atividades

| Regra | Descrição | Verificação |
|---|---|---|
| RN01 | As rotas `/api/student-portal/**` exigem o perfil STUDENT; o serviço resolve o aluno ativo ligado ao usuário autenticado. | POR-01, `test_student_portal_real.py` |
| RN02 | O aluno só lista e abre atividades da sua turma ou atribuídas diretamente a ele. | `test_student_portal_real.py` |
| RN03 | Atividade sem questões não recebe envio online (400). | `test_submissions_sprint6_real.py` |
| RN04 | O aluno precisa responder todas as questões; cada índice deve ser válido e cada resposta, preenchida. | SUB-02 |
| RN05 | O aluno não reenvia a mesma atividade (409); garantido também por índice único `(activity_id, student_id)`. | SUB-04 |
| RN06 | O envio fica ligado à atividade e ao aluno; a API calcula acertos e percentual das objetivas antes de gravar. As discursivas ficam aguardando correção do professor. | SUB-03, SUB-07 |
| RN07 | Criação de atividade: título de 5 a 200 caracteres, tópico de 3 a 100, de 1 a 100 questões e turma obrigatória (422). | ATI-02 |
| RN08 | Criar, editar, excluir e gerar atividades é restrito a TEACHER e ADMIN; erros no formato JSON padronizado. | matriz de permissões |
| RN09 | O gabarito não é enviado ao aluno antes do envio; as rotas genéricas de leitura de atividades são restritas à equipe. | POR-01, `test_permissions_sprint8.py` |
| RN10 | A atividade só pode ser ligada a uma turma existente e a um aluno matriculado nela (400). | ATI-04 |

## Notas e frequência

| Regra | Descrição | Verificação |
|---|---|---|
| RN11 | Nota entre 0 e 10; aluno e turma precisam existir (422 e 400). | NOT-02, NOT-03 |
| RN12 | Presença opcional em cada lançamento: presente, faltou ou não registrar. | NOT-07 |
| RN13 | Média = média aritmética das notas lançadas (por aluno, turma ou disciplina). A interface destaca média abaixo de 6,0. | NOT-06, NOT-09 |
| RN14 | Frequência = presenças / lançamentos com presença registrada, em porcentagem inteira. Lançamento sem presença (ex.: nota de atividade online) não conta como aula. A interface destaca frequência abaixo de 75%. | NOT-07 |
| RN15 | A turma lista seus alunos ativos; sem alunos, a tela mostra estado vazio. | navegação |
| RN16 | Só a equipe lê e grava notas pelas rotas de notas; o aluno vê só as próprias notas, pelo portal. | `test_permissions_sprint8.py` |
| RN17 | Lançamento por atividade: nota = percentual de acerto / 10 (uma casa decimal); quem ainda aguarda correção manual fica de fora; é idempotente por (atividade, aluno) e não altera a frequência. | NOT-08 |
| RN18 | Editar ou excluir um lançamento recalcula média e frequência; a exclusão pede confirmação na interface. | NOT-06, NOT-10 |
| RN26 | A nota só pode ser lançada para aluno matriculado na turma informada (400). | NOT-04 |
| RN27 | A data do lançamento não pode ser futura (tolerância de 1 dia por causa do fuso; 422). | NOT-05 |

## Dashboard, relatórios, pesquisa e histórico

| Regra | Descrição | Verificação |
|---|---|---|
| RN19 | Dashboard, relatórios, pesquisa, exportação e histórico são restritos à equipe. O professor vê só os dados das turmas sob sua responsabilidade (RN33). | REL-01, HIS-02 |
| RN20 | Média e frequência dos indicadores seguem RN13 e RN14; "em atenção" = média abaixo de 6,0 ou frequência abaixo de 75%. | REL-01, `test_sprint7_real.py` |
| RN21 | Filtros: data inicial não pode ser posterior à final (422); turma inexistente (404); disciplina sem diferenciar acento e maiúsculas; datas no horário de Brasília. | REL-02 |
| RN22 | Pesquisa: mínimo de 2 caracteres, sem diferenciar acento, todas as palavras em qualquer ordem. | REL-06 |
| RN23 | Toda operação que altera dados é registrada com autor, resultado e resumo; notas guardam o antes e o depois; o histórico não pode ser editado nem apagado pela API. | HIS-01 |
| RN24 | O professor vê o próprio histórico; o administrador vê o de todos. | HIS-02 |
| RN25 | A exportação usa exatamente os filtros da tela e o mesmo cálculo do relatório; números vão como números no Excel; formato inválido devolve 422. | REL-04, REL-05 |

## Cadastros, turmas e matrículas

| Regra | Descrição | Verificação |
|---|---|---|
| RN28 | Um aluno pertence a uma única turma: matricular em outra o retira da anterior; a matrícula fica coerente nos dois lados (`students.class_id` e `classrooms.students`). | TUR-11, SEG-03 |
| RN29 | Data de nascimento no futuro ou anterior a 1900 é recusada (422). | `test_business_rules_sprint8.py` |
| RN31 | A turma exige professor responsável existente e ativo; cada professor tem no máximo 5 turmas ativas; nome e ano são únicos entre as turmas ativas; turma com alunos não pode ser excluída. | TUR-15, TUR-16, TUR-12 |
| RN32 | Cada matéria tem no máximo um professor responsável por turma, e só entram na turma as matérias compatíveis com a série (BNCC). | `test_subject_assignment_real.py`, `test_curriculum_rules.py` |
| RN38 | Excluir (desativar) um aluno o retira da turma e desativa o login do portal na hora; excluir um professor desativa o login dele. | ALU-14, SEG-07, PRO-05 |
| RN39 | E-mail em formato válido e único entre as contas ativas; senha com 6 a 100 caracteres; nomes com tamanho mínimo. | AUT-06 a AUT-09, PRO-03 |
| RN41 | A matrícula do aluno é gerada automaticamente (`MAT-<ano>-0001`) e é única. | ALU-01 |

## Contas, acesso e segurança

| Regra | Descrição | Verificação |
|---|---|---|
| RN30 | O cadastro público de professor fica pendente até o ADMIN aprovar; o login pendente recebe 403 só para quem acerta a senha; recusar remove o cadastro e libera o e-mail. | AUT-10, APR-01 a APR-04 |
| RN33 | O professor só atua nas turmas em que é titular, em que leciona uma matéria ou que constam no próprio cadastro, e nos alunos, notas, atividades e relatórios delas; fora disso, 403 (inclusive para id inexistente). O ADMIN vê tudo. | SEG-01, SEG-02, TUR-06 |
| RN34 | Criar, alterar e desativar professores, aprovar cadastros e alterar ou desativar matérias do catálogo são tarefas do ADMIN. A turma criada por um professor é sempre dele; transferir aluno da turma de outro professor é tarefa do ADMIN. | PRO-01, PRO-05, MAT-03, TUR-05, SEG-03 |
| RN35 | Sessão: token de acesso de 30 minutos; o refresh token vale uma vez, e reapresentar um já usado encerra todas as sessões daquele login. Trocar ou redefinir a senha e desativar a conta invalidam os tokens já emitidos; a troca de senha devolve um par novo para a sessão atual. | SES-01, SEG-04, SEG-05, SEN-02 |
| RN36 | Limite de tentativas: 5 falhas de login em 15 minutos por IP e e-mail; cadastro público e recuperação de senha também limitados; acima do limite, 429 com `Retry-After`. | SEG-06 |
| RN37 | O aluno cadastrado pela escola recebe o acesso ao portal da equipe (senha inicial definida pelo professor ou administrador). O autocadastro com o e-mail desse aluno é recusado (409), em vez de criar um segundo registro. | `test_sprint11_regressions_real.py` |
| RN40 | Em produção, a API não inicia com chave JWT fraca, modos de demonstração ligados, limite de tentativas desligado ou cadastro de professor sem aprovação. | `test_security_regressions_real.py` |
| RN42 | Recuperação de senha por código enviado por e-mail, válido por 15 minutos e com tentativas limitadas; a resposta é a mesma quer o e-mail exista ou não. | AUT-15 a AUT-17 |

## Geração de atividades com IA

| Regra | Descrição | Verificação |
|---|---|---|
| RN43 | Se o serviço de IA falhar, a atividade é gerada pelo gerador de reserva ou com questões já salvas do mesmo assunto, e a fonte usada fica registrada e é mostrada ao professor. | ATI-06, `test_ai_pdf_real.py` |
| RN44 | As adaptações inclusivas escolhidas (dislexia, baixa visão, TDAH) valem para o conteúdo e para o PDF; em baixa visão o PDF usa fonte 30% maior. | `test_sprint11_regressions_real.py` |
