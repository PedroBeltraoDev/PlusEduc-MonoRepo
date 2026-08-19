# PlusEduc UI

Dashboard educacional em **React** e **TypeScript** para gestão de turmas, alunos e atividades — interface do professor e portal do aluno, integrada à [PlusEduc API](https://github.com/PedroBeltraoDev/PlusEduc-BE).

> Repositório de **demonstração / portfólio**. Variáveis de ambiente e deploy real ficam fora do Git. Veja `docs/desenvolvimento.md`.

## Funcionalidades

- Dashboard com estatísticas e métricas
- Gestão de turmas, alunos e notas
- Criação e geração de atividades (com integração à API)
- Portal do aluno (atividades, notas, turma)
- Modo claro/escuro e layout responsivo

## Stack

- React 18 · TypeScript · Vite 6
- Tailwind CSS v4 · Radix UI · React Router 7
- Lucide React · Recharts

## Início rápido

### Pré-requisitos

- Node.js 18+
- Backend PlusEduc em execução (ex.: `http://localhost:8080`)

### Instalação

```bash
git clone https://github.com/PedroBeltraoDev/PlusEduc-UI.git
cd PlusEduc-UI
cp .env.example .env
npm install
npm run dev
```

Acesse `http://localhost:5173`. Em desenvolvimento, o Vite encaminha `/api` para o backend configurado em `VITE_DEV_PROXY_TARGET`.

### Scripts

| Comando | Descrição |
|---------|-----------|
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Build de produção |
| `npm run preview` | Preview do build |
| `npm run type-check` | Verificação TypeScript |

## Estrutura

```text
src/
├── app/
│   ├── components/   # UI, Sidebar, layouts
│   ├── pages/        # Telas do professor e do aluno
│   ├── App.tsx
│   └── routes.tsx
├── contexts/         # Autenticação
├── services/         # Cliente HTTP e APIs
├── styles/           # Tema e Tailwind
└── types/
```

## Configuração

Copie `.env.example` para `.env`. O arquivo `.env` não é versionado.

- **Desenvolvimento:** `VITE_DEV_PROXY_TARGET` (padrão: `http://localhost:8080`)
- **Produção:** opcionalmente `VITE_API_BASE_URL` se a API estiver em outro domínio (com CORS no backend)

## Sistema de design

Paleta principal: `#0A2463`, `#1E5AA8`, `#4FC3F7`. Tokens em `src/styles/theme.css`.

## Licença

MIT License — veja `ATTRIBUTIONS.md` para créditos de bibliotecas de UI.

## Autor

**Pedro Beltrão** — [GitHub](https://github.com/PedroBeltraoDev)
