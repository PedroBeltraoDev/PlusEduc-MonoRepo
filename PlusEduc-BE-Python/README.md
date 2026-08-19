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
