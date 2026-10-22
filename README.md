# PlusEduc MonoRepo

Monorepo da plataforma educacional PlusEduc, reunindo o frontend React e o backend FastAPI.

## Versões deste repositório
- **`main`**: versão **web**. Backend e frontend rodam separados e são acessados pelo navegador.
- **`feat/desktop-installer`** (esta branch): versão **desktop**. O PlusEduc vira um aplicativo instalável do Windows,
  com janela própria (sem navegador) e instalador `PlusEduc-Setup`.

## Estrutura
- `PlusEduc-UI/`: aplicação web React, TypeScript, Vite e TailwindCSS.
- `PlusEduc-BE-Python/`: API FastAPI com MongoDB local, estatísticas de notas em OpenCL, e o empacotamento do aplicativo
  de desktop (`run_server.py`, `installer/`, `scripts/build_exe.py`).

## Aplicativo de desktop (Windows)

**Instalar:** execute `PlusEduc-Setup-<versão>.exe` (não pede administrador) e abra o PlusEduc pelo Menu Iniciar ou pelo
atalho da Área de Trabalho. Requer o MongoDB em execução na máquina. A configuração fica em `%APPDATA%\PlusEduc\.env`,
criada na primeira execução.

**Gerar o instalador:** dê dois cliques em `PlusEduc-BE-Python\Compilar_PlusEduc.bat`. Pré-requisitos: Python 3.11+,
Node.js e o Inno Setup 6 (`winget install JRSoftware.InnoSetup`). O instalador sai em `PlusEduc-BE-Python\dist\installer`.

**Backend compilado (opcional):** `PlusEduc-BE-Python\Compilar_PlusEduc.bat nuitka` compila o backend para código nativo com o
Nuitka (demora ~30 min na primeira vez e baixa um compilador C; instalador de 42 MB contra 37 MB). O ganho de desempenho medido é
modesto e inconsistente, então o padrão continua sendo o PyInstaller. Detalhes e medições no README do backend.

**Atualização automática:** o aplicativo avisa quando existe uma versão mais nova no GitHub (releases do repositório) e o botão
**Atualizar** baixa e executa o instalador. Configurável por `UPDATE_CHECK_ENABLED` e `UPDATE_REPO` (ver `.env.example`).
Para publicar uma versão: altere `PlusEduc-BE-Python/app/version.py`, gere o instalador e anexe-o à release `v<versão>` com o nome
`PlusEduc-Setup.exe`.

Detalhes, opções e solução de problemas: [PlusEduc-BE-Python/README.md](PlusEduc-BE-Python/README.md).

## Execução local (desenvolvimento)
Backend: `PlusEduc-BE-Python/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload`
Frontend: `PlusEduc-UI/npm run dev -- --host 0.0.0.0 --port 5173`

## Testes
Backend: `PlusEduc-BE-Python/.venv/Scripts/python.exe -m pytest --tb=no -q`
Frontend: `npm run type-check` e `npm run build`

Arquivos `.env`, ambientes virtuais, dependências, builds, logs e caches locais não são versionados.
