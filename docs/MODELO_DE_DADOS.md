# Modelo de dados (MongoDB)

Gerado em 03/11/2026 a partir das coleções reais do banco de avaliação (`pluseduc_sprint9_eval`, cópia do `escola_db`) por `docs/sprint-09/scripts/gerar_modelo_dados.py`.
Mostra os nomes e os tipos dos campos encontrados, nunca os valores. "Presença" é a parcela dos documentos que traz o campo.
O banco não tem esquema fixo (MongoDB): as regras de integridade estão nos serviços da API, não no banco.

## Visão geral das coleções

| Coleção | Documentos | Para que serve |
|---|---:|---|
| `activities` | 38 | Atividades (objetivas e discursivas); o conteúdo das questões, com o gabarito, fica em content. |
| `activity_submissions` | 99 | Respostas dos alunos e o resultado da correção (content). Índice único (activity_id, student_id) impede reenvio. |
| `audit_logs` | 703 | Histórico de operações que alteram dados: autor, ação, entidade, resultado e antes/depois das notas. |
| `classrooms` | 22 | Turmas: série, ano letivo, alunos matriculados e o professor responsável por cada matéria (subjectTeachers). |
| `grades` | 234 | Notas e presença (um documento por lançamento). Pode apontar para a atividade que a originou (activityId). |
| `students` | 79 | Cadastro pedagógico do aluno (matrícula, turma, lacunas de aprendizagem). Exclusão lógica (active=false). |
| `subject_topics` | 1 | Tópicos sugeridos por matéria, usados na criação de atividades. |
| `subjects` | 21 | Catálogo de matérias (componentes curriculares) ativas e inativas. |
| `teachers` | 20 | Cadastro do professor (disciplinas, turmas). A senha fica em bcrypt; o login usado é o documento de users. |
| `users` | 100 | Contas de acesso (login). Um documento por pessoa que entra no sistema; o papel (role) decide as permissões. |

## Relações entre as coleções

| Campo | Aponta para | Significado |
|---|---|---|
| `students.class_id` | `classrooms._id` | turma do aluno (a lista classrooms.students[] guarda a mesma matrícula) |
| `students.user_id / users.studentId` | `users._id / students._id` | login do aluno |
| `classrooms.teacher_id` | `teachers._id` | professor responsável pela turma |
| `classrooms.subjectTeachers[].subjectId / teacherId` | `subjects._id / teachers._id` | um professor por matéria na turma (RF08) |
| `activities.classroom_id / student_id / created_by` | `classrooms._id / students._id / users._id` | turma da atividade, aluno específico (opcional) e autor |
| `activity_submissions.activity_id / student_id` | `activities._id / students._id` | resposta de um aluno a uma atividade |
| `grades.studentId / classroomId / activityId` | `students._id / classrooms._id / activities._id` | nota do aluno na turma, opcionalmente vinda de uma atividade |
| `audit_logs.actorId / entityId` | `users._id / qualquer coleção` | quem fez e sobre qual registro |
| `teachers.email = users.email` | `—` | o login do professor é o documento de users com o mesmo e-mail |

## Pontos de atenção do modelo (débitos conhecidos)

* **Nomes misturados:** os dados mais antigos usam `snake_case` (`class_id`, `created_at`) e os mais novos `camelCase` (`studentId`, `createdAt`), às vezes na mesma coleção. A API aceita as duas formas; a padronização exige migração.
* **Matrícula em dois lugares:** `students.class_id` e `classrooms.students[]`. A API mantém os dois ao matricular, desmatricular e excluir aluno, mas criar aluno já com `classId` preenche só o primeiro.
* **Ids como texto:** referências entre coleções são gravadas como texto (24 caracteres), enquanto `_id` é `ObjectId`; as consultas testam as duas formas.
* **Gabarito dentro da atividade:** `activities.content` guarda as questões com a resposta correta; a proteção é feita na API (o portal do aluno remove o gabarito).
* **Datas de notas** antigas estão como texto ISO e as novas como data/hora; os serviços normalizam as duas formas.

## Detalhe por coleção

### `activities`

