# API do PlusEduc — referência (versão 1.0.0-rc.1)

> Documento gerado por `PlusEduc-BE-Python/scripts/export_api_docs.py` a partir do esquema OpenAPI do backend. Não edite à mão: altere os routers, os schemas ou `app/api/openapi_docs.py` e gere de novo.

| Onde consultar | Endereço |
|---|---|
| Swagger UI (interativo, com o servidor em execução) | `http://127.0.0.1:8080/docs` |
| ReDoc (leitura) | `http://127.0.0.1:8080/redoc` |
| Esquema OpenAPI 3.1 | `http://127.0.0.1:8080/openapi.json` e [`docs/api/openapi.json`](api/openapi.json) |

São **99 rotas** em 18 grupos. Base: `http://127.0.0.1:8080` em desenvolvimento (o frontend chama `/api` pelo proxy do Vite).

## Visão geral

API REST do **PlusEduc**, plataforma de gestão pedagógica da educação básica: turmas, alunos, professores,
atividades, notas, frequência, relatórios e portal do aluno.

### Autenticação

1. `POST /api/auth/login` com e-mail e senha devolve `accessToken` (8 h) e `refreshToken` (7 dias).
2. Envie o token de acesso em todas as rotas protegidas: `Authorization: Bearer <accessToken>`.
3. Quando o token de acesso vencer, troque o refresh token por um novo par em `POST /api/auth/refresh`.

No Swagger, clique em **Authorize** e cole o `accessToken`.

### Perfis

| Perfil | O que acessa |
|---|---|
| `TEACHER` | gestão de turmas, alunos, atividades, notas, relatórios e o próprio histórico |
| `ADMIN` | o mesmo que o professor, mais a aprovação de cadastros de professor e o histórico de todos |
| `STUDENT` | apenas `/api/student-portal/**` e os próprios dados de desempenho |

Cada rota informa o perfil exigido no campo **Acesso**. Sem token a resposta é `401`; com perfil errado, `403`.

### Erros

Todo erro tem o mesmo formato JSON:

```json
{"timestamp": "2026-11-11T18:00:00Z", "status": 400, "error": "Bad Request", "message": "Senha atual incorreta"}
```

Erros de validação (`422`) trazem também `details`, com o campo (`loc`) e o motivo (`msg`) de cada problema.
Datas usam ISO 8601; identificadores são os `_id` do MongoDB em texto (24 caracteres hexadecimais).

## Exemplos de uso

Os exemplos usam `curl` contra o servidor local (`http://127.0.0.1:8080`). Troque os valores entre `<>`.

### 1. Entrar e guardar o token

```bash
curl -s -X POST http://127.0.0.1:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "<e-mail>", "password": "<senha>"}'
```

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "tokenType": "Bearer",
  "expiresIn": 28800,
  "userId": "6a0f1f9d20a4a3f5efdd7cb1",
  "userEmail": "<e-mail>",
  "role": "TEACHER",
  "name": "Marina Ferreira"
}
```

E-mail ou senha errados: `401` com `{"message": "Invalid email or password"}`. Professor com cadastro ainda não
aprovado: `403` com a mensagem de aprovação pendente.

### 2. Chamar uma rota protegida

```bash
curl -s http://127.0.0.1:8080/api/classrooms -H "Authorization: Bearer <accessToken>"
```

### 3. Renovar a sessão

```bash
curl -s -X POST http://127.0.0.1:8080/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refreshToken": "<refreshToken>"}'
```

A resposta tem o mesmo formato do login, com um novo par de tokens.

### 4. Criar uma turma

```bash
curl -s -X POST http://127.0.0.1:8080/api/classrooms \
  -H "Authorization: Bearer <accessToken>" -H "Content-Type: application/json" \
  -d '{"name": "7º Ano do Ensino Fundamental E", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": "<id do professor>"}'
```

`201` com a turma criada. `409` se já existir turma com o mesmo nome e ano; `400` se o professor não existir,
estiver inativo ou já tiver 5 turmas ativas. As matérias são preenchidas conforme a série (BNCC).

### 5. Lançar uma nota

```bash
curl -s -X POST http://127.0.0.1:8080/api/grades \
  -H "Authorization: Bearer <accessToken>" -H "Content-Type: application/json" \
  -d '{"studentId": "<id do aluno>", "classroomId": "<id da turma>", "grade": 8.5, "attendance": true, "subject": "Matemática", "activityType": "EXAM", "date": "2026-11-10T12:00:00Z"}'
```

`201` com a nota. `400` se o aluno não estiver matriculado na turma; `422` se a nota estiver fora de 0 a 10 ou a
data estiver no futuro.

### 6. Aluno envia as respostas de uma atividade

```bash
curl -s -X POST http://127.0.0.1:8080/api/student-portal/activities/<id da atividade>/submissions \
  -H "Authorization: Bearer <accessToken do aluno>" -H "Content-Type: application/json" \
  -d '{"answers": [{"questionIndex": 0, "selectedAnswer": "B"}, {"questionIndex": 1, "selectedAnswer": "Texto da resposta discursiva"}]}'
```

As questões objetivas voltam corrigidas na resposta; as discursivas ficam aguardando o professor
(`PUT /api/teacher/activity-corrections/{submission_id}/questions/{question_index}`).

### 7. Exportar um relatório

```bash
curl -s -o boletim.xlsx "http://127.0.0.1:8080/api/reports/<tipo>/export?format=xlsx&classroomId=<id da turma>" \
  -H "Authorization: Bearer <accessToken>"
```

Os tipos de relatório disponíveis vêm de `GET /api/reports`; `format` aceita `csv`, `xlsx` e `pdf`.

## Rotas por grupo

### Infraestrutura

Verificação de disponibilidade da aplicação e do banco.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/health` | público | Verificar a disponibilidade da aplicação |

### Autenticação

Login, renovação de sessão, cadastro público, perfil e senha.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `PUT` | `/api/auth/profile` | qualquer usuário autenticado | Atualizar perfil do usuário autenticado |
| `POST` | `/api/auth/register/student` | público | Cadastrar aluno com matrícula automática e emitir tokens |
| `POST` | `/api/auth/register/teacher` | público | Cadastro público de professor (fica pendente até um ADMIN aprovar) |
| `POST` | `/api/auth/refresh` | público | Renovar a sessão com o refresh token |
| `POST` | `/api/auth/change-password` | qualquer usuário autenticado | Trocar a própria senha (usuário autenticado) |
| `POST` | `/api/auth/login` | público | Autenticar usuário e emitir tokens |
| `POST` | `/api/auth/forgot-password` | público | Solicitar código de verificação para redefinição de senha |
| `POST` | `/api/auth/reset-password` | público | Redefinir senha a partir do código de verificação |

### Alunos

Cadastro de alunos, matrícula, lacunas de aprendizagem e acesso ao portal.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/students` | TEACHER ou ADMIN | Listar alunos ativos |
| `POST` | `/api/students` | TEACHER ou ADMIN | Cadastrar aluno |
| `GET` | `/api/students/unassigned` | TEACHER ou ADMIN | Listar alunos sem turma |
| `GET` | `/api/students/paginated` | TEACHER ou ADMIN | Listar alunos com paginação |
| `GET` | `/api/students/class/{class_id}` | TEACHER ou ADMIN | Listar alunos de uma turma |
| `GET` | `/api/students/learning-gap/{subject}` | TEACHER ou ADMIN | Listar alunos com lacuna de aprendizagem em uma matéria |
| `GET` | `/api/students/{student_id}` | TEACHER ou ADMIN | Consultar aluno |
| `PUT` | `/api/students/{student_id}` | TEACHER ou ADMIN | Editar aluno |
| `DELETE` | `/api/students/{student_id}` | TEACHER ou ADMIN | Excluir aluno (exclusão lógica; o login deixa de valer) |
| `POST` | `/api/students/{student_id}/enable-access` | TEACHER ou ADMIN | Criar o login do portal para um aluno já cadastrado |

### Desempenho do aluno

Desempenho, frequência e recomendação pedagógica de um aluno.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/students/{student_id}/performance` | TEACHER ou ADMIN; STUDENT apenas para o próprio registro | Desempenho do aluno por disciplina |
| `GET` | `/api/students/{student_id}/attendance` | TEACHER ou ADMIN; STUDENT apenas para o próprio registro | Frequência do aluno |
| `GET` | `/api/students/{student_id}/pedagogical-recommendation` | TEACHER ou ADMIN; STUDENT apenas para o próprio registro | Recomendação pedagógica priorizada, com as evidências |

### Professores

