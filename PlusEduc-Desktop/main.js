// PlusEduc - aplicativo de desktop.
// Abre uma janela própria, sobe a API empacotada (PlusEduc-API.exe) em segundo plano numa porta local
// livre e mostra a interface servida por ela. Ao fechar o aplicativo, a API é encerrada junto.
const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
const { spawn, execFile } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const path = require('node:path');

const PACKAGED = app.isPackaged;
const RESOURCES = PACKAGED ? process.resourcesPath : path.join(__dirname, 'resources');
const API_EXE = path.join(RESOURCES, 'PlusEduc-API', 'PlusEduc-API.exe');
const UI_DIR = PACKAGED ? path.join(process.resourcesPath, 'ui') : path.join(__dirname, '..', 'PlusEduc-UI', 'dist');

let mainWindow = null;
let apiProcess = null;
let quitting = false;

// ---- configuração local (fica em %APPDATA%\PlusEduc\config.json) -------------------------------
function loadConfig() {
  const file = path.join(app.getPath('userData'), 'config.json');
  let config = {};
  try {
    config = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    // primeira execução
  }
  const defaults = {
    mongodbUri: 'mongodb://localhost:27017',
    mongodbDatabase: 'escola_db',
    // Segredo próprio desta instalação (assina as sessões); gerado uma vez e guardado só aqui.
    jwtSecret: crypto.randomBytes(48).toString('base64url'),
    preferredPort: 18080,
  };
  const merged = { ...defaults, ...config };
  if (JSON.stringify(merged) !== JSON.stringify(config)) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(merged, null, 2), 'utf8');
  }
  return { ...merged, file };
}

// ---- utilitários de rede ------------------------------------------------------------------------
function canConnect(host, port, timeoutMs = 1500) {
  return new Promise((resolve) => {
    const socket = net.connect({ host, port });
    const done = (ok) => {
      socket.destroy();
      resolve(ok);
    };
    socket.setTimeout(timeoutMs, () => done(false));
    socket.once('connect', () => done(true));
    socket.once('error', () => done(false));
  });
}

function freePort(preferred) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => {
      const fallback = net.createServer();
      fallback.listen(0, '127.0.0.1', () => {
        const { port } = fallback.address();
        fallback.close(() => resolve(port));
      });
    });
    server.listen(preferred, '127.0.0.1', () => server.close(() => resolve(preferred)));
  });
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    const request = http.get(url, { timeout: 2000 }, (response) => {
      let body = '';
      response.on('data', (chunk) => (body += chunk));
      response.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(error);
        }
      });
    });
    request.on('timeout', () => request.destroy(new Error('timeout')));
    request.on('error', reject);
  });
}

function mongoParts(uri) {
  const match = /mongodb:\/\/(?:[^@/]+@)?([^:/,]+)(?::(\d+))?/.exec(uri);
  return { host: match ? match[1] : 'localhost', port: match && match[2] ? Number(match[2]) : 27017 };
}

function tryStartMongoService() {
  return new Promise((resolve) => {
    execFile('net', ['start', 'MongoDB'], { windowsHide: true }, () => resolve());
  });
}

// ---- tela de carregamento ------------------------------------------------------------------------
function setStatus(text) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents
      .executeJavaScript(`document.getElementById('status').textContent = ${JSON.stringify(text)};`)
      .catch(() => undefined);
  }
}

function showError(text) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents
      .executeJavaScript(
        `document.getElementById('bar').style.display='none';` +
          `document.getElementById('status').textContent='Não foi possível iniciar o PlusEduc';` +
          `const e=document.getElementById('erro'); e.style.display='block'; e.textContent=${JSON.stringify(text)};`,
      )
      .catch(() => undefined);
  }
}

