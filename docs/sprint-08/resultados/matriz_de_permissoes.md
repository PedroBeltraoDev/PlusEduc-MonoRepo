# Matriz de permissões por rota (resultado real)

Código HTTP obtido ao chamar cada uma das 94 rotas da API como anônimo, aluno, professor e administrador, contra o backend em execução.
Rotas de leitura (GET) usam ids reais; as de escrita usam ids inexistentes e corpo vazio. Para quem tem permissão o resultado é 404/422
(passou pela autorização e falhou na validação, sem alterar dados) e para quem não tem é 401/403. "—" = rota não exercitada (login e recuperação de senha).
Quando o resultado mudou por causa das correções da Sprint 08, o valor anterior aparece em "(antes: ...)".

| Método | Rota | Perfil exigido | Anônimo | Aluno | Professor | Admin |
|---|---|---|---|---|---|---|
| GET | `/api/activities` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/activities` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/activities/classroom/{classroom_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/activities/generate` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/activities/student/{student_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/activities/teacher/{teacher_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| DELETE | `/api/activities/{activity_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/activities/{activity_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| PUT | `/api/activities/{activity_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/activities/{activity_id}/export-pdf` | qualquer autenticado | 401 | 403 | 200 | 200 |
| GET | `/api/activities/{activity_id}/submissions` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/audit-logs` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/auth/forgot-password` | público | — | — | — | — |
| POST | `/api/auth/login` | público | — | — | — | — |
| PUT | `/api/auth/profile` | qualquer autenticado | 401 | 422 | 422 | 422 |
| POST | `/api/auth/register/student` | público | 422 | 422 | 422 | 422 |
| POST | `/api/auth/register/teacher` | público | 422 | 422 | 422 | 422 |
| POST | `/api/auth/reset-password` | público | — | — | — | — |
| GET | `/api/classrooms` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/classrooms` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/classrooms/paginated` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/classrooms/student/{student_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/classrooms/teacher/{teacher_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/classrooms/year/{year}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| DELETE | `/api/classrooms/{classroom_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/classrooms/{classroom_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| PUT | `/api/classrooms/{classroom_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| POST | `/api/classrooms/{classroom_id}/enroll/{student_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/classrooms/{classroom_id}/performance` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| DELETE | `/api/classrooms/{classroom_id}/unenroll/{student_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/dashboard/overview` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/grades` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/grades` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/grades/classroom/{classroom_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/grades/classroom/{classroom_id}/summary` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/grades/from-activity/{activity_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/grades/student/{student_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/grades/student/{student_id}/average` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| DELETE | `/api/grades/{grade_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/grades/{grade_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| PUT | `/api/grades/{grade_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/reports` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/reports/{report_type}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/reports/{report_type}/export` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/search` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/student-portal/activities` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/activities/{activity_id}` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/activities/{activity_id}/export-pdf` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/activities/{activity_id}/submissions` | STUDENT | 401 | 200 | 403 | 403 |
| POST | `/api/student-portal/activities/{activity_id}/submissions` | STUDENT | 401 | 422 | 403 | 403 |
| GET | `/api/student-portal/classmates` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/classroom` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/grades` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/me` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/performance` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/student-portal/teachers` | STUDENT | 401 | 200 | 403 | 403 |
| GET | `/api/students` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/students` | TEACHER/ADMIN | 401 | 403 | 422 | 422 (antes: 401/403/422/403) |
| GET | `/api/students/class/{class_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/students/learning-gap/{subject}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/students/paginated` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/students/unassigned` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| DELETE | `/api/students/{student_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 (antes: 401/403/404/403) |
| GET | `/api/students/{student_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| PUT | `/api/students/{student_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 (antes: 401/403/404/403) |
| GET | `/api/students/{student_id}/attendance` | qualquer autenticado | 401 | 200 | 200 | 200 |
| POST | `/api/students/{student_id}/enable-access` | TEACHER/ADMIN | 401 | 403 | 422 | 422 (antes: 401/403/422/403) |
| GET | `/api/students/{student_id}/pedagogical-recommendation` | qualquer autenticado | 401 | 200 | 200 | 200 |
| GET | `/api/students/{student_id}/performance` | qualquer autenticado | 401 | 200 | 200 | 200 |
| GET | `/api/subject-topics` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/subject-topics` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| DELETE | `/api/subject-topics/{item_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| PUT | `/api/subject-topics/{item_id}` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/subjects` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/subjects` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| POST | `/api/subjects/assignments` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/subjects/available` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| DELETE | `/api/subjects/{subject_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| PATCH | `/api/subjects/{subject_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/subjects/{subject_id}/classrooms` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/subjects/{subject_id}/classrooms/{classroom_id}/performance` | TEACHER/ADMIN | 401 | 403 | 200 | 404 |
| GET | `/api/teacher/activity-corrections/pending` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| PUT | `/api/teacher/activity-corrections/{submission_id}/questions/{question_index}` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/teacher/activity_corrections/pending` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| PUT | `/api/teacher/activity_corrections/{submission_id}/questions/{question_index}` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/teachers` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| POST | `/api/teachers` | TEACHER/ADMIN | 401 | 403 | 422 | 422 |
| GET | `/api/teachers/count` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/teachers/email/{email}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| GET | `/api/teachers/subject/{subject}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| DELETE | `/api/teachers/{teacher_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/api/teachers/{teacher_id}` | TEACHER/ADMIN | 401 | 403 | 200 | 200 |
| PUT | `/api/teachers/{teacher_id}` | TEACHER/ADMIN | 401 | 403 | 404 | 404 |
| GET | `/health` | público | 200 | 200 | 200 | 200 |
