# PlusEduc — Roteiro de demonstração e apresentação

Atualizado na Sprint 11 para a versão 1.0.0-rc.1 com a atualização de segurança. Serve para a orientação, a gravação dos
vídeos e a banca. O passo a passo de cada tela está no [Manual do Usuário](MANUAL_DO_USUARIO.md).

> **Senhas:** as contas de demonstração usam uma senha comum definida só no MongoDB local (variável
> `PLUS_EDUC_DEMO_PASSWORD` do seed). Ela não está neste repositório e deve ser compartilhada só com quem vai apresentar.

## 1. Banco de demonstração (`escola_db`)

Situação em 19/11/2026, somente leitura:

| Item | Quantidade |
|---|---:|
| Alunos ativos | 79 |
| Professores ativos | 20 |
| Turmas ativas | 16 |
| Matérias ativas | 16 |
| Atividades / respostas | 38 / 99 |
| Lançamentos de nota | 234 |
| Administradores | **0** (criar antes da apresentação) |

## 2. Preparação, uma vez antes de apresentar

Todos os comandos rodam a partir de `PlusEduc-BE-Python`, com `PY = .\.venv\Scripts\python.exe`.

1. **Backup do banco:**

   ```powershell
   mongodump --db escola_db --out ..\backup-escola-db
   ```

2. **Migração da atualização de segurança** (idempotente; sem `--apply` ela só mostra o que faria):

   ```powershell
   $PY scripts\migrate_security_integrity.py --apply
   ```

3. **Limpeza de órfãos:** remove 3 atividades e 2 respostas sem dono. Depois, a coordenação decide como redistribuir
   as 12 turmas de um mesmo professor, já que o limite é de 5.

   ```powershell
   $PY scripts\check_database.py --repair
   ```

4. **Administrador da demonstração:**

   ```powershell
   $PY scripts\create_admin.py --email coordenacao@pluseduc.local --name "Coordenação Pedagógica"
   ```

5. **Subir o sistema:**
   - API: `$PY -m uvicorn app.main:app --port 8080`
   - Interface: `npm run dev`, dentro de `PlusEduc-UI`
   - Confira `http://127.0.0.1:8080/health`.

6. **Escolher as contas:** uma professora com turma e alunos (por exemplo `marina.ferreira@pluseduc.local`) e um aluno
   dessa turma (por exemplo `lucas.carvalho@aluno.local`).

7. **IA:** com `GEMINI_API_KEY` preenchida, a geração usa o Gemini. Sem chave ou sem rede, o gerador de reserva entra e
   a tela avisa. Vale testar a geração uma vez antes da apresentação.

## 3. Roteiro (cerca de 10 minutos, o tempo do vídeo horizontal)

| Tempo | Perfil | O que mostrar | Mensagem |
|---|---|---|---|
| 0:00–0:45 | — | abertura animada e login | problema: acompanhamento pedagógico manual e tardio |
| 0:45–2:00 | Professora | Dashboard com filtros e alunos em atenção | indicadores calculados das notas e da frequência reais |
| 2:00–3:15 | Professora | Turmas: detalhe da turma, matérias por série (BNCC), cadastro de aluno e **Liberar acesso ao portal** | cada matéria tem um professor; um aluno, uma turma |
| 3:15–4:45 | Professora | **Gerar com IA**: aluno com lacunas, **Aplicar recomendação**, adaptação inclusiva, prévia e envio | IA com recomendação explicável e alternativa sem IA |
| 4:45–6:15 | Aluno | Portal: abrir a atividade, responder (rascunho salvo), enviar e ver a correção automática | o aluno não vê o gabarito antes de enviar |
| 6:15–7:15 | Professora | sino de notificações, correção da discursiva com feedback e **Lançar notas no boletim** | correção automática + manual, nota no boletim |
| 7:15–8:15 | Professora | Notas e Frequência e Relatórios com exportação (Excel/PDF) | médias e frequência, exportação com os filtros da tela |
| 8:15–9:15 | ADMIN | turmas da escola inteira, aprovação de cadastro de professor, Histórico de operações | escopo por perfil, rastreabilidade |
| 9:15–10:00 | — | Swagger (`/docs`), modo escuro, celular, perfis de animação | API documentada, interface responsiva |

Para a banca, ter à mão:
- [`MANUAL_TECNICO.md`](MANUAL_TECNICO.md), seção 10: IA, recomendação e OpenCL;
- [`REQUISITOS_STATUS.md`](REQUISITOS_STATUS.md): o que foi e o que não foi implementado;
- [`REGRAS_DE_NEGOCIO.md`](REGRAS_DE_NEGOCIO.md).

## 4. Cuidados durante a apresentação

- **Limite de tentativas:** 5 logins errados em 15 minutos bloqueiam aquele e-mail naquele computador. Se acontecer,
  reinicie a API.
- **Troca de senha:** trocar a senha durante a demonstração encerra as outras sessões abertas daquela conta.
- **Aluno cadastrado na hora:** precisa ter o acesso liberado pela professora antes de entrar no portal.
- **Escopo da professora:** ela só vê as turmas dela. Para mostrar a escola inteira, use o ADMIN.

## 5. Checklist

- [ ] Backup do `escola_db` feito.
- [ ] Migração aplicada e `check_database.py` sem erros.
- [ ] Administrador criado e testado.
- [ ] Contas de professora e aluno testadas (login).
- [ ] Geração com IA testada (Gemini ou alternativa).
- [ ] `/health` com banco "ok"; `/docs` abrindo.
- [ ] Nenhuma senha ou chave aparecendo na tela ou no repositório.
