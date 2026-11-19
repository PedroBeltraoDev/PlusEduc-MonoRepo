# Sprint 10 — Entrega (19/11/2026, após o prazo de 14/11)

A release candidate (`../README.md`, verificada em 11/11) foi entregue com atraso. Antes da entrega, a `main` recebeu a
Sprint 09 (PR #12), a release candidate (PR #13) e a atualização de segurança e Ultra Motion (PR #14, integrado pelo PR #15).
Esta pasta guarda a verificação da versão entregue, refeita do zero em 19/11/2026 com o sistema em execução.

O banco de avaliação é `pluseduc_sprint10_entrega`, cópia do `escola_db` com a migração aplicada. O `escola_db` só foi lido.

## Resultado

| Verificação | Casos | Resultado |
|---|---:|---|
| `pytest` (backend, `resultados/testes_backend.txt`) | 190 | 190 aprovados |
| Regressão da API (`resultados/regressao_api.txt`) | 111 | 111 aprovados. São os 104 da RC, 14 deles reescritos para as regras novas, mais 7 de segurança (SEG-01 a SEG-07) |
| Navegação com Selenium (`resultados/regressao_navegacao.json`) | 91 | 91 aprovados |
| Validação pela interface (`resultados/regressao_validacao_ui.json`) | 15 | 15 aprovados |
| Revisão das telas (`resultados/revisao_interface.json`) | 36 | sem rolagem lateral. O único erro de console é o 403 esperado do login pendente |
| Consistência do banco (`resultados/banco_antes.txt` e `banco_depois.txt`) | 22 | cópia: 2 erros e 1 aviso. Depois da migração e do reparo: 0 erros e 1 aviso |
| Migração (`resultados/migracao_1.json` e `migracao_2.json`) | — | 2 senhas removidas de `teachers`. Na segunda execução, nenhuma alteração |

## Casos reescritos na regressão da API

Algumas regras mudaram de propósito com a atualização de segurança. Os casos que esperavam o comportamento antigo foram
reescritos em `scripts/regressao_entrega.py`, e cada um explica a mudança:

- **TUR-06, TUR-14, ALU-05 e ATI-03:** turma fora do escopo ou inexistente responde 403 para o professor; o ADMIN continua recebendo 404 ou 400.
- **TUR-05 e TUR-15:** turma criada por professor é sempre dele; o limite de 5 turmas é testado pelo ADMIN.
- **PRO-01 a PRO-05 e MAT-03:** criar, alterar e excluir professores e alterar ou desativar matérias passou a ser só do ADMIN.
- **REL-01:** o dashboard do professor mostra só as turmas dele.
- **SEN-02:** trocar a senha encerra as sessões, e a senha fica só em `users`.

## Observações da execução

- **Limite de cadastros:** uma rodada da regressão da API usa exatamente os 10 cadastros públicos por hora do limite. Como o limite fica em memória, a API foi reiniciada antes de cada suíte.
- **Abertura animada:** o Windows desta máquina pede movimento reduzido, e o app respeita isso. Os roteiros marcam a abertura como já vista, e as capturas `u01` e `u02` emulam um navegador sem essa preferência.
- **Erros de console na troca de usuário:** o roteiro limpa o `localStorage` com o app do usuário anterior aberto, e isso gerava 401 que não acontecem com o usuário. Agora o roteiro descarta esse log. Um login limpo não gera erro nenhum, o que foi conferido à parte.

## Como reproduzir

Com o MongoDB local, a partir de `PlusEduc-BE-Python` (`PY` = `.venv\Scripts\python.exe`):

```powershell
$env:PLUSEDUC_EVAL_PASSWORD = "<senha de teste>"
$PY ..\docs\sprint-10\scripts\preparar_entrega.py pluseduc_sprint10_entrega
# API em :8093 (MONGODB_DATABASE=pluseduc_sprint10_entrega) e interface em :5193 (VITE_DEV_PROXY_TARGET=http://127.0.0.1:8093)
$PY ..\docs\sprint-10\scripts\regressao_entrega.py http://127.0.0.1:8093 pluseduc_sprint10_entrega ..\docs\sprint-10\entrega\resultados\regressao_api.json
$env:PLUSEDUC_EVAL_DB = "pluseduc_sprint10_entrega"; $env:PLUSEDUC_EVID_DIR = "..\docs\sprint-10\entrega\evidencias"
python ..\docs\sprint-10\scripts\regressao_ui.py testes_navegacao.py ..\docs\sprint-10\entrega\resultados\regressao_navegacao.json
python ..\docs\sprint-10\scripts\regressao_ui.py testes_validacao_ui.py ..\docs\sprint-10\entrega\resultados\regressao_validacao_ui.json
$env:PLUSEDUC_ADMIN_EMAIL = "admin.avaliacao@pluseduc.local"; $env:PLUSEDUC_RESULT_DIR = "..\docs\sprint-10\entrega\resultados"
python ..\docs\sprint-10\scripts\capturas_rc.py
python ..\docs\sprint-10\scripts\gerar_pdf_entrega.py <PDF das Sprints 01-09> <PDF de saída 01-10>
```