Cadastro de professores e aprovação dos cadastros públicos.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/teachers` | TEACHER ou ADMIN | Listar professores ativos |
| `POST` | `/api/teachers` | TEACHER ou ADMIN | Cadastrar professor (já ativo, com login) |
| `GET` | `/api/teachers/email/{email}` | TEACHER ou ADMIN | Consultar professor pelo e-mail |
| `GET` | `/api/teachers/subject/{subject}` | TEACHER ou ADMIN | Listar professores de uma matéria |
| `GET` | `/api/teachers/pending` | ADMIN | Listar cadastros públicos de professor aguardando aprovação (ADMIN) |
| `POST` | `/api/teachers/{teacher_id}/approve` | ADMIN | Aprovar cadastro de professor (ADMIN): libera o login |
| `POST` | `/api/teachers/{teacher_id}/reject` | ADMIN | Recusar cadastro de professor (ADMIN): remove o cadastro pendente |
| `GET` | `/api/teachers/count` | TEACHER ou ADMIN | Quantidade de professores cadastrados |
| `GET` | `/api/teachers/{teacher_id}` | TEACHER ou ADMIN | Consultar professor |
| `PUT` | `/api/teachers/{teacher_id}` | TEACHER ou ADMIN | Editar professor |
| `DELETE` | `/api/teachers/{teacher_id}` | TEACHER ou ADMIN | Excluir professor (exclusão lógica; o login deixa de valer) |

### Turmas

Turmas, matrícula de alunos e desempenho por turma.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/classrooms` | TEACHER ou ADMIN | Listar turmas ativas |
| `POST` | `/api/classrooms` | TEACHER ou ADMIN | Criar turma |
| `GET` | `/api/classrooms/paginated` | TEACHER ou ADMIN | Listar turmas com paginação |
| `GET` | `/api/classrooms/teacher/{teacher_id}` | TEACHER ou ADMIN | Listar turmas de um professor |
| `GET` | `/api/classrooms/student/{student_id}` | TEACHER ou ADMIN | Listar turmas de um aluno |
| `GET` | `/api/classrooms/year/{year}` | TEACHER ou ADMIN | Listar turmas de um ano letivo |
| `GET` | `/api/classrooms/{classroom_id}/performance` | TEACHER ou ADMIN | Desempenho dos alunos da turma |
| `GET` | `/api/classrooms/{classroom_id}` | TEACHER ou ADMIN | Consultar turma |
| `PUT` | `/api/classrooms/{classroom_id}` | TEACHER ou ADMIN | Editar turma |
| `DELETE` | `/api/classrooms/{classroom_id}` | TEACHER ou ADMIN | Excluir turma (só sem alunos matriculados) |
| `POST` | `/api/classrooms/{classroom_id}/enroll/{student_id}` | TEACHER ou ADMIN | Matricular aluno na turma (sai da turma anterior) |
| `DELETE` | `/api/classrooms/{classroom_id}/unenroll/{student_id}` | TEACHER ou ADMIN | Remover aluno da turma |

### Notas e frequência

Lançamento e consulta de notas e presença; resumo por turma.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/grades` | TEACHER ou ADMIN | Listar notas |
| `POST` | `/api/grades` | TEACHER ou ADMIN | Lançar nota e presença |
| `GET` | `/api/grades/student/{student_id}/average` | TEACHER ou ADMIN | Média geral de um aluno |
| `GET` | `/api/grades/student/{student_id}` | TEACHER ou ADMIN | Listar notas de um aluno |
| `GET` | `/api/grades/classroom/{classroom_id}` | TEACHER ou ADMIN | Listar notas de uma turma |
| `GET` | `/api/grades/classroom/{classroom_id}/summary` | TEACHER ou ADMIN | Boletim da turma: média e frequência por aluno |
| `POST` | `/api/grades/from-activity/{activity_id}` | TEACHER ou ADMIN | Lançar no boletim as notas de uma atividade respondida |
| `GET` | `/api/grades/{grade_id}` | TEACHER ou ADMIN | Consultar nota |
| `PUT` | `/api/grades/{grade_id}` | TEACHER ou ADMIN | Editar nota |
| `DELETE` | `/api/grades/{grade_id}` | TEACHER ou ADMIN | Excluir nota |

### Atividades

Atividades objetivas e discursivas, geração assistida e exportação em PDF.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/activities` | TEACHER ou ADMIN | Listar atividades |
| `POST` | `/api/activities` | TEACHER ou ADMIN | Criar atividade |
| `POST` | `/api/activities/generate` | TEACHER ou ADMIN | Gerar atividade a partir de um tópico (IA, com alternativa determinística) |
| `GET` | `/api/activities/classroom/{classroom_id}` | TEACHER ou ADMIN | Listar atividades de uma turma |
| `GET` | `/api/activities/student/{student_id}` | TEACHER ou ADMIN | Listar atividades atribuídas a um aluno |
| `GET` | `/api/activities/teacher/{teacher_id}` | TEACHER ou ADMIN | Listar atividades criadas por um professor |
| `GET` | `/api/activities/{activity_id}/submissions` | TEACHER ou ADMIN | Participação e respostas da turma em uma atividade |
| `GET` | `/api/activities/{activity_id}/export-pdf` | qualquer usuário autenticado | Exportar atividade em PDF (gabarito só para professor) |
| `GET` | `/api/activities/{activity_id}` | TEACHER ou ADMIN | Consultar atividade (com gabarito) |
| `PUT` | `/api/activities/{activity_id}` | TEACHER ou ADMIN | Editar atividade |
| `DELETE` | `/api/activities/{activity_id}` | TEACHER ou ADMIN | Excluir atividade e as respostas dela |

### Portal do aluno

Dados que o aluno vê sobre si: turma, professores, atividades, notas e desempenho.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/student-portal/me` | STUDENT | Perfil do aluno autenticado |
| `GET` | `/api/student-portal/classroom` | STUDENT | Turma do aluno |
| `GET` | `/api/student-portal/classmates` | STUDENT | Colegas de turma (somente nome) |
| `GET` | `/api/student-portal/teachers` | STUDENT | Professores da turma do aluno |
| `GET` | `/api/student-portal/activities` | STUDENT | Atividades da turma do aluno ou atribuídas a ele |
| `GET` | `/api/student-portal/activities/{activity_id}` | STUDENT | Atividade para responder (sem gabarito) |
| `GET` | `/api/student-portal/activities/{activity_id}/export-pdf` | STUDENT | Exportar a atividade em PDF (sem gabarito) |
| `GET` | `/api/student-portal/grades` | STUDENT | Notas do aluno |
| `GET` | `/api/student-portal/performance` | STUDENT | Desempenho do aluno por disciplina |

### Tópicos das matérias

Tópicos de conteúdo usados na criação de atividades.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/subject-topics` | TEACHER ou ADMIN | Listar tópicos |
| `POST` | `/api/subject-topics` | TEACHER ou ADMIN | Criar tópico |
| `PUT` | `/api/subject-topics/{item_id}` | TEACHER ou ADMIN | Editar tópico |
| `DELETE` | `/api/subject-topics/{item_id}` | TEACHER ou ADMIN | Excluir tópico |

### Matérias

Catálogo de componentes curriculares (BNCC) e atribuição de professor por turma.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/subjects` | TEACHER ou ADMIN | Listar matérias do catálogo |
| `POST` | `/api/subjects` | TEACHER ou ADMIN | Criar matéria |
| `GET` | `/api/subjects/available` | TEACHER ou ADMIN | Matérias compatíveis com a série de uma turma |
| `POST` | `/api/subjects/assignments` | TEACHER ou ADMIN | Assumir uma matéria em uma turma (um professor por matéria) |
| `PATCH` | `/api/subjects/{subject_id}` | TEACHER ou ADMIN | Editar ou desativar matéria |
| `DELETE` | `/api/subjects/{subject_id}` | TEACHER ou ADMIN | Desativar matéria |
| `GET` | `/api/subjects/{subject_id}/classrooms` | TEACHER ou ADMIN | Turmas do professor que têm a matéria |
| `GET` | `/api/subjects/{subject_id}/classrooms/{classroom_id}/performance` | TEACHER ou ADMIN | Desempenho dos alunos na matéria |

### Portal do aluno — respostas

Envio e consulta das respostas do aluno a uma atividade.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/student-portal/activities/{activity_id}/submissions` | STUDENT | Consultar as próprias respostas e a correção |
| `POST` | `/api/student-portal/activities/{activity_id}/submissions` | STUDENT | Enviar respostas (objetivas são corrigidas na hora) |

### Correção de atividades

Correção manual das questões discursivas pelo professor.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/teacher/activity-corrections/pending` | TEACHER ou ADMIN | Listar respostas discursivas aguardando correção |
| `PUT` | `/api/teacher/activity-corrections/{submission_id}/questions/{question_index}` | TEACHER ou ADMIN | Corrigir uma questão discursiva (nota e comentário) |

### Correção de atividades (rota antiga)

Mesmo comportamento de **Correção de atividades**, no endereço antigo com sublinhado. Mantida por compatibilidade.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/teacher/activity_corrections/pending` | TEACHER ou ADMIN | Listar respostas discursivas aguardando correção (rota antiga) |
| `PUT` | `/api/teacher/activity_corrections/{submission_id}/questions/{question_index}` | TEACHER ou ADMIN | Corrigir uma questão discursiva (rota antiga) |

### Histórico de operações

