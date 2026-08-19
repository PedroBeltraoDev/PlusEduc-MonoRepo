# PlusEduc MonoRepo

Monorepo da plataforma educacional PlusEduc, reunindo o frontend React e o backend FastAPI.

## Estrutura
- `PlusEduc-UI/`: aplicação web React, TypeScript, Vite e TailwindCSS.
- `PlusEduc-BE-Python/`: API FastAPI com MongoDB local.

## Execução local
Backend: `PlusEduc-BE-Python/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload`
Frontend: `PlusEduc-UI/npm run dev -- --host 0.0.0.0 --port 5173`

## Testes
Backend: `PlusEduc-BE-Python/.venv/Scripts/python.exe -m pytest --tb=no -q`
Frontend: `npm run type-check` e `npm run build`

Arquivos `.env`, ambientes virtuais, dependências, builds, logs e caches locais não são versionados.
