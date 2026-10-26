# PlusEduc Backend — FastAPI

Backend Python/FastAPI do PlusEduc. A aplicação substitui incrementalmente o backend Java/Spring Boot, mantendo compatibilidade com o frontend React e utilizando MongoDB como persistência principal.

## Pré-requisitos

O ambiente local requer **Python 3.11 ou superior**, **MongoDB em execução** e PowerShell no Windows. O banco utilizado pelo projeto é `escola_db`, conectado por padrão em `mongodb://localhost:27017`.

O frontend React está no diretório irmão `PlusEduc-UI`. Este README documenta somente o backend localizado em `PlusEduc-BE-Python`.

## Estrutura principal

| Diretório/arquivo | Finalidade |
|---|---|
| `app/main.py` | Criação da aplicação FastAPI, lifespan, CORS, tratamento de exceções e registro das rotas. |
| `app/api/` | Routers HTTP separados por domínio. |
| `app/services/` | Regras de negócio e orquestração dos casos de uso. |
| `app/repositories/` | Acesso às collections do MongoDB. |
| `app/schemas/` | Schemas Pydantic de entrada e saída. |
| `tests/` | Testes automatizados da API e dos serviços. |
| `.env` | Configuração local; não deve ser versionado nem publicado. |
| `requirements.txt` | Dependências Python do backend. |

## Configuração do ambiente

Entre no diretório do backend:

```powershell
Set-Location 'D:\PlusEducPython\PlusEduc\PlusEduc-BE-Python'
```

Se o ambiente virtual ainda não existir, crie-o com Python 3.11 ou superior:

```powershell
py -3.11 -m venv .venv
```

Instale as dependências usando o Python do ambiente virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O arquivo `.env` local deve conter as configurações do ambiente. Para começar usando o modelo seguro, execute:

```powershell
Copy-Item .env.example .env
```

Depois, edite somente o `.env` local e preencha os segredos necessários. Nunca copie valores reais de chaves para este README, para o frontend ou para o GitHub.

| Variável | Valor esperado neste projeto |
|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017` |
| `MONGODB_DATABASE` | `escola_db` |
| `MONGODB_REQUIRED` | `false` ou `true`, conforme a política do ambiente |
| `JWT_SECRET` | Segredo forte definido somente no `.env` local |
| `JWT_EXPIRATION_MS` | `28800000`, equivalente a 8 horas |
| `JWT_REFRESH_EXPIRATION_MS` | `604800000`, equivalente a 7 dias |
| `CORS_ALLOWED_ORIGINS` | Origens do frontend, por exemplo `http://localhost:5173` |
| `GEMINI_API_KEY` | Chave local do Gemini; quando vazia, a aplicação usa o fallback educacional |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |
| `GEMINI_API_VERSION` | `v1` |

## Executando o backend

Use o comando abaixo para iniciar o servidor na porta utilizada pelo frontend:

```powershell
Set-Location 'D:\PlusEducPython\PlusEduc\PlusEduc-BE-Python'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

O backend ficará disponível nos seguintes endereços:

| Recurso | URL |
|---|---|
| API local | `http://127.0.0.1:8080` |
| Swagger UI | `http://127.0.0.1:8080/docs` |
| ReDoc | `http://127.0.0.1:8080/redoc` |
| OpenAPI JSON | `http://127.0.0.1:8080/openapi.json` |
| Health check | `http://127.0.0.1:8080/health` |

Para validar rapidamente a aplicação em outro terminal:

```powershell
Invoke-WebRequest 'http://127.0.0.1:8080/health'
```

Uma resposta saudável deve indicar que a aplicação está ativa e que a conexão com o MongoDB foi inicializada conforme a configuração do ambiente.

Para interromper o servidor, pressione `Ctrl + C` no terminal em que o Uvicorn está sendo executado.

## Domínios e endpoints principais

A API está organizada pelos seguintes domínios:

| Domínio | Rotas principais |
|---|---|
| Health | `GET /health` |
| Autenticação e perfil | `POST /api/auth/login`, `PUT /api/auth/profile` |
| Students | `/api/students` e endpoints analíticos de performance e frequência |
| Teachers | `/api/teachers` |
| Classrooms | `/api/classrooms`, matrícula, consultas e `GET /api/classrooms/{id}/performance` |
| Grades | `/api/grades`, consultas por aluno/turma e média do aluno |
| Activities | `/api/activities`, geração por IA e exportação PDF |
| Submissões | `/api/activity-submissions` e submissões no portal do aluno |
| Student Portal | `/api/student-portal` |

Os endpoints protegidos exigem `Authorization: Bearer <accessToken>`. O login usa o e-mail como subject do JWT e retorna os campos previstos pelo frontend, incluindo `accessToken`, `refreshToken`, `expiresIn`, `userId`, `userEmail`, `role`, `studentId` quando aplicável e `name` quando disponível.