Atividades (objetivas e discursivas); o conteúdo das questões, com o gabarito, fica em content.

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_class` | str | 8% |
| `_id` | ObjectId | 100% |
| `ai_provider` | str | 92% |
| `classroom_id` | str | 100% |
| `content` | str | 100% |
| `created_at` | datetime | 100% |
| `created_by` | str | 92% |
| `demo_population_key` | str | 79% |
| `difficulty_level` | str | 100% |
| `disability_adaptations` | list | 100% |
| `format` | str | 100% |
| `generated_by_ai` | bool | 100% |
| `pdf_url` | NoneType | 3% |
| `questions_count` | int | 100% |
| `student_id` | str | 11% |
| `subject` | str | 100% |
| `title` | str | 100% |
| `topic` | str | 100% |

Índices: `_id_` [('_id', 1)]; `classroom_id_1` [('classroom_id', 1)]; `student_id_1` [('student_id', 1)]; `created_at_-1` [('created_at', -1)]; `classroomId_1` [('classroomId', 1)]; `studentId_1` [('studentId', 1)]; `created_by_1` [('created_by', 1)]

### `activity_submissions`

Respostas dos alunos e o resultado da correção (content). Índice único (activity_id, student_id) impede reenvio.

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_class` | str | 2% |
| `_id` | ObjectId | 100% |
| `activity_id` | str | 100% |
| `content` | str, dict | 100% |
| `content.answers` | list | 5% |
| `content.correctCount` | int | 5% |
| `content.pendingCount` | int | 5% |
| `content.results` | list | 5% |
| `content.scorePercent` | int | 5% |
| `content.totalQuestions` | int | 5% |
| `demo_population_key` | str | 93% |
| `student_id` | str | 100% |
| `submitted_at` | datetime | 100% |

Índices: `_id_` [('_id', 1)]; `submissions_activity_student_unique` (único) [('activity_id', 1), ('student_id', 1)]; `activity_id_1` [('activity_id', 1)]; `activityId_1` [('activityId', 1)]; `student_id_1` [('student_id', 1)]; `studentId_1` [('studentId', 1)]

### `audit_logs`

Histórico de operações que alteram dados: autor, ação, entidade, resultado e antes/depois das notas.

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `action` | str | 100% |
| `actorEmail` | str, NoneType | 100% |
| `actorId` | str, NoneType | 100% |
| `actorName` | NoneType, str | 100% |
| `actorRole` | str, NoneType | 100% |
| `details` | dict | 100% |
| `details.activityId` | str | 1% |
| `details.activityTitle` | str | 1% |
| `details.after` | dict | 3% |
| `details.alreadyLaunched` | int | 1% |
| `details.awaitingCorrection` | int | 1% |
| `details.before` | dict | 2% |
| `details.classroomId` | str | 10% |
| `details.fields` | list | 1% |
| `details.launched` | int | 1% |
| `details.name` | str | 12% |
| `details.notSubmitted` | int | 1% |
| `details.studentId` | str | 7% |
| `details.subject` | str | 3% |
| `details.submissionsRemoved` | int | 1% |
| `details.title` | str | 4% |
| `details.year` | int | 7% |
| `entity` | str | 100% |
| `entityId` | NoneType, str | 100% |
| `ip` | str | 100% |
| `method` | str | 100% |
| `path` | str | 100% |
| `status` | int | 100% |
| `success` | bool | 100% |
| `summary` | str | 100% |
| `timestamp` | datetime | 100% |

Índices: `_id_` [('_id', 1)]; `audit_timestamp_desc` [('timestamp', -1)]; `audit_actor_timestamp` [('actorId', 1), ('timestamp', -1)]; `audit_entity_action` [('entity', 1), ('action', 1)]

### `classrooms`

Turmas: série, ano letivo, alunos matriculados e o professor responsável por cada matéria (subjectTeachers).

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `active` | bool | 100% |
| `created_at` | datetime | 100% |
| `grade_level` | str | 100% |
| `name` | str | 100% |
| `students` | list | 100% |
| `subjectTeachers` | list | 100% |
| `subjects` | list | 100% |
| `teacher_id` | str | 100% |
| `updated_at` | datetime | 100% |
| `year` | int | 100% |

Índices: `_id_` [('_id', 1)]; `teacher_id_1` [('teacher_id', 1)]; `year_1` [('year', 1)]; `active_1` [('active', 1)]; `students_1` [('students', 1)]

### `grades`

