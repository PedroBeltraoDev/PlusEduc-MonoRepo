# Correção geral + PlusEduc Ultra Motion

Branch: `feat/correcao-geral-ultra-motion` (a `main` não foi alterada).

## 1. Segurança e permissões (backend)

| Problema encontrado | Correção |
|---|---|
| `POST /api/auth/register/teacher` devolvia tokens de professor na hora: qualquer pessoa obtinha acesso a turmas, alunos e notas. | O cadastro fica **pendente** (`202`, sem tokens). Login de conta pendente responde `403` com aviso, só para quem sabe a senha. O ADMIN aprova ou recusa em `GET/POST /api/admin/teacher-requests…` (tela: Configurações, visível só ao ADMIN). |
| `teacher_service.py` gravava a senha do professor **em texto puro** em `teachers` e não criava conta de acesso (o professor cadastrado não conseguia entrar). | A senha vai só para `users`, com bcrypt. Criar, alterar e desativar professor sincroniza a conta; trocar senha, e-mail ou desativar encerra as sessões. `teachers.password` não existe mais. |
| Qualquer professor criava, alterava e excluía outros professores. | CRUD de professores restrito ao ADMIN. |
| Professores acessavam **todas** as turmas, alunos, notas, atividades, correções, relatórios, dashboard e pesquisa. | Escopo central em `app/core/access.py`: professor só atua nas turmas em que é titular, nas que leciona uma disciplina ou nas ligadas ao próprio cadastro. Aplicado em todas as rotas de equipe, inclusive as legadas (`/api/teacher/activity_corrections`) e a exportação PDF. |
| A exportação PDF liberava o acesso quando o professor **não tinha cadastro**; as correções comparavam o id da conta com o id do professor (dois ids diferentes). | Professor sem cadastro ativo não recebe permissão nenhuma; a comparação usa o cadastro do professor. |
| Professor podia trazer para a turma dele um aluno matriculado na turma de outro professor, ou criar turma em nome de outro. | Transferência entre professores fica com o ADMIN; turma criada por professor é sempre dele. |
| Alterar/desativar matérias do catálogo global estava liberado a qualquer professor. | Restrito ao ADMIN (criar continua para a equipe). |

Rotas alternativas de envio de atividade foram conferidas: as duas (`/api/student-portal/...` e `/api/activity-submissions/...`) validam a turma do aluno.

## 2. Sessões e tokens

* Access token curto (padrão 30 min) e **refresh token rotativo** (`POST /api/auth/refresh`): cada uso gera um par novo; reapresentar um refresh já usado revoga toda a cadeia daquele login (detecção de roubo). Só o hash SHA-256 do `jti` fica no banco (coleção `refresh_tokens`, com TTL).
* `POST /api/auth/logout` revoga o refresh token; `POST /api/auth/change-password` troca a senha e derruba as outras sessões.
* `users.tokenVersion`: trocar/redefinir a senha ou desativar a conta invalida **todos** os tokens já emitidos.
* Limite de tentativas: login (5 falhas em 15 min por IP + e-mail, só falhas contam), cadastro e recuperação de senha → `429` com `Retry-After`.
* Em `APP_ENV=production` a API **não inicia** com `JWT_SECRET` fraco/de exemplo, `PASSWORD_RESET_DEMO_MODE=true`, e-mail de redirecionamento de código ou limite de tentativas desligado.
* Frontend: renovação automática e transparente (uma renovação por vez, mesmo com várias requisições simultâneas); a requisição que falhou é repetida, sem perder o que o usuário estava fazendo. Downloads (PDF/CSV/XLSX) usam o mesmo cliente e respeitam `VITE_API_BASE_URL`.

## 3. Integridade dos dados

* `students.class_id` e `classrooms.students` ficam coerentes em matrícula, transferência, remoção, cadastro e edição de aluno e edição da lista de alunos da turma (antes o cadastro com turma não entrava na lista e a remoção de uma turma apagava o vínculo com outra).
* Aluno em várias listas (dado legado) fica só na turma nova ao ser matriculado.
* Excluir (desativar) aluno o retira da turma e desativa a conta do portal; e-mail e nome do aluno/professor são sincronizados com a conta de acesso.
* Matrícula usa o ano corrente (`MAT-<ano>-0001`), não mais 2026 fixo.
* Paginação real no MongoDB (`skip/limit + count`) em `/students/paginated` e `/classrooms/paginated`.
* O MongoDB local é *standalone* (sem transações multi-documento); as operações compostas usam desfazer compensatório quando a segunda etapa falha.

### Migração (idempotente)

```powershell
cd PlusEduc-BE-Python
.\.venv\Scripts\python.exe scripts\migrate_security_integrity.py          # simulação
.\.venv\Scripts\python.exe scripts\migrate_security_integrity.py --apply  # grava
```

Converte/move senhas de `teachers` para `users` (bcrypt), cria contas que faltam, desativa contas de alunos e professores desativados, corrige vínculos aluno/turma e lista e-mails duplicados. Pode ser executada várias vezes.

## 4. Correções funcionais

