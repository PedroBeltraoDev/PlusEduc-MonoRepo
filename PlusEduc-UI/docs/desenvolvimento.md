# PlusEduc UI — Desenvolvimento local

Repositório de **demonstração / portfólio**. Não versione credenciais nem URLs de produção reais.

## Pré-requisitos

- Node.js 18+ (recomendado 20+)
- Backend PlusEduc rodando (padrão: `http://localhost:8080`)

## Configuração

```bash
cp .env.example .env
npm install
```

| Variável | Uso |
|----------|-----|
| `VITE_DEV_PROXY_TARGET` | Backend local para o proxy do Vite em `npm run dev` |
| `VITE_API_BASE_URL` | Opcional no build de produção, se a API estiver em outro domínio |

## Executar

```bash
npm run dev          # http://localhost:5173 (proxy /api -> backend)
npm run type-check
npm run build
npm run preview
```

## Autenticação

O token JWT fica no `localStorage` do navegador após login. Isso é adequado para demo local; em produção real, avalie cookies httpOnly e HTTPS.

## Deploy (opcional)

Exemplo de variáveis no painel do provedor (Vercel, Netlify, etc.):

- `VITE_API_BASE_URL` — URL pública da API com CORS configurado para o domínio do frontend

Não commite `.env` com URLs ou chaves de produção.