## Build e execução em produção

```powershell
# Backend: gera build\app apenas com bytecode (.pyc), usando o mesmo Python que vai rodar o servidor
.\.venv\Scripts\python.exe scripts\build_backend.py

# Alternativa: o pacote app traduzido para C e compilado em código nativo (build\app.<tag>.pyd), com o Nuitka
.\.venv\Scripts\python.exe -m pip install -r requirements-compile.txt
.\.venv\Scripts\python.exe scripts\build_backend.py --nuitka

# Sobe o build compilado com vários processos (padrão: um por núcleo, no máximo 4; ou WEB_CONCURRENCY)
Set-Location build
..\.venv\Scripts\python.exe scripts\serve.py --port 8080 --workers 4

# Frontend: gera PlusEduc-UI\dist (bundle de produção com code splitting por rota)
Set-Location ..\..\PlusEduc-UI
npm ci
npm run build
```

**Compilação nativa (opcional).** Como as `.class` do Java, o resultado dos dois modos não é um executável: é o backend
sem os fontes `.py`, que continua rodando no interpretador Python (`serve.py` ou `uvicorn app.main:app`, com a API e as
rotas iguais). `--nuitka` gera uma única extensão nativa `build\app.cp312-win_amd64.pyd` com todo o pacote `app/`
(só o código do projeto é compilado; as bibliotecas continuam as instaladas no ambiente) e copia ao lado dela o kernel
OpenCL `grade_stats.cl`, que o driver compila ao executar. Requer o mesmo Python (3.12 foi o validado) no build e na
execução, `requirements-compile.txt` e um compilador C: sem MSVC, o Nuitka baixa um MinGW64 (~250 MB) na primeira vez.
O build leva cerca de 2 minutos (80 arquivos C; menos com o cache do compilador aquecido). O ganho de desempenho é
modesto porque o tempo da API é dominado por E/S do MongoDB; o bytecode (padrão) é o caminho mais simples e o fallback.
Com o Python da Microsoft Store o script usa o cache `C:\nuitka-cache` (o padrão tem caminho longo demais para extrair o
MinGW); defina `NUITKA_CACHE_DIR` para usar outra pasta.

**Servidor inteiro compilado (`--standalone`, opcional).** Compila também as bibliotecas Python (FastAPI, Starlette,
Uvicorn, Pydantic, PyMongo, ReportLab...) e embute o runtime do Python numa pasta que não precisa do interpretador
instalado nem de nenhum `.py`:

```powershell
.\.venv\Scripts\python.exe scripts\build_backend.py --standalone     # build\PlusEduc-API\PlusEduc-API.exe
Copy-Item .env.example build\PlusEduc-API\.env                        # edite: JWT_SECRET, MongoDB...
build\PlusEduc-API\PlusEduc-API.exe --host 0.0.0.0 --port 8080 --workers 4
```

O ponto de entrada é `run_api.py` (`--host`, `--port`, `--workers`, como `serve.py`; `--check` só importa a aplicação).
O `.env` é lido da pasta do executável, o kernel OpenCL `app/compute/grade_stats.cl` vai ao lado (sem GPU a API usa o
caminho em Python) e cada worker é um processo próprio. É só a API: o frontend continua separado (`PlusEduc-UI`).

Medido nesta máquina (Windows 11, Python 3.12, Nuitka 4.3, MinGW gcc 15.2, Radeon RX 580, MongoDB local, 2 workers):

| | `serve.py` (interpretado) | `PlusEduc-API.exe` |
|---|---|---|
| Build | segundos (bytecode) | 28 min (primeira compilação das bibliotecas) |
| Tamanho | só os fontes/bytecode (usa o Python e os pacotes do venv) | 165 MB, 113 arquivos |
| Subida até `/health` (mediana de 3) | 2,55 s | 1,77 s |
| `GET /api/classrooms/{id}/performance` (mediana) | 5,1 ms | 6,0 ms |
| `GET /api/students/paginated` (mediana) | 2,8 ms | 3,6 ms |
| PDF de 10 questões (mediana) | 29–31 ms | 32 ms |

A subida é mais rápida, mas **as rotas não ficaram mais rápidas** (nas duas ordens de medição o executável saiu ~15–30%
mais lento nas rotas curtas): o tempo da API é dominado por E/S do MongoDB, validação e serialização, e o código das
bibliotecas compilado não compensa. Por isso o bytecode segue o padrão; `--standalone` vale para distribuir o servidor sem
exigir Python instalado nem expor os fontes. Verificado: executável iniciado com `PATH` sem Python, `/health` com banco e
OpenCL ativos, registro, login, aluno, turma, notas (kernel OpenCL executado), atividade e PDF, com 2 workers.

