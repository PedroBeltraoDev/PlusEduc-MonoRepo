"""Gera resultados/matriz_de_permissoes.md a partir de matriz_antes.json e matriz_depois.json."""
import json
from pathlib import Path

RES = Path(__file__).resolve().parents[1] / "resultados"
COLS = ["ANÔNIMO", "ALUNO", "PROFESSOR", "ADMIN"]


def cell(value):
    return "—" if value is None else str(value)


after = json.loads((RES / "matriz_depois.json").read_text(encoding="utf-8"))
before = {(r["method"], r["path"]): r for r in json.loads((RES / "matriz_antes.json").read_text(encoding="utf-8"))}
lines = [
    "# Matriz de permissões por rota (resultado real)",
    "",
    f"Código HTTP obtido ao chamar cada uma das {len(after)} rotas da API como anônimo, aluno, professor e administrador, contra o backend em execução.",
    "Rotas de leitura (GET) usam ids reais; as de escrita usam ids inexistentes e corpo vazio. Para quem tem permissão o resultado é 404/422",
    "(passou pela autorização e falhou na validação, sem alterar dados) e para quem não tem é 401/403. \"—\" = rota não exercitada (login e recuperação de senha).",
    "Quando o resultado mudou por causa das correções da Sprint 08, o valor anterior aparece em \"(antes: ...)\".",
    "",
    "| Método | Rota | Perfil exigido | Anônimo | Aluno | Professor | Admin |",
    "|---|---|---|---|---|---|---|",
]
changed = []
for row in after:
    need = "/".join(row["roles"]) if row["roles"] else ("qualquer autenticado" if row["auth"] else "público")
    res = row["results"]
    prev = before.get((row["method"], row["path"]))
    note = ""
    if prev and prev["results"] != res:
        note = " (antes: " + "/".join(cell(prev["results"][c]) for c in COLS) + ")"
        changed.append((row["method"], row["path"]))
    lines.append(f"| {row['method']} | `{row['path']}` | {need} | " + " | ".join(cell(res[c]) for c in COLS[:3]) + f" | {cell(res['ADMIN'])}{note} |")
(RES / "matriz_de_permissoes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(len(after), "rotas;", len(changed), "com resultado diferente depois das correções:")
for method, path in changed:
    print(" ", method, path)