Registro das operações que alteram dados (quem, quando, o quê e o resultado).

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/audit-logs` | TEACHER ou ADMIN | Histórico de operações (professor: as próprias; admin: todas) |

### Relatórios

Relatórios com filtros e exportação em CSV, Excel e PDF.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/reports` | TEACHER ou ADMIN | Relatórios disponíveis |
| `GET` | `/api/reports/{report_type}` | TEACHER ou ADMIN | Executa um relatório com filtros |
| `GET` | `/api/reports/{report_type}/export` | TEACHER ou ADMIN | Exporta um relatório em CSV, XLSX ou PDF |

### Dashboard

Indicadores e séries dos gráficos do painel inicial.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/dashboard/overview` | TEACHER ou ADMIN | Indicadores e gráficos do dashboard |

### Pesquisa

Pesquisa global em alunos, turmas e atividades.

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/api/search` | TEACHER ou ADMIN | Pesquisa global em alunos, turmas e atividades |

## Detalhe das rotas

Para cada rota: parâmetros de caminho e de consulta, corpo esperado e respostas. Os nomes em link levam aos campos em [Esquemas](#esquemas).

### Infraestrutura — detalhe

#### `GET /health`

Verificar a disponibilidade da aplicação. **Acesso:** público.

**Respostas:** `200` Sucesso — [HealthResponse](#healthresponse).

### Autenticação — detalhe

#### `PUT /api/auth/profile`

Atualizar perfil do usuário autenticado. **Acesso:** qualquer usuário autenticado.

**Corpo (JSON):** [ProfileUpdateRequest](#profileupdaterequest)

**Respostas:** `200` Sucesso — [AuthenticationResponse](#authenticationresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado.

#### `POST /api/auth/register/student`

Cadastrar aluno com matrícula automática e emitir tokens. **Acesso:** público.

**Corpo (JSON):** [StudentRegistrationRequest](#studentregistrationrequest)

**Respostas:** `200` Sucesso — [AuthenticationResponse](#authenticationresponse); `422` Dados inválidos (campo e motivo em `details`).

#### `POST /api/auth/register/teacher`

Cadastro público de professor (fica pendente até um ADMIN aprovar). **Acesso:** público.

Com `TEACHER_REGISTRATION_REQUIRES_APPROVAL=true` (padrão) a conta nasce pendente: a resposta é **202** com `status=PENDING_APPROVAL` e nenhum token; o login devolve 403 até um ADMIN aprovar em `POST /api/teachers/{id}/approve`. Com a opção desligada, a resposta é 200 com os tokens.

**Corpo (JSON):** [TeacherRegistrationRequest](#teacherregistrationrequest)

**Respostas:** `200` Sucesso — [AuthenticationResponse](#authenticationresponse) ou [TeacherRegistrationPendingResponse](#teacherregistrationpendingresponse); `202` Cadastro aguardando aprovação — [TeacherRegistrationPendingResponse](#teacherregistrationpendingresponse); `422` Dados inválidos (campo e motivo em `details`).

#### `POST /api/auth/refresh`

Renovar a sessão com o refresh token. **Acesso:** público.

Recebe o `refreshToken` do login e devolve um novo par de tokens. O token de acesso (8 h) não serve aqui, e o refresh token não abre as demais rotas. Conta excluída ou desativada recebe 401.

**Corpo (JSON):** [RefreshTokenRequest](#refreshtokenrequest)

**Respostas:** `200` Sucesso — [AuthenticationResponse](#authenticationresponse); `422` Dados inválidos (campo e motivo em `details`).

#### `POST /api/auth/change-password`

Trocar a própria senha (usuário autenticado). **Acesso:** qualquer usuário autenticado.

Exige a senha atual. A nova senha precisa ter de 6 a 100 caracteres e ser diferente da atual.

**Corpo (JSON):** [ChangePasswordRequest](#changepasswordrequest)

**Respostas:** `200` Sucesso — [ChangePasswordResponse](#changepasswordresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado.

#### `POST /api/auth/login`

Autenticar usuário e emitir tokens. **Acesso:** público.

**Corpo (JSON):** [AuthenticationRequest](#authenticationrequest)

**Respostas:** `200` Sucesso — [AuthenticationResponse](#authenticationresponse); `422` Dados inválidos (campo e motivo em `details`).

#### `POST /api/auth/forgot-password`

Solicitar código de verificação para redefinição de senha. **Acesso:** público.

**Corpo (JSON):** [ForgotPasswordRequest](#forgotpasswordrequest)

**Respostas:** `200` Sucesso — [ForgotPasswordResponse](#forgotpasswordresponse); `422` Dados inválidos (campo e motivo em `details`).

#### `POST /api/auth/reset-password`

Redefinir senha a partir do código de verificação. **Acesso:** público.

**Corpo (JSON):** [ResetPasswordRequest](#resetpasswordrequest)

**Respostas:** `200` Sucesso — [ResetPasswordResponse](#resetpasswordresponse); `422` Dados inválidos (campo e motivo em `details`).

### Alunos — detalhe

#### `GET /api/students`

Listar alunos ativos. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [StudentResponse](#studentresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/students`

Cadastrar aluno. **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [StudentCreateRequest](#studentcreaterequest)

**Respostas:** `201` Sucesso — [StudentResponse](#studentresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/students/unassigned`

Listar alunos sem turma. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [StudentResponse](#studentresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/students/paginated`

Listar alunos com paginação. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `page` | consulta | inteiro | não | mín. 0; padrão: `0` |
| `size` | consulta | inteiro | não | mín. 1; máx. 100; padrão: `20` |
| `sort` | consulta | texto (ou nulo) | não |  |

**Respostas:** `200` Sucesso — [StudentPageResponse](#studentpageresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/students/class/{class_id}`

Listar alunos de uma turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `class_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [StudentResponse](#studentresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/students/learning-gap/{subject}`

Listar alunos com lacuna de aprendizagem em uma matéria. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `subject` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [StudentResponse](#studentresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/students/{student_id}`

Consultar aluno. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [StudentResponse](#studentresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/students/{student_id}`

Editar aluno. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Corpo (JSON):** [StudentUpdateRequest](#studentupdaterequest)

**Respostas:** `200` Sucesso — [StudentResponse](#studentresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/students/{student_id}`

Excluir aluno (exclusão lógica; o login deixa de valer). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/students/{student_id}/enable-access`

Criar o login do portal para um aluno já cadastrado. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Corpo (JSON):** [EnableStudentAccessRequest](#enablestudentaccessrequest)

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Desempenho do aluno — detalhe

#### `GET /api/students/{student_id}/performance`

Desempenho do aluno por disciplina. **Acesso:** TEACHER ou ADMIN; STUDENT apenas para o próprio registro.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [StudentPerformanceResponse](#studentperformanceresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/students/{student_id}/attendance`

Frequência do aluno. **Acesso:** TEACHER ou ADMIN; STUDENT apenas para o próprio registro.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [StudentAttendanceResponse](#studentattendanceresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/students/{student_id}/pedagogical-recommendation`

Recomendação pedagógica priorizada, com as evidências. **Acesso:** TEACHER ou ADMIN; STUDENT apenas para o próprio registro.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [PedagogicalRecommendationResponse](#pedagogicalrecommendationresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Professores — detalhe

#### `GET /api/teachers`

Listar professores ativos. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [TeacherResponse](#teacherresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/teachers`

Cadastrar professor (já ativo, com login). **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [TeacherCreateRequest](#teachercreaterequest)

**Respostas:** `201` Sucesso — [TeacherResponse](#teacherresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/teachers/email/{email}`

Consultar professor pelo e-mail. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `email` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [TeacherResponse](#teacherresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/teachers/subject/{subject}`

Listar professores de uma matéria. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `subject` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [TeacherResponse](#teacherresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/teachers/pending`

Listar cadastros públicos de professor aguardando aprovação (ADMIN). **Acesso:** ADMIN.

**Respostas:** `200` Sucesso — lista de [PendingTeacherResponse](#pendingteacherresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/teachers/{teacher_id}/approve`

Aprovar cadastro de professor (ADMIN): libera o login. **Acesso:** ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `teacher_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [TeacherResponse](#teacherresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/teachers/{teacher_id}/reject`

Recusar cadastro de professor (ADMIN): remove o cadastro pendente. **Acesso:** ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `teacher_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/teachers/count`

Quantidade de professores cadastrados. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — inteiro; `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/teachers/{teacher_id}`

Consultar professor. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `teacher_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [TeacherResponse](#teacherresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/teachers/{teacher_id}`

Editar professor. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `teacher_id` | caminho | texto | sim |  |

**Corpo (JSON):** [TeacherUpdateRequest](#teacherupdaterequest)

**Respostas:** `200` Sucesso — [TeacherResponse](#teacherresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/teachers/{teacher_id}`

Excluir professor (exclusão lógica; o login deixa de valer). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `teacher_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Turmas — detalhe

#### `GET /api/classrooms`

Listar turmas ativas. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [ClassroomResponse](#classroomresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/classrooms`

Criar turma. **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [ClassroomCreateRequest](#classroomcreaterequest)

**Respostas:** `201` Sucesso — [ClassroomResponse](#classroomresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/classrooms/paginated`

Listar turmas com paginação. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `page` | consulta | inteiro | não | mín. 0; padrão: `0` |
| `size` | consulta | inteiro | não | mín. 1; máx. 100; padrão: `20` |
| `sort` | consulta | texto (ou nulo) | não |  |

**Respostas:** `200` Sucesso — [ClassroomPageResponse](#classroompageresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/classrooms/teacher/{teacher_id}`

Listar turmas de um professor. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `teacher_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [ClassroomResponse](#classroomresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/classrooms/student/{student_id}`

Listar turmas de um aluno. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [ClassroomResponse](#classroomresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/classrooms/year/{year}`

Listar turmas de um ano letivo. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `year` | caminho | inteiro | sim |  |

**Respostas:** `200` Sucesso — lista de [ClassroomResponse](#classroomresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/classrooms/{classroom_id}/performance`

Desempenho dos alunos da turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [ClassroomPerformanceResponse](#classroomperformanceresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/classrooms/{classroom_id}`

Consultar turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [ClassroomResponse](#classroomresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/classrooms/{classroom_id}`

Editar turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |

**Corpo (JSON):** [ClassroomUpdateRequest](#classroomupdaterequest)

**Respostas:** `200` Sucesso — [ClassroomResponse](#classroomresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/classrooms/{classroom_id}`

Excluir turma (só sem alunos matriculados). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/classrooms/{classroom_id}/enroll/{student_id}`

Matricular aluno na turma (sai da turma anterior). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |
| `student_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/classrooms/{classroom_id}/unenroll/{student_id}`

Remover aluno da turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |
| `student_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Notas e frequência — detalhe

#### `GET /api/grades`

Listar notas. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [GradeResponse](#graderesponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/grades`

Lançar nota e presença. **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [GradeCreateRequest](#gradecreaterequest)

**Respostas:** `201` Sucesso — [GradeResponse](#graderesponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/grades/student/{student_id}/average`

Média geral de um aluno. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — número; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/grades/student/{student_id}`

Listar notas de um aluno. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [GradeResponse](#graderesponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/grades/classroom/{classroom_id}`

Listar notas de uma turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [GradeResponse](#graderesponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/grades/classroom/{classroom_id}/summary`

Boletim da turma: média e frequência por aluno. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |
| `subject` | consulta | texto (ou nulo) | não |  |

**Respostas:** `200` Sucesso — [GradeClassroomSummaryResponse](#gradeclassroomsummaryresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/grades/from-activity/{activity_id}`

Lançar no boletim as notas de uma atividade respondida. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [ActivityGradesLaunchResponse](#activitygradeslaunchresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/grades/{grade_id}`

Consultar nota. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `grade_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [GradeResponse](#graderesponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/grades/{grade_id}`

Editar nota. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `grade_id` | caminho | texto | sim |  |

**Corpo (JSON):** [GradeUpdateRequest](#gradeupdaterequest)

**Respostas:** `200` Sucesso — [GradeResponse](#graderesponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/grades/{grade_id}`

Excluir nota. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `grade_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Atividades — detalhe

#### `GET /api/activities`

Listar atividades. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [ActivityResponse](#activityresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/activities`

Criar atividade. **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [ActivityCreateRequest](#activitycreaterequest)

**Respostas:** `201` Sucesso — [ActivityResponse](#activityresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/activities/generate`

Gerar atividade a partir de um tópico (IA, com alternativa determinística). **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [ActivityGenerationRequest](#activitygenerationrequest)

**Respostas:** `201` Sucesso — [ActivityResponse](#activityresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/activities/classroom/{classroom_id}`

Listar atividades de uma turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroom_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [ActivityResponse](#activityresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/activities/student/{student_id}`

Listar atividades atribuídas a um aluno. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `student_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [ActivityResponse](#activityresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/activities/teacher/{teacher_id}`

Listar atividades criadas por um professor. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `teacher_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [ActivityResponse](#activityresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/activities/{activity_id}/submissions`

Participação e respostas da turma em uma atividade. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [ActivitySubmissionDetailResponse](#activitysubmissiondetailresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/activities/{activity_id}/export-pdf`

Exportar atividade em PDF (gabarito só para professor). **Acesso:** qualquer usuário autenticado.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |
| `includeAnswers` | consulta | booleano | não | padrão: `False` |

**Respostas:** `200` Sucesso — application/json; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado.

#### `GET /api/activities/{activity_id}`

Consultar atividade (com gabarito). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [ActivityResponse](#activityresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/activities/{activity_id}`

Editar atividade. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Corpo (JSON):** [ActivityUpdateRequest](#activityupdaterequest)

**Respostas:** `200` Sucesso — [ActivityResponse](#activityresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/activities/{activity_id}`

Excluir atividade e as respostas dela. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Portal do aluno — detalhe

#### `GET /api/student-portal/me`

Perfil do aluno autenticado. **Acesso:** STUDENT.

**Respostas:** `200` Sucesso — [StudentPortalProfile](#studentportalprofile); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/classroom`

Turma do aluno. **Acesso:** STUDENT.

**Respostas:** `200` Sucesso — [StudentClassroom](#studentclassroom); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/classmates`

Colegas de turma (somente nome). **Acesso:** STUDENT.

**Respostas:** `200` Sucesso — lista de [Classmate](#classmate); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/teachers`

Professores da turma do aluno. **Acesso:** STUDENT.

**Respostas:** `200` Sucesso — lista de [TeacherSummary](#teachersummary); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/activities`

Atividades da turma do aluno ou atribuídas a ele. **Acesso:** STUDENT.

**Respostas:** `200` Sucesso — lista de [StudentActivity](#studentactivity); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/activities/{activity_id}`

Atividade para responder (sem gabarito). **Acesso:** STUDENT.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [StudentActivityDetail](#studentactivitydetail); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/activities/{activity_id}/export-pdf`

Exportar a atividade em PDF (sem gabarito). **Acesso:** STUDENT.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — application/json; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/grades`

Notas do aluno. **Acesso:** STUDENT.

**Respostas:** `200` Sucesso — lista de [GradeResponse](#graderesponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/student-portal/performance`

Desempenho do aluno por disciplina. **Acesso:** STUDENT.

**Respostas:** `200` Sucesso — [StudentPortalPerformance](#studentportalperformance); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Tópicos das matérias — detalhe

#### `GET /api/subject-topics`

Listar tópicos. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [SubjectTopicResponse](#subjecttopicresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/subject-topics`

Criar tópico. **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [SubjectTopicCreateRequest](#subjecttopiccreaterequest)

**Respostas:** `201` Sucesso — [SubjectTopicResponse](#subjecttopicresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/subject-topics/{item_id}`

Editar tópico. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `item_id` | caminho | texto | sim |  |

**Corpo (JSON):** [SubjectTopicUpdateRequest](#subjecttopicupdaterequest)

**Respostas:** `200` Sucesso — [SubjectTopicResponse](#subjecttopicresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/subject-topics/{item_id}`

Excluir tópico. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `item_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Matérias — detalhe

#### `GET /api/subjects`

Listar matérias do catálogo. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [SubjectResponse](#subjectresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/subjects`

Criar matéria. **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [SubjectCreateRequest](#subjectcreaterequest)

**Respostas:** `201` Sucesso — [SubjectResponse](#subjectresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/subjects/available`

Matérias compatíveis com a série de uma turma. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroomId` | consulta | texto | sim | mín. 1 caracteres |

**Respostas:** `200` Sucesso — lista de [SubjectResponse](#subjectresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/subjects/assignments`

Assumir uma matéria em uma turma (um professor por matéria). **Acesso:** TEACHER ou ADMIN.

**Corpo (JSON):** [SubjectAssignmentRequest](#subjectassignmentrequest)

**Respostas:** `201` Sucesso — [SubjectAssignmentResponse](#subjectassignmentresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PATCH /api/subjects/{subject_id}`

Editar ou desativar matéria. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `subject_id` | caminho | texto | sim |  |

**Corpo (JSON):** [SubjectUpdateRequest](#subjectupdaterequest)

**Respostas:** `200` Sucesso — [SubjectResponse](#subjectresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `DELETE /api/subjects/{subject_id}`

Desativar matéria. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `subject_id` | caminho | texto | sim |  |

**Respostas:** `204` Sucesso; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/subjects/{subject_id}/classrooms`

Turmas do professor que têm a matéria. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `subject_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — lista de [SubjectClassroomResponse](#subjectclassroomresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/subjects/{subject_id}/classrooms/{classroom_id}/performance`

Desempenho dos alunos na matéria. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `subject_id` | caminho | texto | sim |  |
| `classroom_id` | caminho | texto | sim |  |
| `sortBy` | consulta | `name` \| `grade` | não | padrão: `name` |
| `order` | consulta | `asc` \| `desc` | não | padrão: `asc` |

**Respostas:** `200` Sucesso — lista de [SubjectStudentPerformanceResponse](#subjectstudentperformanceresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Portal do aluno — respostas — detalhe

#### `GET /api/student-portal/activities/{activity_id}/submissions`

Consultar as próprias respostas e a correção. **Acesso:** STUDENT.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Respostas:** `200` Sucesso — [StudentSubmissionResult](#studentsubmissionresult); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `POST /api/student-portal/activities/{activity_id}/submissions`

Enviar respostas (objetivas são corrigidas na hora). **Acesso:** STUDENT.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `activity_id` | caminho | texto | sim |  |

**Corpo (JSON):** [ActivitySubmissionRequest](#activitysubmissionrequest)

**Respostas:** `200` Sucesso — [StudentSubmissionResult](#studentsubmissionresult); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Correção de atividades — detalhe

#### `GET /api/teacher/activity-corrections/pending`

Listar respostas discursivas aguardando correção. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [PendingCorrectionResponse](#pendingcorrectionresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/teacher/activity-corrections/{submission_id}/questions/{question_index}`

Corrigir uma questão discursiva (nota e comentário). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `submission_id` | caminho | texto | sim |  |
| `question_index` | caminho | inteiro | sim |  |

**Corpo (JSON):** [ReviewQuestionRequest](#reviewquestionrequest)

**Respostas:** `200` Sucesso — [StudentSubmissionResult](#studentsubmissionresult); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Correção de atividades (rota antiga) — detalhe

#### `GET /api/teacher/activity_corrections/pending`

Listar respostas discursivas aguardando correção (rota antiga). **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [PendingCorrectionResponse](#pendingcorrectionresponse); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `PUT /api/teacher/activity_corrections/{submission_id}/questions/{question_index}`

Corrigir uma questão discursiva (rota antiga). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `submission_id` | caminho | texto | sim |  |
| `question_index` | caminho | inteiro | sim |  |

**Corpo (JSON):** [ReviewQuestionRequest](#reviewquestionrequest)

**Respostas:** `200` Sucesso — [StudentSubmissionResult](#studentsubmissionresult); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Histórico de operações — detalhe

#### `GET /api/audit-logs`

Histórico de operações (professor: as próprias; admin: todas). **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `entity` | consulta | texto (ou nulo) | não |  |
| `action` | consulta | texto (ou nulo) | não |  |
| `success` | consulta | booleano (ou nulo) | não |  |
| `actor` | consulta | texto (ou nulo) | não |  |
| `q` | consulta | texto (ou nulo) | não | máx. 100 caracteres |
| `from` | consulta | texto (date) (ou nulo) | não |  |
| `to` | consulta | texto (date) (ou nulo) | não |  |
| `page` | consulta | inteiro | não | mín. 0; padrão: `0` |
| `size` | consulta | inteiro | não | mín. 1; máx. 100; padrão: `20` |

**Respostas:** `200` Sucesso — [AuditLogPage](#auditlogpage); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Relatórios — detalhe

#### `GET /api/reports`

Relatórios disponíveis. **Acesso:** TEACHER ou ADMIN.

**Respostas:** `200` Sucesso — lista de [ReportCatalogItem](#reportcatalogitem); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/reports/{report_type}`

Executa um relatório com filtros. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `report_type` | caminho | texto | sim |  |
| `classroomId` | consulta | texto (ou nulo) | não |  |
| `subject` | consulta | texto (ou nulo) | não | máx. 80 caracteres |
| `from` | consulta | texto (date) (ou nulo) | não |  |
| `to` | consulta | texto (date) (ou nulo) | não |  |
| `status` | consulta | texto (ou nulo) | não | máx. 30 caracteres |
| `entity` | consulta | texto (ou nulo) | não | máx. 30 caracteres |
| `action` | consulta | texto (ou nulo) | não | máx. 40 caracteres |

**Respostas:** `200` Sucesso — [ReportResponse](#reportresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

#### `GET /api/reports/{report_type}/export`

Exporta um relatório em CSV, XLSX ou PDF. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `report_type` | caminho | texto | sim |  |
| `format` | consulta | texto | não | formato `^(csv\|xlsx\|pdf)$`; padrão: `csv` |
| `classroomId` | consulta | texto (ou nulo) | não |  |
| `subject` | consulta | texto (ou nulo) | não | máx. 80 caracteres |
| `from` | consulta | texto (date) (ou nulo) | não |  |
| `to` | consulta | texto (date) (ou nulo) | não |  |
| `status` | consulta | texto (ou nulo) | não | máx. 30 caracteres |
| `entity` | consulta | texto (ou nulo) | não | máx. 30 caracteres |
| `action` | consulta | texto (ou nulo) | não | máx. 40 caracteres |

**Respostas:** `200` Sucesso — application/json; `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Dashboard — detalhe

#### `GET /api/dashboard/overview`

Indicadores e gráficos do dashboard. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `classroomId` | consulta | texto (ou nulo) | não |  |
| `subject` | consulta | texto (ou nulo) | não | máx. 80 caracteres |
| `from` | consulta | texto (date) (ou nulo) | não |  |
| `to` | consulta | texto (date) (ou nulo) | não |  |
| `status` | consulta | texto (ou nulo) | não | máx. 30 caracteres |
| `entity` | consulta | texto (ou nulo) | não | máx. 30 caracteres |
| `action` | consulta | texto (ou nulo) | não | máx. 40 caracteres |

**Respostas:** `200` Sucesso — [DashboardResponse](#dashboardresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

### Pesquisa — detalhe

#### `GET /api/search`

Pesquisa global em alunos, turmas e atividades. **Acesso:** TEACHER ou ADMIN.

| Parâmetro | Onde | Tipo | Obrigatório | Limites |
|---|---|---|---|---|
| `q` | consulta | texto | sim | mín. 2 caracteres; máx. 80 caracteres |
| `types` | consulta | texto (ou nulo) | não |  |
| `limit` | consulta | inteiro | não | mín. 1; máx. 100; padrão: `20` |

**Respostas:** `200` Sucesso — [SearchResponse](#searchresponse); `422` Dados inválidos (campo e motivo em `details`); `401` Token ausente, inválido ou expirado; `403` Perfil sem permissão para esta rota.

## Esquemas

Campos dos corpos de requisição e de resposta. "Obrigatório" vale para requisições; nas respostas, campos nulos podem ser omitidos.

### ActivityCreateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `title` | texto | sim | mín. 5 caracteres; máx. 200 caracteres |
| `subject` | texto (ou nulo) | não |  |
| `topic` | texto (ou nulo) | não | mín. 3 caracteres; máx. 100 caracteres |
| `difficultyLevel` | texto | sim |  |
| `questionsCount` | inteiro | sim | mín. 1; máx. 100 |
| `format` | texto | sim |  |
| `classroomId` | texto | sim | mín. 1 caracteres |
| `studentId` | texto (ou nulo) | não |  |
| `disabilityAdaptations` | lista de texto (ou nulo) | não |  |
| `questions` | lista de [GeneratedQuestion](#generatedquestion) (ou nulo) | não |  |
| `content` | texto (ou nulo) | não | máx. 10000 caracteres |
| `pdfUrl` | texto (ou nulo) | não |  |

### ActivityGenerationRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `classroomId` | texto | sim | mín. 1 caracteres |
| `studentId` | texto (ou nulo) | não |  |
| `subject` | texto | sim | mín. 3 caracteres; máx. 50 caracteres |
| `topic` | texto | sim | mín. 3 caracteres; máx. 100 caracteres |
| `difficultyLevel` | texto | sim |  |
| `questionsCount` | inteiro | sim | mín. 1; máx. 50 |
| `format` | texto | sim |  |
| `disabilityAdaptations` | lista de texto | não |  |
| `learningGapId` | texto (ou nulo) | não |  |
| `additionalInstructions` | texto (ou nulo) | não | máx. 500 caracteres |

### ActivityGradesLaunchResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `activityId` | texto | sim |  |
| `activityTitle` | texto | sim |  |
| `launched` | inteiro | sim |  |
| `alreadyLaunched` | inteiro | sim |  |
| `awaitingCorrection` | inteiro | sim |  |
| `notSubmitted` | inteiro | sim |  |

### ActivityParticipant

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `studentName` | texto | sim |  |
| `submittedAt` | texto (date-time) (ou nulo) | não |  |

### ActivityParticipation

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `totalStudents` | inteiro | não | padrão: `0` |
| `completedStudents` | inteiro | não | padrão: `0` |
| `pendingStudents` | inteiro | não | padrão: `0` |
| `completed` | lista de [ActivityParticipant](#activityparticipant) | não |  |
| `pending` | lista de [ActivityParticipant](#activityparticipant) | não |  |

### ActivityResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `title` | texto | sim |  |
| `subject` | texto (ou nulo) | não |  |
| `topic` | texto (ou nulo) | não |  |
| `difficultyLevel` | texto (ou nulo) | não |  |
| `questionsCount` | inteiro (ou nulo) | não |  |
| `format` | texto (ou nulo) | não |  |
| `classroomId` | texto (ou nulo) | não |  |
| `classroomName` | texto (ou nulo) | não |  |
| `studentId` | texto (ou nulo) | não |  |
| `studentName` | texto (ou nulo) | não |  |
| `disabilityAdaptations` | lista de texto | não |  |
| `questions` | lista de [GeneratedQuestion](#generatedquestion) | não |  |
| `content` | texto (ou nulo) | não |  |
| `pdfUrl` | texto (ou nulo) | não |  |
| `generatedByAi` | booleano (ou nulo) | não |  |
| `aiProvider` | texto (ou nulo) | não |  |
| `createdBy` | texto (ou nulo) | não |  |
| `creatorName` | texto (ou nulo) | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |
| `participation` | [ActivityParticipation](#activityparticipation) (ou nulo) | não |  |

### ActivitySubmissionDetailResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `submissionId` | texto | sim |  |
| `studentId` | texto | sim |  |
| `studentName` | texto | sim |  |
| `submittedAt` | texto (date-time) (ou nulo) | não |  |
| `correctCount` | inteiro | sim |  |
| `totalQuestions` | inteiro | sim |  |
| `scorePercent` | inteiro | sim |  |
| `pendingCount` | inteiro | não | padrão: `0` |
| `results` | lista de [QuestionResult](#questionresult) | não |  |

### ActivitySubmissionRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `answers` | lista de [QuestionAnswer](#questionanswer) | sim | mín. 1 itens |

### ActivityUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `title` | texto (ou nulo) | não | mín. 5 caracteres; máx. 200 caracteres |
| `subject` | texto (ou nulo) | não |  |
| `topic` | texto (ou nulo) | não | mín. 3 caracteres; máx. 100 caracteres |
| `difficultyLevel` | texto (ou nulo) | não |  |
| `questionsCount` | inteiro (ou nulo) | não | mín. 1; máx. 100 |
| `format` | texto (ou nulo) | não |  |
| `classroomId` | texto (ou nulo) | não |  |
| `studentId` | texto (ou nulo) | não |  |
| `disabilityAdaptations` | lista de texto (ou nulo) | não |  |
| `questions` | lista de [GeneratedQuestion](#generatedquestion) (ou nulo) | não |  |
| `content` | texto (ou nulo) | não | máx. 10000 caracteres |
| `pdfUrl` | texto (ou nulo) | não |  |

### AtRiskStudent

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `studentName` | texto | sim |  |
| `classroomName` | texto | sim |  |
| `average` | número (ou nulo) | sim |  |
| `attendanceRate` | inteiro (ou nulo) | sim |  |
| `reasons` | lista de texto | sim |  |

### AuditLogPage

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `items` | lista de [AuditLogResponse](#auditlogresponse) | sim |  |
| `total` | inteiro | sim |  |
| `page` | inteiro | sim |  |
| `size` | inteiro | sim |  |
| `totalPages` | inteiro | sim |  |

### AuditLogResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `timestamp` | texto (date-time) | sim |  |
| `actorEmail` | texto (ou nulo) | não |  |
| `actorName` | texto (ou nulo) | não |  |
| `actorRole` | texto (ou nulo) | não |  |
| `action` | texto | sim |  |
| `actionLabel` | texto | sim |  |
| `entity` | texto | sim |  |
| `entityLabel` | texto | sim |  |
| `entityId` | texto (ou nulo) | não |  |
| `method` | texto | sim |  |
| `path` | texto | sim |  |
| `status` | inteiro | sim |  |
| `success` | booleano | sim |  |
| `summary` | texto | sim |  |
| `details` | objeto | não |  |

### AuthenticationRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `email` | texto | sim | mín. 1 caracteres |
| `password` | texto | sim | mín. 1 caracteres |

### AuthenticationResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `accessToken` | texto | sim |  |
| `refreshToken` | texto | sim |  |
| `tokenType` | texto | sim |  |
| `expiresIn` | inteiro | sim |  |
| `userId` | texto | sim |  |
| `userEmail` | texto | sim |  |
| `role` | texto | sim |  |
| `studentId` | texto (ou nulo) | não |  |
| `name` | texto (ou nulo) | não |  |

### ChangePasswordRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `currentPassword` | texto | sim | mín. 1 caracteres; máx. 100 caracteres |
| `newPassword` | texto | sim | mín. 6 caracteres; máx. 100 caracteres |

### ChangePasswordResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `message` | texto | sim |  |

### Classmate

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |

### ClassroomCreateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto | sim | mín. 3 caracteres; máx. 100 caracteres |
| `year` | inteiro | sim |  |
| `gradeLevel` | texto | sim | mín. 1 caracteres |
| `teacherId` | texto | sim | mín. 1 caracteres |
| `studentIds` | lista de texto (ou nulo) | não |  |
| `subjects` | lista de texto (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não | padrão: `True` |

### ClassroomPageResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `content` | lista de [ClassroomResponse](#classroomresponse) | sim |  |
| `totalPages` | inteiro | sim |  |
| `totalElements` | inteiro | sim |  |
| `size` | inteiro | sim |  |
| `number` | inteiro | sim |  |
| `first` | booleano | sim |  |
| `last` | booleano | sim |  |

### ClassroomPerformanceResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `classroomId` | texto | sim |  |
| `averageGrade` | número | sim |  |
| `studentsCount` | inteiro | sim |  |
| `subjectPerformance` | lista de [ClassroomSubjectPerformance](#classroomsubjectperformance) | sim |  |

### ClassroomResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `year` | inteiro | sim |  |
| `gradeLevel` | texto | sim |  |
| `teacherId` | texto | sim |  |
| `teacherName` | texto (ou nulo) | não |  |
| `studentIds` | lista de texto | sim |  |
| `students` | lista de [StudentSummary](#studentsummary) | sim |  |
| `subjects` | lista de texto | sim |  |
| `subjectTeachers` | lista de [SubjectTeacherSummary](#subjectteachersummary) | não |  |
| `active` | booleano (ou nulo) | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |
| `updatedAt` | texto (date-time) (ou nulo) | não |  |

### ClassroomSubjectPerformance

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `subject` | texto | sim |  |
| `average` | número | sim |  |
| `studentsCount` | inteiro | sim |  |

### ClassroomUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto (ou nulo) | não | mín. 3 caracteres; máx. 100 caracteres |
| `year` | inteiro (ou nulo) | não |  |
| `gradeLevel` | texto (ou nulo) | não |  |
| `teacherId` | texto (ou nulo) | não |  |
| `studentIds` | lista de texto (ou nulo) | não |  |
| `subjects` | lista de texto (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não |  |

### DashboardKpis

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `students` | inteiro | sim |  |
| `classrooms` | inteiro | sim |  |
| `activities` | inteiro | sim |  |
| `gradeLaunches` | inteiro | sim |  |
| `averageGrade` | número (ou nulo) | sim |  |
| `attendanceRate` | inteiro (ou nulo) | sim |  |
| `submissionRate` | inteiro (ou nulo) | sim |  |
| `studentsAtRisk` | inteiro | sim |  |

### DashboardResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `generatedAt` | texto (date-time) | sim |  |
| `filters` | objeto | sim |  |
| `kpis` | [DashboardKpis](#dashboardkpis) | sim |  |
| `averageByClassroom` | lista de [NamedAverage](#namedaverage) | sim |  |
| `averageBySubject` | lista de [NamedAverage](#namedaverage) | sim |  |
| `monthlyAverage` | lista de [MonthlyAverage](#monthlyaverage) | sim |  |
| `distribution` | lista de [DistributionBucket](#distributionbucket) | sim |  |
| `participation` | [ParticipationTotals](#participationtotals) | sim |  |
| `atRisk` | lista de [AtRiskStudent](#atriskstudent) | sim |  |
| `recentOperations` | lista de [AuditLogResponse](#auditlogresponse) | sim |  |

### DistributionBucket

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `range` | texto | sim |  |
| `count` | inteiro | sim |  |

### EnableStudentAccessRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `password` | texto | sim | mín. 6 caracteres; máx. 100 caracteres |

### ForgotPasswordRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `email` | texto | sim | mín. 3 caracteres; máx. 254 caracteres |

### ForgotPasswordResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `message` | texto | sim |  |
| `demoCode` | texto (ou nulo) | não |  |

### GeneratedQuestion

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `questionText` | texto | sim |  |
| `questionType` | texto | sim |  |
| `options` | lista de texto | não |  |
| `correctAnswer` | texto (ou nulo) | não |  |
| `explanation` | texto (ou nulo) | não |  |
| `difficultyLevel` | texto (ou nulo) | não |  |

### GradeClassroomSummaryResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `classroomId` | texto | sim |  |
| `classroomName` | texto | sim |  |
| `subject` | texto (ou nulo) | não |  |
| `studentsCount` | inteiro | sim |  |
| `totalLaunches` | inteiro | sim |  |
| `averageGrade` | número | sim |  |
| `attendanceRate` | inteiro | sim |  |
| `students` | lista de [GradeStudentSummary](#gradestudentsummary) | sim |  |

### GradeCreateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim | mín. 1 caracteres |
| `classroomId` | texto | sim | mín. 1 caracteres |
| `grade` | número | sim | mín. 0; máx. 10 |
| `attendance` | booleano (ou nulo) | não |  |
| `subject` | texto (ou nulo) | não |  |
| `activityType` | texto (ou nulo) | não |  |
| `observations` | texto (ou nulo) | não | máx. 500 caracteres |
| `activityId` | texto (ou nulo) | não |  |
| `date` | texto (date-time) | sim |  |

### GradeResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `studentId` | texto | sim |  |
| `classroomId` | texto | sim |  |
| `subject` | texto (ou nulo) | não |  |
| `grade` | número | sim |  |
| `gradeValue` | número | sim |  |
| `attendance` | booleano (ou nulo) | não |  |
| `date` | texto (date-time) | sim |  |
| `activityType` | texto (ou nulo) | não |  |
| `observations` | texto (ou nulo) | não |  |
| `activityId` | texto (ou nulo) | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |

### GradeStudentSummary

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `studentName` | texto | sim |  |
| `average` | número | sim |  |
| `launches` | inteiro | sim |  |
| `totalClasses` | inteiro | sim |  |
| `attendedClasses` | inteiro | sim |  |
| `absences` | inteiro | sim |  |
| `attendanceRate` | inteiro | sim |  |
| `lastLaunchAt` | texto (date-time) (ou nulo) | não |  |

### GradeUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto (ou nulo) | não |  |
| `classroomId` | texto (ou nulo) | não |  |
| `grade` | número (ou nulo) | não | mín. 0; máx. 10 |
| `attendance` | booleano (ou nulo) | não |  |
| `subject` | texto (ou nulo) | não |  |
| `activityType` | texto (ou nulo) | não |  |
| `observations` | texto (ou nulo) | não | máx. 500 caracteres |
| `date` | texto (date-time) (ou nulo) | não |  |

### HealthResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `status` | `ok` \| `degraded` | sim |  |
| `service` | texto | sim |  |
| `version` | texto | sim |  |
| `environment` | texto | sim |  |
| `database` | texto | sim | Estado da conexão MongoDB |
| `timestamp` | texto (date-time) | sim |  |
| `opencl` | objeto | sim | Estado do processamento OpenCL das estatísticas de notas |

### LearningGapInput

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto (ou nulo) | não |  |
| `subject` | texto | sim | mín. 1 caracteres |
| `topic` | texto | sim | mín. 1 caracteres |
| `severityLevel` | texto (ou nulo) | não |  |
| `description` | texto (ou nulo) | não |  |
| `identifiedAt` | texto (date-time) (ou nulo) | não |  |
| `lastAssessedAt` | texto (date-time) (ou nulo) | não |  |
| `improved` | booleano (ou nulo) | não |  |
| `improvementStatus` | texto (ou nulo) | não |  |

### LearningGapResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto (ou nulo) | não |  |
| `subject` | texto | sim |  |
| `topic` | texto | sim |  |
| `severityLevel` | texto (ou nulo) | não |  |
| `description` | texto (ou nulo) | não |  |
| `identifiedAt` | texto (date-time) (ou nulo) | não |  |
| `lastAssessedAt` | texto (date-time) (ou nulo) | não |  |
| `improved` | booleano (ou nulo) | não |  |

### MonthlyAverage

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `month` | texto | sim |  |
| `average` | número | sim |  |
| `launches` | inteiro | sim |  |

### NamedAverage

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto (ou nulo) | não |  |
| `name` | texto | sim |  |
| `average` | número | sim |  |
| `attendanceRate` | inteiro (ou nulo) | não |  |
| `launches` | inteiro | sim |  |

### ParticipationTotals

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `delivered` | inteiro | sim |  |
| `pending` | inteiro | sim |  |

### PedagogicalRecommendationResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `studentName` | texto | sim |  |
| `priority` | texto | sim |  |
| `recommendedSubject` | texto | sim |  |
| `recommendedTopic` | texto | sim |  |
| `recommendedDifficulty` | texto | sim |  |
| `recommendedQuestionsCount` | inteiro | sim |  |
| `rationale` | texto | sim |  |
| `evidences` | lista de [RecommendationEvidence](#recommendationevidence) | sim |  |
| `generatedAt` | texto (date-time) | sim |  |

### PendingCorrectionResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `submissionId` | texto | sim |  |
| `activityId` | texto | sim |  |
| `activityTitle` | texto | sim |  |
| `subject` | texto (ou nulo) | não |  |
| `topic` | texto (ou nulo) | não |  |
| `classroomName` | texto (ou nulo) | não |  |
| `studentId` | texto | sim |  |
| `studentName` | texto | sim |  |
| `submittedAt` | texto (date-time) (ou nulo) | não |  |
| `questions` | lista de [PendingQuestionResponse](#pendingquestionresponse) | não |  |

### PendingQuestionResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `questionIndex` | inteiro | sim |  |
| `questionText` | texto | sim |  |
| `selectedAnswer` | texto | sim |  |
| `reviewStatus` | texto | não | padrão: `PENDING` |

### PendingTeacherResponse

Cadastro público de professor aguardando aprovação do ADMIN.

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `email` | texto | sim |  |
| `subjects` | lista de texto | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |

### ProfileUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto | sim | mín. 1 caracteres; máx. 120 caracteres |
| `email` | texto | sim | mín. 3 caracteres; máx. 254 caracteres |

### QuestionAnswer

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `questionIndex` | inteiro | sim | mín. 0 |
| `selectedAnswer` | texto (ou nulo) | não |  |

### QuestionResult

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `questionIndex` | inteiro | sim |  |
| `questionText` | texto | sim |  |
| `questionType` | texto | sim |  |
| `options` | lista de texto | não |  |
| `selectedAnswer` | texto (ou nulo) | não |  |
| `correctAnswer` | texto (ou nulo) | não |  |
| `correct` | booleano | sim |  |
| `reviewStatus` | texto | não | padrão: `AUTO_GRADED` |
| `teacherFeedback` | texto (ou nulo) | não |  |
| `reviewedBy` | texto (ou nulo) | não |  |
| `reviewedAt` | texto (date-time) (ou nulo) | não |  |

### RecommendationEvidence

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `signal` | texto | sim |  |
| `detail` | texto | sim |  |
| `weight` | número | sim |  |

### RefreshTokenRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `refreshToken` | texto | sim | mín. 1 caracteres; Refresh token recebido no login (validade de 7 dias por padrão) |

### ReportCatalogItem

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `type` | texto | sim |  |
| `title` | texto | sim |  |
| `description` | texto | sim |  |
| `statusOptions` | lista de objeto | não |  |

### ReportColumn

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `key` | texto | sim |  |
| `label` | texto | sim |  |
| `type` | texto | não | padrão: `text` |

### ReportResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `type` | texto | sim |  |
| `title` | texto | sim |  |
| `description` | texto | sim |  |
| `generatedAt` | texto (date-time) | sim |  |
| `filters` | objeto | não |  |
| `columns` | lista de [ReportColumn](#reportcolumn) | sim |  |
| `rows` | lista de objeto | sim |  |
| `summary` | lista de [ReportSummaryItem](#reportsummaryitem) | não |  |
| `total` | inteiro | sim |  |

### ReportSummaryItem

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `label` | texto | sim |  |
| `value` | texto | sim |  |

### ResetPasswordRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `email` | texto | sim | mín. 3 caracteres; máx. 254 caracteres |
| `code` | texto | sim | mín. 6 caracteres; máx. 6 caracteres |
| `newPassword` | texto | sim | mín. 6 caracteres; máx. 100 caracteres |

### ResetPasswordResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `message` | texto | sim |  |

### ReviewQuestionRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `correct` | booleano | sim |  |
| `feedback` | texto (ou nulo) | não | máx. 2000 caracteres |

### SearchHit

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `type` | texto | sim |  |
| `id` | texto | sim |  |
| `title` | texto | sim |  |
| `subtitle` | texto (ou nulo) | não |  |
| `url` | texto | sim |  |

### SearchResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `query` | texto | sim |  |
| `total` | inteiro | sim |  |
| `results` | lista de [SearchHit](#searchhit) | sim |  |

### StudentActivity

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `title` | texto | sim |  |
| `subject` | texto | sim |  |
| `topic` | texto | sim |  |
| `difficultyLevel` | texto | sim |  |
| `format` | texto | sim |  |
| `classroomId` | texto (ou nulo) | não |  |
| `classroomName` | texto (ou nulo) | não |  |
| `submitted` | booleano | sim |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |

### StudentActivityDetail

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `title` | texto | sim |  |
| `subject` | texto | sim |  |
| `topic` | texto | sim |  |
| `difficultyLevel` | texto | sim |  |
| `format` | texto | sim |  |
| `classroomName` | texto (ou nulo) | não |  |
| `submitted` | booleano | sim |  |
| `questions` | lista de [StudentQuestion](#studentquestion) | não |  |
| `correctCount` | inteiro (ou nulo) | não |  |
| `totalQuestions` | inteiro (ou nulo) | não |  |
| `scorePercent` | inteiro (ou nulo) | não |  |
| `pendingCount` | inteiro (ou nulo) | não |  |
| `results` | lista de qualquer | não |  |
| `submittedAt` | texto (date-time) (ou nulo) | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |

### StudentAttendanceResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `attendanceRate` | inteiro | sim |  |
| `totalClasses` | inteiro | sim |  |
| `attendedClasses` | inteiro | sim |  |
| `absences` | inteiro | sim |  |

### StudentClassroom

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `year` | inteiro | sim |  |
| `gradeLevel` | texto | sim |  |
| `subjects` | lista de texto | não |  |

### StudentCreateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto | sim | mín. 3 caracteres; máx. 100 caracteres |
| `email` | texto | sim | mín. 1 caracteres |
| `birthDate` | texto (ou nulo) | não |  |
| `classId` | texto (ou nulo) | não |  |
| `learningGaps` | lista de [LearningGapInput](#learninggapinput) (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não | padrão: `True` |

### StudentPageResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `content` | lista de [StudentResponse](#studentresponse) | sim |  |
| `totalPages` | inteiro | sim |  |
| `totalElements` | inteiro | sim |  |
| `size` | inteiro | sim |  |
| `number` | inteiro | sim |  |
| `first` | booleano | sim |  |
| `last` | booleano | sim |  |

### StudentPerformanceResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `averageGrade` | número | sim |  |
| `totalActivities` | inteiro | sim |  |
| `completedActivities` | inteiro | sim |  |
| `subjectPerformance` | lista de [SubjectPerformance](#subjectperformance) | sim |  |

### StudentPortalPerformance

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `averageGrade` | número | sim |  |
| `totalActivities` | inteiro | sim |  |
| `completedActivities` | inteiro | sim |  |
| `subjectPerformance` | lista de [SubjectPerformance](#subjectperformance) | não |  |
| `attendanceRate` | inteiro | sim |  |
| `totalClasses` | inteiro | sim |  |
| `attendedClasses` | inteiro | sim |  |
| `absences` | inteiro | sim |  |

### StudentPortalProfile

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `userId` | texto (ou nulo) | não |  |
| `name` | texto | sim |  |
| `email` | texto | sim |  |
| `classId` | texto (ou nulo) | não |  |
| `className` | texto (ou nulo) | não |  |

### StudentQuestion

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `questionIndex` | inteiro | sim |  |
| `questionText` | texto | sim |  |
| `questionType` | texto | sim |  |
| `options` | lista de texto | não |  |

### StudentRegistrationRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto | sim | mín. 3 caracteres; máx. 120 caracteres |
| `email` | texto | sim | mín. 3 caracteres; máx. 254 caracteres |
| `password` | texto | sim | mín. 6 caracteres; máx. 100 caracteres |

### StudentResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `email` | texto | sim |  |
| `matricula` | texto (ou nulo) | não |  |
| `birthDate` | texto (ou nulo) | não |  |
| `learningGaps` | lista de [LearningGapResponse](#learninggapresponse) (ou nulo) | não |  |
| `classId` | texto (ou nulo) | não |  |
| `className` | texto (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |
| `updatedAt` | texto (date-time) (ou nulo) | não |  |

### StudentSubmissionResult

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `correctCount` | inteiro | sim |  |
| `totalQuestions` | inteiro | sim |  |
| `scorePercent` | inteiro | sim |  |
| `pendingCount` | inteiro | não | padrão: `0` |
| `results` | lista de [QuestionResult](#questionresult) | sim |  |

### StudentSummary

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `learningGaps` | lista de [LearningGapResponse](#learninggapresponse) (ou nulo) | não |  |

### StudentUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto (ou nulo) | não | mín. 3 caracteres; máx. 100 caracteres |
| `email` | texto (ou nulo) | não |  |
| `birthDate` | texto (ou nulo) | não |  |
| `classId` | texto (ou nulo) | não |  |
| `learningGaps` | lista de [LearningGapInput](#learninggapinput) (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não |  |

### SubjectAssignmentRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `classroomId` | texto | sim | mín. 1 caracteres |
| `subjectId` | texto | sim | mín. 1 caracteres |

### SubjectAssignmentResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `classroomId` | texto | sim |  |
| `subjectId` | texto | sim |  |
| `subjectName` | texto | sim |  |
| `teacherId` | texto | sim |  |
| `teacherName` | texto (ou nulo) | não |  |

### SubjectClassroomResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `year` | inteiro (ou nulo) | não |  |
| `gradeLevel` | texto (ou nulo) | não |  |
| `studentCount` | inteiro | não | padrão: `0` |
| `averageGrade` | número | não | padrão: `0` |

### SubjectCreateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto | sim | mín. 2 caracteres; máx. 80 caracteres |
| `area` | texto (ou nulo) | não | máx. 80 caracteres |
| `gradeLevels` | lista de texto (ou nulo) | não |  |

### SubjectPerformance

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `subject` | texto | sim |  |
| `average` | número | sim |  |
| `count` | inteiro | sim |  |

### SubjectResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `active` | booleano | sim |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |
| `updatedAt` | texto (date-time) (ou nulo) | não |  |
| `area` | texto (ou nulo) | não |  |
| `gradeLevels` | lista de texto (ou nulo) | não |  |
| `curriculumKey` | texto (ou nulo) | não |  |

### SubjectStudentPerformanceResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `studentId` | texto | sim |  |
| `studentName` | texto | sim |  |
| `studentEmail` | texto (ou nulo) | não |  |
| `averageGrade` | número | não | padrão: `0` |
| `gradeCount` | inteiro | não | padrão: `0` |
| `lastGrade` | número (ou nulo) | não |  |

### SubjectTeacherSummary

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `subjectId` | texto | sim |  |
| `subjectName` | texto | sim |  |
| `teacherId` | texto | sim |  |
| `teacherName` | texto (ou nulo) | não |  |

### SubjectTopicCreateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `subject` | texto | sim | mín. 2 caracteres; máx. 80 caracteres |
| `topic` | texto (ou nulo) | não | mín. 2 caracteres; máx. 120 caracteres |

### SubjectTopicResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `subject` | texto | sim |  |
| `topics` | lista de texto | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |
| `updatedAt` | texto (date-time) (ou nulo) | não |  |

### SubjectTopicUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `subject` | texto | sim | mín. 2 caracteres; máx. 80 caracteres |
| `topics` | lista de texto | não | máx. 100 itens |

### SubjectUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `active` | booleano (ou nulo) | não |  |

### TeacherCreateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto | sim | mín. 3 caracteres; máx. 120 caracteres |
| `email` | texto | sim | mín. 3 caracteres; máx. 254 caracteres |
| `password` | texto | sim | mín. 6 caracteres; máx. 100 caracteres |
| `subjects` | lista de texto (ou nulo) | não |  |
| `classroomIds` | lista de texto (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não | padrão: `True` |

### TeacherRegistrationPendingResponse

Resposta do cadastro público de professor quando a aprovação do ADMIN é exigida.

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `status` | texto | sim | Sempre "PENDING_APPROVAL" |
| `message` | texto | sim |  |
| `userEmail` | texto | sim |  |
| `name` | texto | sim |  |

### TeacherRegistrationRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto | sim | mín. 3 caracteres; máx. 120 caracteres |
| `email` | texto | sim | mín. 3 caracteres; máx. 254 caracteres |
| `password` | texto | sim | mín. 6 caracteres; máx. 100 caracteres |
| `subjects` | lista de texto | não | máx. 50 itens |

### TeacherResponse

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `email` | texto | sim |  |
| `subjects` | lista de texto (ou nulo) | não |  |
| `classroomIds` | lista de texto (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não |  |
| `createdAt` | texto (date-time) (ou nulo) | não |  |
| `updatedAt` | texto (date-time) (ou nulo) | não |  |

### TeacherSummary

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `id` | texto | sim |  |
| `name` | texto | sim |  |
| `email` | texto | sim |  |
| `subjects` | lista de texto | não |  |

### TeacherUpdateRequest

| Campo | Tipo | Obrigatório | Limites / observação |
|---|---|---|---|
| `name` | texto (ou nulo) | não | mín. 3 caracteres; máx. 120 caracteres |
| `email` | texto (ou nulo) | não | mín. 3 caracteres; máx. 254 caracteres |
| `password` | texto (ou nulo) | não | mín. 6 caracteres; máx. 100 caracteres |
| `subjects` | lista de texto (ou nulo) | não |  |
| `classroomIds` | lista de texto (ou nulo) | não |  |
| `active` | booleano (ou nulo) | não |  |
