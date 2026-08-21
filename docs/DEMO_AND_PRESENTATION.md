# PlusEduc — Dados de demonstração e roteiro de apresentação

## 1. Objetivo do documento

Este documento descreve o estado dos dados locais de demonstração, o roteiro recomendado para apresentar o PlusEduc e os critérios utilizados para validar a consistência do ambiente. O objetivo é permitir uma demonstração reproduzível dos fluxos de professor, aluno, currículo, atividades, notas e recomendações pedagógicas.

> **Importante:** as senhas das contas de demonstração são credenciais locais e não devem ser armazenadas no Git. A lista de acessos deve ser mantida fora do repositório e compartilhada apenas durante a apresentação.

## 2. Visão geral da solução

O PlusEduc é uma aplicação educacional composta por um frontend React e um backend FastAPI/Python. O backend mantém compatibilidade com o contrato consumido pelo frontend, utiliza autenticação JWT com BCrypt e persiste os dados no MongoDB local. A aplicação contempla gerenciamento de alunos, professores e turmas, currículo por série, notas, desempenho, atividades, submissões, recomendações pedagógicas, exportação PDF e portal do aluno.

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| Interface | React, TypeScript e Vite | Painéis do professor e do aluno, formulários e visualizações |
| API | FastAPI e Python | Autenticação, regras de negócio e endpoints REST |
| Persistência | MongoDB local | Usuários, estudantes, professores, turmas, matérias, notas e atividades |
| Segurança | JWT Bearer e BCrypt | Login, roles e proteção dos endpoints |
| IA | Gemini com fallback determinístico | Geração econômica de atividades e continuidade da demonstração |

## 3. Estado validado do banco local

A auditoria foi executada somente leitura contra `mongodb://localhost:27017`, banco `escola_db`. Após a preparação dos acessos, todos os vínculos de alunos com usuários foram confirmados.

| Collection | Quantidade validada | Finalidade |
|---|---:|---|
| `users` | 26 | Contas autenticáveis de professores e alunos |
| `teachers` | 18 | Perfis de professores e disciplinas associadas |
| `students` | 8 | Alunos ativos com matrículas sequenciais |
| `classrooms` | 15 | Turmas curriculares e turmas históricas/de teste |
| `subjects` | 16 | Catálogo de matérias curriculares |
| `subject_topics` | 1 | Tópico cadastrado no catálogo simplificado |
| `activities` | 7 | Atividades persistidas para demonstração |
| `activity_submissions` | 6 | Submissões já realizadas por alunos |
| `grades` | 1 | Registro real de nota para demonstrar desempenho |

A validação encontrou **zero alunos sem usuário**, **zero professores sem usuário**, **zero turmas com aluno inexistente**, **zero turmas com professor inexistente**, **zero e-mails duplicados** e **zero matrículas duplicadas**. As turmas curriculares possuem matérias adequadas à série e não apresentam duplicidade de matéria no vínculo `subjectTeachers`.

## 4. Matrículas disponíveis

As matrículas dos alunos estão organizadas de forma sequencial no padrão `MAT-2026-NNNN`.

| Matrícula | Perfil |
|---|---|
| `MAT-2026-0001` | Henrique Lopes Silva |
| `MAT-2026-0002` | Ana Beatriz Costa |
| `MAT-2026-0003` | Bruno Henrique Alves |
| `MAT-2026-0004` | Camila Oliveira Santos |
| `MAT-2026-0005` | Diego Martins Rocha |
| `MAT-2026-0006` | Elisa Ferreira Lima |
| `MAT-2026-0007` | Felipe Gomes Silva |
| `MAT-2026-0008` | Pedro Teste |

Todos os oito estudantes possuem agora um usuário `STUDENT`, com `student.user_id` e `user.studentId` preenchidos de forma correspondente.

## 5. Contas de demonstração

Foram validados via `POST /api/auth/login` **26 logins**, todos com resposta HTTP 200: 18 contas de professor e 8 contas de aluno. Os nomes de usuário são os e-mails cadastrados em `users`.

