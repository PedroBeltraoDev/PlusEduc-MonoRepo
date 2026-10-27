#!/usr/bin/env bash
# Reexecuta a avaliação de permissões e de regras de negócio da Sprint 08 (Git Bash, Windows).
#
# Pré-requisitos: MongoDB local, banco descartável já criado com clonar_banco.py, e dois backends
# apontando para esse banco (MONGODB_DATABASE=pluseduc_sprint8_eval):
#   - código ANTES das correções (commit a8ef154) em http://127.0.0.1:8092
#   - código DEPOIS das correções (HEAD da branch) em http://127.0.0.1:8091
# Defina PLUSEDUC_EVAL_PASSWORD (senha de teste das contas do banco descartável) e PY (python do .venv).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../resultados"
DB=pluseduc_sprint8_eval
mkdir -p "$OUT"
cd "$HERE/../../../PlusEduc-BE-Python"   # o .env (JWT_SECRET) é lido a partir desta pasta
export PYTHONUTF8=1 MONGODB_REQUIRED=false MONGODB_DATABASE=$DB
: "${PY:?defina PY com o python do .venv}"
: "${PLUSEDUC_EVAL_PASSWORD:?defina PLUSEDUC_EVAL_PASSWORD}"

run() { "$PY" -X utf8 "$@" 2>&1 | grep -v -i warn; }

run "$HERE/preparar_usuarios.py" > /dev/null
run "$HERE/listar_rotas.py" "$OUT/rotas.json" > "$OUT/rotas.txt"

for lado in antes depois; do
  [ "$lado" = antes ] && URL=http://127.0.0.1:8092 || URL=http://127.0.0.1:8091
  run "$HERE/matriz_permissoes.py" $URL $DB "$OUT/matriz_$lado.json" "$OUT/rotas.json" > "$OUT/matriz_$lado.txt"
  run "$HERE/verificacoes_permissoes.py" $URL $DB "$OUT/verificacoes_$lado.json" "$OUT/rotas.json" > "$OUT/verificacoes_$lado.txt"
  run "$HERE/preparar_usuarios.py" > /dev/null   # devolve a senha de teste da conta alterada no teste de recuperação
  run "$HERE/sonda_envio_outra_turma.py" $URL $DB cleanup > "$OUT/envio_outra_turma_$lado.txt"
  run "$HERE/sondas_regras_negocio.py" $URL $DB > "$OUT/regras_negocio_$lado.txt"
done
echo "resultados em $OUT"