Notas e presença (um documento por lançamento). Pode apontar para a atividade que a originou (activityId).

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `activityId` | str | 0% |
| `activityType` | str | 100% |
| `attendance` | bool | 100% |
| `classroomId` | str | 100% |
| `createdAt` | datetime | 1% |
| `created_at` | datetime | 99% |
| `date` | str, datetime | 100% |
| `demo_population_key` | str | 99% |
| `grade` | float | 100% |
| `observations` | str | 100% |
| `studentId` | str | 100% |
| `subject` | str | 100% |

Índices: `_id_` [('_id', 1)]; `student_id_1` [('student_id', 1)]; `classroom_id_1` [('classroom_id', 1)]; `date_-1` [('date', -1)]; `studentId_1` [('studentId', 1)]; `classroomId_1` [('classroomId', 1)]; `activityId_1` [('activityId', 1)]

### `students`

Cadastro pedagógico do aluno (matrícula, turma, lacunas de aprendizagem). Exclusão lógica (active=false).

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `active` | bool | 100% |
| `birth_date` | datetime, str | 96% |
| `class_id` | str | 99% |
| `created_at` | datetime | 100% |
| `created_by` | str | 100% |
| `demo_population_key` | str | 87% |
| `email` | str | 100% |
| `learning_gaps` | list | 100% |
| `matricula` | str | 100% |
| `name` | str | 100% |
| `password` | str | 3% |
| `updated_at` | datetime | 100% |
| `updated_by` | str | 100% |
| `user_id` | str | 100% |

Índices: `_id_` [('_id', 1)]; `email_1` (único) [('email', 1)]; `class_id_1` [('class_id', 1)]; `active_1` [('active', 1)]; `learning_gaps.subject_1` [('learning_gaps.subject', 1)]; `classId_1` [('classId', 1)]; `learningGaps.subject_1` [('learningGaps.subject', 1)]; `students_matricula_unique` (único) [('matricula', 1)]

### `subject_topics`

Tópicos sugeridos por matéria, usados na criação de atividades.

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `created_at` | datetime | 100% |
| `created_by` | str | 100% |
| `owner_key` | str | 100% |
| `subject` | str | 100% |
| `subject_normalized` | str | 100% |
| `topics` | list | 100% |
| `updated_at` | datetime | 100% |

Índices: `_id_` [('_id', 1)]

### `subjects`

Catálogo de matérias (componentes curriculares) ativas e inativas.

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `active` | bool | 100% |
| `area` | str | 71% |
| `created_at` | datetime | 100% |
| `created_by` | str | 29% |
| `curriculum_key` | str | 71% |
| `grade_levels` | list | 71% |
| `name` | str | 100% |
| `name_normalized` | str | 100% |
| `updated_at` | datetime | 100% |

Índices: `_id_` [('_id', 1)]; `subjects_name_normalized_active_unique` (único) [('name_normalized', 1)]

### `teachers`

Cadastro do professor (disciplinas, turmas). A senha fica em bcrypt; o login usado é o documento de users.

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `active` | bool | 100% |
| `classrooms` | list | 100% |
| `created_at` | datetime | 100% |
| `created_by` | str | 10% |
| `email` | str | 100% |
| `name` | str | 100% |
| `password` | str | 15% |
| `subjects` | list | 100% |
| `updated_at` | datetime | 100% |
| `updated_by` | str | 10% |

Índices: `_id_` [('_id', 1)]; `email_1` [('email', 1)]

### `users`

Contas de acesso (login). Um documento por pessoa que entra no sistema; o papel (role) decide as permissões.

| Campo | Tipo(s) | Presença |
|---|---|---:|
| `_id` | ObjectId | 100% |
| `active` | bool | 100% |
| `createdAt` | datetime | 8% |
| `created_at` | datetime | 92% |
| `created_by` | str | 69% |
| `email` | str | 100% |
| `name` | str | 19% |
| `password` | str | 100% |
| `passwordResetAttempts` | int | 1% |
| `passwordResetCodeHash` | str | 1% |
| `passwordResetExpiresAt` | datetime | 1% |
| `role` | str | 100% |
| `studentId` | str | 79% |
| `teacherId` | str | 15% |
| `updatedAt` | datetime | 4% |
| `updated_at` | datetime | 93% |

Índices: `_id_` [('_id', 1)]; `email_1` (único) [('email', 1)]; `active_1` [('active', 1)]