Os professores estão organizados por disciplina, incluindo Matemática, Língua Portuguesa, Língua Inglesa, Ciências, História, Geografia, Arte, Educação Física, Física, Química, Biologia, Filosofia, Sociologia, Álgebra e Geometria. A conta principal `professor@pluseduc.com` também foi habilitada para a demonstração local.

A senha comum das contas de demonstração foi definida apenas no MongoDB local. Ela não está registrada neste arquivo, não foi incluída no commit e deve ser consultada na lista privada de acessos preparada para a apresentação.

## 6. Roteiro recomendado de demonstração

### 6.1 Professor

Inicie pelo login de um professor de demonstração. Mostre o dashboard, a listagem de turmas e o detalhe de uma turma. No detalhe, evidencie que as matérias são determinadas pelo currículo da série e que cada matéria possui no máximo um professor atribuído.

Em seguida, abra **Minhas matérias**, selecione uma disciplina e navegue até a turma correspondente. Mostre o desempenho dos alunos, a ordenação por nome ou nota e o fluxo de alunos sem turma. Depois, abra **Atividades** para demonstrar a criação, edição, exclusão, visualização e acompanhamento de respostas.

Finalize o fluxo do professor criando uma atividade manual ou gerada pela IA. Caso o Gemini não esteja disponível, explique que o fallback determinístico mantém a aplicação demonstrável sem mascarar a indisponibilidade do provedor externo. Mostre também a recomendação pedagógica baseada em lacunas de aprendizagem e notas reais.

### 6.2 Aluno

Faça logout e entre com uma conta de aluno. Mostre o perfil, a turma, os colegas, os professores, as atividades disponíveis e as notas. Abra uma atividade, responda uma questão objetiva e uma discursiva e mostre o resultado de acerto ou erro sem finalizar o fluxo administrativo do professor.

Depois, acesse a tela de desempenho do aluno para demonstrar a leitura pedagógica dos dados. A tela foi pensada para ser utilizada pelo aluno ou compartilhada com os responsáveis, destacando pontos fortes e aspectos que precisam de melhoria.

### 6.3 Currículo e integridade

Para apresentar a regra curricular, compare uma turma do Ensino Fundamental com uma turma do Ensino Médio. Explique que o catálogo oferece matérias diferentes por etapa e que as matérias já ocupadas deixam de aparecer como disponíveis para nova atribuição na mesma turma.

## 7. Comandos para executar localmente

Backend:

```powershell
Set-Location D:\PlusEducPython\PlusEduc\PlusEduc-BE-Python
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Frontend:

```powershell
Set-Location D:\PlusEducPython\PlusEduc\PlusEduc-UI
npm run dev
```

Validação automatizada do backend:

```powershell
Set-Location D:\PlusEducPython\PlusEduc\PlusEduc-BE-Python
.\.venv\Scripts\python.exe -m pytest -q
```

Validação do frontend:

```powershell
Set-Location D:\PlusEducPython\PlusEduc\PlusEduc-UI
npm run type-check
npm run build
```

## 8. Limitações conhecidas

A collection `classrooms` contém duas turmas temporárias criadas durante os testes reais de atribuição curricular. Elas não quebram os vínculos nem os logins, mas podem ser removidas antes da apresentação caso seja desejado um banco visualmente mais limpo.

A collection `subjects` contém as matérias curriculares oficiais ativas e uma matéria livre de teste chamada `Exemplo`, que não faz parte do catálogo por série. O comportamento esperado da aplicação é considerar somente matérias ativas e compatíveis com a série para novos cadastros e seleções. A regra de paralelismo CUDA/OpenCL permanece fora do escopo até a definição do professor responsável pela disciplina.

## 9. Checklist final

- [x] MongoDB local conectado ao banco `escola_db`.
- [x] Oito estudantes ativos com matrículas sequenciais.
- [x] Oito usuários de aluno vinculados bidirecionalmente.
- [x] Dezoito professores com perfis e contas autenticáveis.
- [x] Quinze turmas persistidas, incluindo o currículo por série.
- [x] Dezesseis matérias cadastradas.
- [x] Zero referências inválidas entre estudantes, professores e turmas.
- [x] Vinte e seis logins validados via HTTP com sucesso.
- [x] Senhas e tokens não incluídos no repositório.
- [x] Testes automatizados e build do frontend aprovados na validação anterior.