// ---- API ---------------------------------------------------------------------------------------
function startApi(config, port) {
  const logFile = path.join(app.getPath('userData'), 'api.log');
  const log = fs.createWriteStream(logFile, { flags: 'w' });
  apiProcess = spawn(API_EXE, ['--host', '127.0.0.1', '--port', String(port), '--workers', '1'], {
    cwd: path.dirname(API_EXE),
    windowsHide: true,
    env: {
      ...process.env,
      APP_ENV: 'desktop',
      JWT_SECRET: config.jwtSecret,
      MONGODB_URI: config.mongodbUri,
      MONGODB_DATABASE: config.mongodbDatabase,
      MONGODB_REQUIRED: 'true',
      STATIC_DIR: UI_DIR,
      CORS_ALLOWED_ORIGINS: `http://127.0.0.1:${port}`,
      LOG_LEVEL: 'WARNING',
    },
  });
  apiProcess.stdout.pipe(log);
  apiProcess.stderr.pipe(log);
  apiProcess.once('exit', (code) => {
    apiProcess = null;
    if (!quitting) {
      showError(`O serviço interno do PlusEduc parou (código ${code}).\nDetalhes em: ${logFile}`);
    }
  });
  return logFile;
}

async function waitForApi(port, attempts = 60) {
  for (let i = 0; i < attempts; i += 1) {
    if (!apiProcess) return false;
    try {
      const health = await getJson(`http://127.0.0.1:${port}/health`);
      if (health.status === 'ok') return true;
    } catch {
      // ainda subindo
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function stopApi() {
  if (!apiProcess) return;
  const pid = apiProcess.pid;
  apiProcess = null;
  // Encerra a árvore inteira (o uvicorn pode ter processos filhos).
  execFile('taskkill', ['/pid', String(pid), '/T', '/F'], { windowsHide: true }, () => undefined);
}

// ---- janela ------------------------------------------------------------------------------------
async function boot() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    title: 'PlusEduc',
    icon: path.join(__dirname, 'build', 'icon.png'),
    backgroundColor: '#0A2463',
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      spellcheck: true,
    },
  });
  Menu.setApplicationMenu(null);
  mainWindow.once('ready-to-show', () => mainWindow.show());
  // Título fixo do aplicativo (a página tem um título de site).
  mainWindow.on('page-title-updated', (event) => event.preventDefault());
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Links externos abrem no navegador padrão; a navegação do app fica dentro da janela.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });

  await mainWindow.loadFile(path.join(__dirname, 'loading.html'));

  if (!fs.existsSync(API_EXE) || !fs.existsSync(path.join(UI_DIR, 'index.html'))) {
    showError('Arquivos do aplicativo não encontrados. Reinstale o PlusEduc.');
    return;
  }

  const config = loadConfig();
  const mongo = mongoParts(config.mongodbUri);
  setStatus('Conectando ao banco de dados…');
  if (!(await canConnect(mongo.host, mongo.port))) {
    await tryStartMongoService();
    if (!(await canConnect(mongo.host, mongo.port, 4000))) {
      showError(
        `O MongoDB não está em execução em ${mongo.host}:${mongo.port}.\n` +
          'Inicie o serviço "MongoDB" (Serviços do Windows) e abra o PlusEduc de novo.\n' +
          `Configuração: ${config.file}`,
      );
      return;
    }
  }

  setStatus('Iniciando o PlusEduc…');
  const port = await freePort(config.preferredPort);
  const logFile = startApi(config, port);
  if (!(await waitForApi(port))) {
    if (apiProcess) showError(`O serviço interno não respondeu a tempo.\nDetalhes em: ${logFile}`);
    stopApi();
    return;
  }
  await mainWindow.loadURL(`http://127.0.0.1:${port}/login`);
}

// Uma instância só: abrir de novo traz a janela existente para frente.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
  app.whenReady().then(() => {
    app.setAppUserModelId('br.com.pluseduc.desktop');
    boot().catch((error) => {
      dialog.showErrorBox('PlusEduc', String(error && error.stack ? error.stack : error));
    });
  });
  app.on('before-quit', () => {
    quitting = true;
    stopApi();
  });
  app.on('window-all-closed', () => {
    quitting = true;
    stopApi();
    app.quit();
  });
}
