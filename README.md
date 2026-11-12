# PlusEduc — Plataforma de Gestão Pedagógica com Análise de Aprendizagem

**Versão:** 1.0.0-rc.1 (release candidate, Sprint 10) · **Grupo 08** · Fábrica de Software + Tópicos Avançados · Ciência da Computação, UNINASSAU · 2026.2

O PlusEduc é um sistema web para escolas de educação básica (Ensino Fundamental e Médio, currículo alinhado à BNCC).
Professores e administradores gerenciam turmas, alunos, atividades, notas e frequência e acompanham indicadores e
relatórios; alunos respondem atividades e consultam notas e desempenho em um portal próprio.

## Objetivo da solução

O acompanhamento pedagógico costuma ser manual e reativo: notas e faltas ficam em planilhas que só registram dados, e
as dificuldades de cada aluno aparecem tarde. O PlusEduc centraliza a gestão pedagógica da turma e transforma os
registros em informação de ação:

- **gestão unificada** de alunos, professores, turmas, matérias por série, atividades, notas e frequência, com acesso por perfil;
- **atividades de ponta a ponta**: criação manual ou assistida por IA, resposta do aluno no portal, correção automática das questões objetivas, correção manual das discursivas e lançamento no boletim;
- **diagnóstico**: desempenho por turma, por matéria e por aluno, lacunas de aprendizagem, dashboard com filtros e relatórios exportáveis (CSV, Excel e PDF);
- **rastreabilidade**: histórico de toda operação que altera dados (quem, quando, o quê, antes e depois);
- **desempenho**: estatísticas de notas calculadas em lote com OpenCL (GPU/CPU), com alternativa em Python.

## Equipe

| Integrante | Matrícula | Papel |
|---|---|---|
| Pedro Antônio Silva Pedroso Beltrão | 01605602 | Scrum Master; desenvolvimento (backend e frontend) |
| André Marcílio da Silva Ferreira | 01616701 | UI/UX, testes e documentação |
| Evandro Albuquerque do Rêgo Lima | 01607434 | UI/UX, testes e documentação |

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Frontend (`PlusEduc-UI`) | React 18, TypeScript, Vite 6, Tailwind CSS 4, Radix UI, React Router 7, Recharts |
| Backend (`PlusEduc-BE-Python`) | Python 3.12, FastAPI, Pydantic 2, PyMongo, PyJWT, bcrypt, ReportLab e openpyxl (exportações), PyOpenCL e NumPy (estatísticas) |
| Banco de dados | MongoDB (local), banco `escola_db` |
| Integrações opcionais | Google Gemini (geração de atividades, com alternativa determinística) e SMTP (código de recuperação de senha) |
| Qualidade | pytest (171 testes), verificação de tipos e build do frontend e Selenium (regressão de navegação) |

## Requisitos para execução

- **Python 3.11 ou superior** (validado com 3.12)
- **Node.js 18 ou superior** (validado com 22) e npm
- **MongoDB 6 ou superior** em execução em `localhost:27017`
- Windows 10/11 com PowerShell (os comandos abaixo); em Linux/macOS, troque `.venv\Scripts\python.exe` por `.venv/bin/python`
- Opcionais: driver OpenCL (sem ele o cálculo usa Python), chave do Gemini, conta SMTP

## Instalação e configuração

```powershell
git clone https://github.com/PedroBeltraoDev/PlusEduc-MonoRepo.git
cd PlusEduc-MonoRepo
```

### 1. Backend

```powershell
cd PlusEduc-BE-Python
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite o `.env` (ele nunca é versionado). O mínimo é definir **`JWT_SECRET`** com um texto longo e aleatório:

| Variável | Para que serve | Padrão |
|---|---|---|
| `JWT_SECRET` | assinatura dos tokens (obrigatória) | — |
| `MONGODB_URI`, `MONGODB_DATABASE` | conexão e nome do banco | `mongodb://localhost:27017`, `escola_db` |
| `CORS_ALLOWED_ORIGINS` | origens do frontend | `http://localhost:5173` |
| `TEACHER_REGISTRATION_REQUIRES_APPROVAL` | cadastro público de professor fica pendente até um ADMIN aprovar | `true` |
| `PASSWORD_RESET_DEMO_MODE` | mostra o código de recuperação na tela, sem e-mail (só em máquina local) | `false` |
| `GEMINI_API_KEY`, `SMTP_*` | integrações opcionais | vazio |

### 2. Frontend

```powershell
cd ..\PlusEduc-UI
npm install
```

Não é preciso configurar nada: em desenvolvimento o Vite encaminha `/api` para `http://localhost:8080`
(para outro destino, defina `VITE_DEV_PROXY_TARGET`).

## Banco de dados

1. **Suba o MongoDB** local (serviço do Windows `MongoDB` ou `mongod --dbpath <pasta>`). Não é preciso criar o banco,
   as coleções nem os índices: a API cria os índices ao iniciar e as coleções no primeiro uso.
2. **Crie o administrador** (ele aprova os cadastros de professor e vê o histórico de todos):

   ```powershell
   cd PlusEduc-BE-Python
   .\.venv\Scripts\python.exe scripts\create_admin.py --email admin@escola.local --name "Coordenação"
   ```

   A senha é pedida no terminal (ou lida de `PLUSEDUC_ADMIN_PASSWORD`).
