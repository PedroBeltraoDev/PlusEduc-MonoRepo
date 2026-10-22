# PlusEduc Backend — FastAPI

Backend Python/FastAPI do PlusEduc. A aplicação substitui incrementalmente o backend Java/Spring Boot, mantendo compatibilidade com o frontend React e utilizando MongoDB como persistência principal.

## Pré-requisitos

O ambiente local requer **Python 3.11 ou superior**, **MongoDB em execução** e PowerShell no Windows. O banco utilizado pelo projeto é `escola_db`, conectado por padrão em `mongodb://localhost:27017`.

O frontend React está no diretório irmão `PlusEduc-UI`. Este README documenta somente o backend localizado em `PlusEduc-BE-Python`.

> **Branch `feat/desktop-installer`:** além da API, esta branch empacota o PlusEduc como **aplicativo instalável do Windows**
> (janela própria, sem navegador), descrito em [Aplicativo de desktop e instalador](#aplicativo-de-desktop-e-instalador-pluseduc-setup).
> A versão que roda no navegador (API + frontend separados) fica na `main`.

## Estrutura principal

| Diretório/arquivo | Finalidade |
|---|---|
| `app/main.py` | Criação da aplicação FastAPI, lifespan, CORS, tratamento de exceções e registro das rotas. |
| `app/api/` | Routers HTTP separados por domínio. |
| `app/services/` | Regras de negócio e orquestração dos casos de uso. |
| `app/repositories/` | Acesso às collections do MongoDB. |
| `app/schemas/` | Schemas Pydantic de entrada e saída. |
| `app/compute/` | Estatísticas de notas com kernel OpenCL (`grade_stats.cl`) e caminho de reserva em Python. |
| `app/core/parallel.py` | `run_parallel`: consultas independentes ao MongoDB executadas ao mesmo tempo. |
| `app/version.py` | Versão do aplicativo (fonte única, lida pelo build do instalador e pela verificação de atualização). |
| `app/services/update_service.py` | Verificação de nova versão no GitHub, download validado do instalador e disparo da atualização (`/api/app/*`). |
| `app/core/spa.py` | Serve a interface compilada (React) na mesma porta da API quando `FRONTEND_DIST` está definido. |
| `run_server.py` | Ponto de entrada do aplicativo de desktop: sobe a API e abre a janela própria. |
| `installer/PlusEduc.iss` | Script do instalador (Inno Setup 6). |
| `assets/pluseduc.ico` | Ícone do aplicativo e do instalador. |
| `scripts/` | `build_exe.py` (aplicativo e instalador), `build_backend.py` (bytecode), `serve.py` (vários processos), `benchmark_*.py`, `make_icon.py`, `seed_demo_population.py`. |
| `Compilar_PlusEduc.bat` | Clique para gerar o instalador. |
| `tests/` | Testes automatizados da API e dos serviços. |
| `.env` | Configuração local; não deve ser versionado nem publicado. |
| `requirements.txt` | Dependências Python do backend (inclui `numpy` e `pyopencl`). |
| `requirements-build.txt` | Dependências só para empacotar: `pyinstaller` e `pywebview`. |

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

# Sobe o build compilado com vários processos (padrão: um por núcleo, no máximo 4; ou WEB_CONCURRENCY)
Set-Location build
..\.venv\Scripts\python.exe scripts\serve.py --port 8080 --workers 4

# Frontend: gera PlusEduc-UI\dist (bundle de produção com code splitting por rota)
Set-Location ..\..\PlusEduc-UI
npm ci
npm run build
```

Ao conectar, a API cria índices simples nas coleções **já existentes** (`users.email`, `grades.studentId`, `activities.classroom_id` etc.; lista em `PERFORMANCE_INDEXES` de `app/core/database.py`). Índices equivalentes que você já tenha são respeitados.

Para medir consultas e tempo dos serviços mais pesados num banco temporário (criado e apagado pelo script):

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_services.py --latency-ms 20
```

## Aplicativo de desktop e instalador (PlusEduc-Setup)

O PlusEduc também roda como **aplicativo instalado no Windows**, com janela própria (sem navegador e sem console).
O pacote inclui Python, dependências, o kernel OpenCL e a interface; a única dependência externa é o MongoDB.

**Para quem usa:** baixe `PlusEduc-Setup-<versão>.exe`, execute (não pede administrador), conclua o assistente e abra o
PlusEduc pelo Menu Iniciar ou pelo atalho da Área de Trabalho. Na primeira execução ele cria
`%APPDATA%\PlusEduc\.env` (MongoDB local, banco `escola_db`, `JWT_SECRET` gerado) e o log `PlusEduc.log` na mesma pasta;
edite o `.env` para trocar o banco ou informar a chave do Gemini. A desinstalação (Configurações > Aplicativos) mantém
essa pasta. Requer o Microsoft Edge WebView2 (já vem no Windows 10/11 atualizados).

**Para gerar o instalador:** dê dois cliques em `Compilar_PlusEduc.bat` (instala dependências, compila a interface, empacota
com o PyInstaller e monta o instalador com o Inno Setup; leva alguns minutos). O resultado fica em `dist\installer`.

```powershell
winget install JRSoftware.InnoSetup                          # uma vez
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts\build_exe.py --installer  # dist\installer\PlusEduc-Setup-<versão>.exe
.\.venv\Scripts\python.exe scripts\build_exe.py              # só a pasta dist\PlusEduc\ (sem instalador)
```

**Como funciona.** O `PlusEduc.exe` sobe o servidor FastAPI numa thread, em `127.0.0.1` (só esta máquina) na porta 8080 ou na
próxima livre, espera ele ficar pronto e abre a janela (pywebview, que usa o Edge WebView2 do sistema) apontando para essa
porta. A interface React compilada vai embutida no pacote e é servida pela própria API, então não há CORS nem proxy. Ao fechar
a janela o servidor é encerrado. O login fica salvo em `%APPDATA%\PlusEduc\webview`. O executável é gerado sem console: tudo
o que seria impresso vai para `%APPDATA%\PlusEduc\PlusEduc.log`.

**Atualizar (automático).** Ao abrir, o aplicativo consulta em segundo plano a última release do GitHub
(`https://api.github.com/repos/<UPDATE_REPO>/releases/latest`). Se a versão publicada for maior que a instalada, aparece no
canto da tela o aviso **"Nova versão X disponível"** com **Atualizar** e **Lembrar depois** (adia por 4 horas). **Atualizar**
baixa o `PlusEduc-Setup.exe` da release para uma pasta temporária, confere tamanho e SHA-256 (informados pelo GitHub) e o
executa com `/SILENT`; o aplicativo fecha, o instalador (mesmo `AppId`) substitui os arquivos preservando
`%APPDATA%\PlusEduc` e o PlusEduc abre de novo na versão nova. A verificação nunca atrasa nem impede a abertura: sem internet,
sem nenhuma release publicada (404), com o limite de consultas do GitHub ou com qualquer erro, o aviso simplesmente não aparece
(o motivo fica no log). Repete a cada 6 horas.

| Variável (`%APPDATA%\PlusEduc\.env`) | Padrão | Efeito |
|---|---|---|
| `UPDATE_CHECK_ENABLED` | `true` | `false` desliga a verificação (nenhuma conexão ao GitHub). |
| `UPDATE_REPO` | `PedroBeltraoDev/PlusEduc-MonoRepo` | `dono/repositório` público onde ficam as releases. O instalador só é baixado de `https://github.com/<UPDATE_REPO>/releases/download/...`. |
| `UPDATE_CHECK_INTERVAL_HOURS` | `6` | Intervalo entre verificações. |
| `UPDATE_REQUEST_TIMEOUT_SECONDS` | `5` | Tempo máximo de cada consulta ao GitHub. |

*Publicar uma versão (para quem mantém o projeto):* altere `__version__` em `app/version.py` (fonte única da versão: o
instalador, o `/health` e a verificação a leem de lá), gere o instalador (`scriptsuild_exe.py --installer`) e crie no GitHub
uma release com a tag `v<versão>` anexando o instalador **com o nome fixo `PlusEduc-Setup.exe`** (o mesmo nome que o site de
download usa em `releases/latest/download/`). Rascunhos e pré-lançamentos são ignorados. Estado e ações:
`GET /api/app/version`, `GET /api/app/update`, `POST /api/app/update/check` e `POST /api/app/update/install` (exige o cabeçalho
`X-PlusEduc-Update: 1`, para que outro site aberto no computador não consiga acioná-lo).

Limites: a instalação automática só funciona no aplicativo instalado (`PlusEduc.exe`, Windows) e com janela; em `--headless`,
rodando pelo código-fonte ou em outro sistema o aviso aparece com um link para a página da versão. Com `--browser` a
atualização funciona, mas o aplicativo reabre na janela própria. Atualização manual continua valendo: execute o novo
`PlusEduc-Setup.exe` por cima. **Testar sem instalar:** rode `scriptsuild_exe.py` e abra `dist\PlusEduc\PlusEduc.exe`.

Opções do executável: `--port` (se estiver em uso, usa a próxima livre), `--browser` (abre no navegador em vez da janela),
`--headless` (só o servidor; com `--host 0.0.0.0` outras máquinas acessam). Um `.env` ao lado do `.exe` tem prioridade
(uso portátil). O pacote vale para o Windows e o Python em que foi gerado. Em desenvolvimento a interface continua no Vite;
o backend só a serve quando `FRONTEND_DIST` aponta para `PlusEduc-UI\dist`. O ícone vem de `assets\pluseduc.ico`
(`scripts\make_icon.py` o regenera).

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

### Aplicativo de desktop: a janela não abre ou fecha sozinha

Abra `%APPDATA%\PlusEduc\PlusEduc.log` (o aplicativo não tem console). Causas comuns: o **MongoDB está parado** (a janela mostra a tela de login, mas o login falha; inicie o serviço `MongoDB`), o **Microsoft Edge WebView2** não está instalado (a janela não abre e o motivo fica no log; instale o "WebView2 Runtime" da Microsoft ou use `PlusEduc.exe --browser`) ou o `.env` em `%APPDATA%\PlusEduc` tem um valor inválido. Para ver as mensagens ao vivo, gere com `python scripts\build_exe.py --console`.

### Aplicativo de desktop: não vejo meus dados

O `.env` criado na primeira execução usa o banco `escola_db`. Se os seus dados estão em outro banco ou outro servidor, edite `MONGODB_DATABASE` e `MONGODB_URI` em `%APPDATA%\PlusEduc\.env` e reabra o aplicativo.

### Compilar_PlusEduc.bat falha

Confirme se o Inno Setup está instalado (`winget install JRSoftware.InnoSetup`) e se o Node.js está no `PATH` (a interface é compilada com `npm`). Em pasta recém-clonada o `.bat` cria o `.venv` e instala as dependências sozinho; a primeira execução baixa pacotes e demora mais.

## Segurança e Git

O `.env`, ambientes virtuais, dependências instaladas, builds, logs e caches são arquivos locais e não devem ser publicados. Antes de executar `git add`, confira sempre:

```powershell
git status --short
git diff --cached --name-only
```

Não coloque chaves Gemini, segredos JWT, credenciais MongoDB ou senhas em commits, issues, screenshots ou documentação pública.
