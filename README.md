# PlusEduc MonoRepo

Plataforma de gestão pedagógica da educação básica (projeto da disciplina Fábrica de Software + Tópicos Avançados, UNINASSAU, Grupo 08).
Professores e administradores gerenciam turmas, alunos, atividades, notas e frequência e acompanham indicadores e relatórios; alunos respondem
atividades e consultam notas e desempenho em um portal próprio.

## Estrutura
- `PlusEduc-UI/`: aplicação web React, TypeScript, Vite e TailwindCSS.
- `PlusEduc-BE-Python/`: API FastAPI com MongoDB local.
- `docs/`: documentação do projeto (ver abaixo).

## Execução local
Pré-requisitos: Python 3.11+ (validado com 3.12), Node 18+ (validado com 22), MongoDB em `localhost:27017`.

1. Backend (a partir de `PlusEduc-BE-Python`): criar o ambiente virtual e instalar `requirements.txt`, copiar `.env.example` para `.env` e definir `JWT_SECRET`; depois
   `.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload` (Swagger em `http://127.0.0.1:8080/docs`).
2. Frontend (a partir de `PlusEduc-UI`): `npm install` e `npm run dev -- --host 0.0.0.0 --port 5173` (o Vite encaminha `/api` para a porta 8080;
   para outro destino use `VITE_DEV_PROXY_TARGET`). Aplicação em `http://localhost:5173`.
3. Dados de demonstração: `PlusEduc-BE-Python/scripts/seed_demo_population.py` (ver `docs/DEMO_DATA_POPULATION.md`).
   Para mostrar "Esqueci minha senha" sem SMTP, defina `PASSWORD_RESET_DEMO_MODE=true` no `.env` local (somente em máquina local).

## Testes
- Backend: `PlusEduc-BE-Python/.venv/Scripts/python.exe -m pytest -q` (158 testes; veja o README do backend para rodar contra um banco descartável com `MONGODB_DATABASE`).
- Frontend: `npm run type-check` e `npm run build`.
- Testes funcionais, de validação e de navegação contra o sistema em execução: `docs/sprint-09/`.

## Documentação
| Documento | Conteúdo |
|---|---|
| `docs/PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md` | plano, requisitos, casos de uso, backlog e cronograma |
| `docs/REQUISITOS_STATUS.md` | situação real de cada requisito funcional e não funcional |
| `docs/ARQUITETURA.md` | camadas, segurança, frontend, build e o que está fora do escopo |
| `docs/MODELO_DE_DADOS.md` | coleções do MongoDB, campos, relações e débitos do modelo |
| `docs/DEMO_AND_PRESENTATION.md`, `docs/DEMO_DATA_POPULATION.md` | roteiro de demonstração e população de dados |
| `docs/sprint-08/` | permissões verificadas: matriz de rotas por perfil, resultados e capturas |
| `docs/sprint-09/` | testes completos: catálogo de casos, resultados antes e depois das correções, capturas |

Arquivos `.env`, ambientes virtuais, dependências, builds, logs e caches locais não são versionados.