3. **Dados de demonstração (opcional):** turmas, alunos, professores, atividades e notas fictícios.

   ```powershell
   $env:PLUS_EDUC_DEMO_PASSWORD = "<senha das contas de demonstração>"
   .\.venv\Scripts\python.exe scripts\seed_demo_population.py
   ```

   Detalhes em [`docs/DEMO_DATA_POPULATION.md`](docs/DEMO_DATA_POPULATION.md).
4. **Verifique a consistência** quando quiser (somente leitura; 22 verificações de referências, duplicidades e índices):

   ```powershell
   .\.venv\Scripts\python.exe scripts\check_database.py
   ```

A estrutura final do banco (10 coleções, relações, chaves, índices e regras de integridade) está em
[`docs/MODELO_DE_DADOS.md`](docs/MODELO_DE_DADOS.md).

## Como executar

Em dois terminais:

```powershell
# terminal 1 — API em http://127.0.0.1:8080
cd PlusEduc-BE-Python
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

```powershell
# terminal 2 — interface em http://localhost:5173
cd PlusEduc-UI
npm run dev -- --host 0.0.0.0 --port 5173
```

Abra `http://localhost:5173`. Confira a API em `http://127.0.0.1:8080/health`.

| Perfil | Como obter acesso | O que vê |
|---|---|---|
| Administrador | `scripts/create_admin.py` | painel do educador, aprovação de professores, histórico de todos |
| Professor | "Cadastre-se como professor" na tela de login (aguarda aprovação do administrador) ou cadastro feito por um administrador | turmas, atividades, notas, relatórios, o próprio histórico |
| Aluno | "Cadastre-se como aluno" ou acesso liberado pelo professor na turma | portal do aluno |

### Testes

```powershell
# backend: 171 testes (use um banco descartável para não tocar nos dados de demonstração)
cd PlusEduc-BE-Python
$env:MONGODB_DATABASE = "pluseduc_teste"
.\.venv\Scripts\python.exe -m pytest -q

# frontend: tipos e build de produção
cd ..\PlusEduc-UI
npm run type-check
npm run build
```

A regressão
funcional contra o sistema em execução (104 casos de API, 91 de navegação e 15 de validação pela interface) está em
[`docs/sprint-10/`](docs/sprint-10/README.md).

## Documentação da API

| Onde | Conteúdo |
|---|---|
| [`docs/API.md`](docs/API.md) | referência das 99 rotas: autenticação, perfis, exemplos com `curl`, parâmetros, corpos e respostas |
| `http://127.0.0.1:8080/docs` | Swagger UI interativo (com o backend em execução) |
| `http://127.0.0.1:8080/redoc` | ReDoc |
| [`docs/api/openapi.json`](docs/api/openapi.json) | esquema OpenAPI 3.1 (importável no Postman ou Insomnia) |

`docs/API.md` e o `openapi.json` são gerados do código com `python scripts/export_api_docs.py`.

## Estrutura do projeto

```text
PlusEduc-MonoRepo/
├── PlusEduc-BE-Python/          API FastAPI
│   ├── app/
│   │   ├── api/                 routers por domínio (auth, students, classrooms, grades, activities, reports...)
│   │   ├── services/            regras de negócio e casos de uso
│   │   ├── repositories/        acesso às coleções do MongoDB
│   │   ├── schemas/             contratos de entrada e saída (Pydantic) e validações
│   │   ├── core/                configuração, JWT, senhas, conexão, erros, histórico de operações
│   │   └── compute/             estatísticas de notas em OpenCL
│   ├── scripts/                 create_admin, seed, check_database, export_api_docs, build e benchmarks
│   └── tests/                   suíte pytest
├── PlusEduc-UI/                 interface React
│   └── src/
│       ├── app/pages/           telas do professor/administrador e, em student/, do portal do aluno
│       ├── app/components/      layouts, menus e componentes de interface
│       ├── contexts/            sessão do usuário (AuthContext)
│       ├── services/            cliente HTTP e um serviço por domínio
│       └── types/, hooks/, utils/, styles/
└── docs/                        documentação do projeto e evidências de cada sprint
```

## Documentação do projeto

| Documento | Conteúdo |
|---|---|
| [`docs/PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md`](docs/PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md) | plano, requisitos, casos de uso, backlog e cronograma |
| [`docs/REQUISITOS_STATUS.md`](docs/REQUISITOS_STATUS.md) | situação real de cada requisito funcional e não funcional |
| [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) | camadas, segurança, frontend e build |
| [`docs/MODELO_DE_DADOS.md`](docs/MODELO_DE_DADOS.md) | estrutura final do banco |
| [`docs/API.md`](docs/API.md) | documentação da API |
| [`docs/DEMO_AND_PRESENTATION.md`](docs/DEMO_AND_PRESENTATION.md) | roteiro de demonstração |
| [`docs/sprint-08/`](docs/sprint-08/README.md), [`docs/sprint-09/`](docs/sprint-09/README.md), [`docs/sprint-10/`](docs/sprint-10/README.md) | permissões verificadas, testes completos e release candidate (resultados e capturas) |

## Pendências conhecidas

Registradas em [`docs/sprint-10/README.md`](docs/sprint-10/README.md): predição de risco, agrupamento por perfil e
otimização de grupos de reforço (RF19, RF21 e RF22), o escopo de dados por turma para cada professor e a
integração contínua (os testes ainda rodam manualmente).

Arquivos `.env`, ambientes virtuais, dependências, builds, logs e caches locais não são versionados.
