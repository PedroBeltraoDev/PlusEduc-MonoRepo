# PlusEduc — aplicativo de desktop (Windows)

Instalador: `dist\PlusEduc-Setup-1.0.0.exe`. Instala o PlusEduc com atalho na Área de Trabalho e no Menu Iniciar.
O aplicativo abre numa janela própria, sobe a API empacotada (`PlusEduc-API.exe`, sem precisar de Python) numa porta
local livre (padrão 18080) e mostra a interface servida por ela. Fechar a janela encerra a API.

Requisito: **MongoDB** rodando em `localhost:27017` (o serviço "MongoDB" do Windows; o app tenta iniciá-lo se estiver
parado). A configuração fica em `%APPDATA%\PlusEduc\config.json` (banco, URI e porta); o segredo das sessões é gerado
na primeira execução e guardado só ali. O log da API fica em `%APPDATA%\PlusEduc\api.log`.

## Gerar o instalador de novo

```powershell
# 1. Interface
cd ..\PlusEduc-UI; npm ci; npm run build

# 2. API como executável (PyInstaller)
cd ..\PlusEduc-BE-Python
.\.venv\Scripts\python.exe -m pip install "pyinstaller>=6.10"
.\.venv\Scripts\python.exe -m PyInstaller run_api.py --noconfirm --clean --name PlusEduc-API --onedir --console `
  --distpath ..\PlusEduc-Desktop\resources --workpath ..\PlusEduc-Desktop\.pyinstaller --specpath ..\PlusEduc-Desktop\.pyinstaller `
  --paths . --collect-submodules app --collect-submodules uvicorn --hidden-import app.main `
  --add-data "$PWD\app\compute\grade_stats.cl;app/compute" `
  --exclude-module pyopencl --exclude-module pytest --exclude-module nuitka --exclude-module tkinter

# 3. Aplicativo e instalador
cd ..\PlusEduc-Desktop; npm install; npm run dist
```

Observações do ambiente de build:

* Com Node 26 a extração automática do Electron pode falhar; extraia o zip do cache
  (`%LOCALAPPDATA%\electron\Cache\...\electron-v33.2.1-win32-x64.zip`) em `node_modules\electron\dist` e grave
  `electron.exe` em `node_modules\electron\path.txt`.
* Sem o "Modo de desenvolvedor" do Windows, o electron-builder não consegue extrair o pacote `winCodeSign` (links
  simbólicos de macOS). Extraia-o ignorando a pasta `darwin` em `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\winCodeSign-2.6.0`.
* O instalador não é assinado digitalmente: o Windows SmartScreen pode mostrar "O Windows protegeu o computador";
  clique em "Mais informações" → "Executar assim mesmo".
* O OpenCL (GPU) fica fora do executável; os cálculos usam o caminho em Python, que é o mais rápido para os volumes atuais.