**O que ainda não é compilado por nós** (vai para a pasta como está): o runtime e as DLLs do Python (`python312.dll`,
`vcruntime`, OpenSSL, SQLite) e os módulos nativos que o pip já entrega prontos, como `numpy`, `pydantic-core` (Rust),
`bcrypt`, `pymongo._cmessage`/`bson._cbson`, `pyopencl` e a DLL `OpenCL.dll`, `httptools`, `websockets`, `watchfiles`,
`Pillow`, `yaml` e `zstandard`. O kernel OpenCL (`grade_stats.cl`) é compilado pelo driver da GPU ao executar. Só o código
Python (nosso e das bibliotecas) vira C; o resultado depende do Windows e do Python em que foi gerado.

Ao conectar, a API cria índices simples nas coleções **já existentes** (`users.email`, `grades.studentId`, `activities.classroom_id` etc.; lista em `PERFORMANCE_INDEXES` de `app/core/database.py`). Índices equivalentes que você já tenha são respeitados.

Para medir consultas e tempo dos serviços mais pesados num banco temporário (criado e apagado pelo script):

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_services.py --latency-ms 20
```

## Paralelismo com OpenCL

As estatísticas de notas (média por disciplina e por aluno, frequência, última data) são calculadas por um
kernel OpenCL (`app/compute/grade_stats.cl`): redução segmentada com um work-group por grupo, árvore em memória local
e `barrier`, sem operações atômicas. É usado em `/api/students/{id}/performance`, `/attendance`, no desempenho da turma
(`/api/classrooms/{id}/performance`), no resumo de notas da turma e no portal do aluno.

Requer `pyopencl` e `numpy` (já em `requirements.txt`) e um dispositivo OpenCL com fp64 (GPU de preferência). Sem eles a API
continua funcionando pelo caminho em Python, que é também o oracle dos testes.

| Variável | Padrão | Efeito |
|---|---|---|
| `OPENCL_ENABLED` | `true` | Liga/desliga o OpenCL. |
| `OPENCL_MIN_RECORDS` | `0` | Abaixo desse número de lançamentos usa Python. O ponto de equilíbrio medido fica perto de 100 mil registros; em produção use algo como `50000`. |
| `OPENCL_DEVICE` | vazio | Trecho do nome do dispositivo (ex.: `Radeon`); vazio escolhe a primeira GPU. |

`GET /health` mostra o estado em `opencl` (dispositivo, se está ativo e quantas execuções do kernel já ocorreram). Para comparar Python x GPU:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_opencl.py
```

## Testes

Execute a suíte completa com o ambiente virtual do projeto:

```powershell
Set-Location 'D:\PlusEducPython\PlusEduc\PlusEduc-BE-Python'
.\.venv\Scripts\python.exe -m pytest --tb=no -q
```

Para executar apenas os testes de autenticação:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_auth.py -q
```

Para executar os testes de turmas, incluindo performance agregada:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_classrooms.py -q
```

Os testes utilizam fixtures controladas para validar contratos e regras, enquanto a execução normal da aplicação utiliza os repositórios conectados ao MongoDB local. Não crie usuários ou notas de teste diretamente no banco de homologação sem necessidade.

## Integração com o frontend

O frontend deve ser executado em outro terminal:

```powershell
Set-Location 'D:\PlusEducPython\PlusEduc\PlusEduc-UI'
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

O proxy do Vite encaminha as chamadas `/api` para `http://127.0.0.1:8080`. Se o navegador estiver sendo acessado por outro dispositivo da rede, mantenha o Vite exposto na interface de rede e inclua a origem correspondente em `CORS_ALLOWED_ORIGINS`.

## Solução de problemas

### Erro `ERR_CONNECTION_REFUSED`

Verifique se o Uvicorn está em execução na porta `8080`, se o Vite está em execução na porta `5173` e se o MongoDB está ativo. Teste primeiro `http://127.0.0.1:8080/health`.

### Erro `401 Unauthorized`

Faça logout e login novamente para obter um token atualizado. O frontend armazena o token e o prazo retornado em `expiresIn`; tokens antigos não são renovados automaticamente por este projeto.

### Geração por IA retorna modo de demonstração

Confirme se `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.5-flash-lite` e `GEMINI_API_VERSION=v1` estão configurados no `.env`. Quando a API do Gemini estiver indisponível ou sem cota, o fallback determinístico é utilizado e o frontend exibe um aviso.

### MongoDB não conecta

Confirme se o serviço local está ativo e se `MONGODB_URI` e `MONGODB_DATABASE` correspondem ao ambiente esperado. O backend não deve criar collections novas como parte do funcionamento normal.

## Segurança e Git

O `.env`, ambientes virtuais, dependências instaladas, builds, logs e caches são arquivos locais e não devem ser publicados. Antes de executar `git add`, confira sempre:

```powershell
git status --short
git diff --cached --name-only
```

Não coloque chaves Gemini, segredos JWT, credenciais MongoDB ou senhas em commits, issues, screenshots ou documentação pública.