* Configurações: "Alterar senha" exibia "Um link foi enviado para seu e-mail" sem fazer nada → agora troca a senha de verdade (também no portal do aluno).
* Removidos "Último acesso 15/04/2026" e "Chrome - Windows 11" fixos apresentados como reais; função "Professora" fixa → "Professor(a)"/"Administrador".
* Sino de notificações: os dois sinos (celular e computador) faziam consultas duplicadas a cada 30 s; agora há uma consulta compartilhada, pausada com a aba em segundo plano; o painel fecha com Esc e clique fora; o item leva à atividade.
* Turmas: ~50 `console.log` de depuração expunham nomes, e-mails e ids de alunos no console — removidos; modais fecham com Esc; lista de turmas navegável por teclado.
* Portal do aluno: rascunho local das respostas, isolado por aluno e atividade (sobrevive a recarregar a página, expira em 14 dias, é apagado no envio) e destaque da primeira questão sem resposta.

## 5. Desempenho

* Bundle inicial: 388 kB → 451 kB (gzip 122 → 144 kB) com todo o Ultra Motion; o motor de animação (85 kB, 28 kB gzip) carrega à parte (`LazyMotion`).
* Gráficos do dashboard animam só na primeira carga (trocar filtros não repete a animação).
* Notificações de professor buscam só as submissões das atividades das turmas dele (antes: a coleção inteira a cada 30 s). Relatórios e dashboard do professor consultam só as turmas dele.
* OpenCL: o padrão era `OPENCL_MIN_RECORDS=0` (GPU até para 5 notas); o benchmark documentado aponta equilíbrio perto de 100 mil registros, então o padrão passou a `50000`. Nenhum ganho novo foi medido nesta entrega.

## 6. PlusEduc Ultra Motion

Código em `PlusEduc-UI/src/motion/` e `src/styles/motion.css`, usando a biblioteca `motion` que já estava nas dependências (nenhuma dependência nova).

* **Abertura cinematográfica** (`CinematicIntro.tsx`): fundo azul-escuro com iluminação, o **SVG original do `Logo.tsx`** montado por partes (órbitas, engrenagens, livro desenhado), nome letra a letra, "Soluções Inteligentes para a Educação" e saída com profundidade. 2,2 s (Ultra), 1,6 s (Equilibrado), 0,9 s (Desempenho); botão "Pular", Esc ou clique; uma vez por sessão (ou sempre, se escolhido); pulada com movimento reduzido ou aba em segundo plano; trava de 4 s; a aplicação carrega por baixo.
* **Perfis** (Configurações → Animações, nos dois portais): Ultra (padrão), Equilibrado, Desempenho; ajuste automático (aparelho modesto pelos sinais do navegador, ou travadas longas detectadas por `PerformanceObserver`, sem loop de `requestAnimationFrame`); "Reduzir movimentos não essenciais"; `prefers-reduced-motion` sempre respeitado.
* **Componentes**: transição de página (sem animação de saída, a navegação nunca espera), entrada em sequência com teto de atraso, números com contagem curta, painéis com mola, troca de conteúdo, mensagens de erro (tremor curto no Ultra) e sucesso, indicador deslizante na sidebar (`layoutId`), modais/menus do Radix com curva de mola em CSS `linear()`, botões com resposta ao toque, cartões com elevação só com mouse, esqueletos de carregamento, troca de tema suave.
* Só `transform` e `opacity` (e desfoque de profundidade apenas no Ultra em telas maiores). Sem limite artificial de FPS: as animações seguem o ritmo do monitor. **Nenhuma taxa de FPS foi medida** nesta entrega.

## 7. Testes executados

* Backend (`MONGODB_DATABASE=pluseduc_test`, cópia descartável do banco de demonstração): **156 aprovados** (138 antes; 18 novos em `tests/test_security_regressions_real.py`).
* Testes antigos ajustados ao novo modelo, sem remoção: fixtures que usavam um "professor" fictício sem cadastro passaram a usar ADMIN; os que dependiam de contas do banco do autor criam o próprio professor (`tests/teacher_fixture.py`); o cadastro de professor testa o fluxo de aprovação.
* Frontend: `npm run type-check` e `npm run build` sem erros.
* Navegador (painel do app, banco de testes): login de professora mostra só as 3 turmas dela; access token inválido é renovado sozinho; 5 requisições simultâneas → 1 renovação, 0 falhas; troca de perfil e movimento reduzido refletidos no `<html>` e salvos; troca de senha com senha atual errada mostra o erro e Esc fecha; cadastro de professor pendente → login bloqueado → ADMIN aprova → login liberado; rascunho do aluno recuperado após recarregar; celular (375 px) + tema escuro conferidos.

## 8. Pendências conhecidas

* A abertura cinematográfica não pôde ser conferida visualmente: o painel do navegador usado nos testes estava oculto e não desenhava quadros. Confira abrindo o app (Configurações → "Mostrar a abertura sempre").
* A atribuição de disciplina (`POST /api/subjects/assignments`) continua permitindo que um professor se vincule a uma disciplina livre de qualquer turma, o que lhe dá acesso àquela turma. É a regra pedagógica atual; restringir exige decisão da coordenação.
* O limite de tentativas é em memória (um processo). Com vários servidores, usar armazenamento compartilhado.
* Tokens ficam no `localStorage` (mesmo modelo anterior). Migrar o refresh token para cookie `HttpOnly` exige mudança de CORS/proxy e foi deixado de fora.
* Virtualização de tabelas não foi necessária com os volumes atuais e não foi implementada.
