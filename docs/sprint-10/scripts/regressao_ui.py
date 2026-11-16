"""Reexecuta um roteiro de interface da Sprint 09 (Selenium) contra a versão release candidate.

    PLUSEDUC_EVAL_PASSWORD=... PLUSEDUC_EVAL_DB=pluseduc_sprint10_eval \
        python regressao_ui.py testes_navegacao.py saida.json
    (também: testes_validacao_ui.py)

Variáveis: PLUSEDUC_UI (padrão http://127.0.0.1:5193) e PLUSEDUC_API (padrão http://127.0.0.1:8093).
Os roteiros originais ficam intactos em docs/sprint-09/scripts; aqui só mudam os endereços e a pasta das capturas.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S9 = HERE.parents[1] / "sprint-09" / "scripts"
script, out = sys.argv[1], sys.argv[2]

sys.path.insert(0, str(HERE))
import evid  # noqa: E402,F401 - a versão da Sprint 10 fica em sys.modules antes de o roteiro importar "evid"

source = (S9 / script).read_text(encoding="utf-8").replace("http://127.0.0.1:8091", os.environ.get("PLUSEDUC_API", "http://127.0.0.1:8093"))
# NAV-SS01 da Sprint 09 trocava só o token de acesso e esperava a volta ao login. Com a renovação de sessão (RF01)
# o esperado mudou: token de acesso inválido + refresh token válido = sessão renovada, o usuário continua na tela;
# só com os dois inválidos a sessão é encerrada (NAV-SS02).
OLD_SS01 = """    d.execute_script("localStorage.setItem('accessToken','token-invalido');")
    got = visit(d, "/aluno/notas", 2.5)
    rec("NAV-SS01", "aluno", "abrir /aluno/notas com token inválido", "/login (sessão encerrada)", got, got == "/login")
"""
NEW_SS01 = """    d.execute_script("localStorage.setItem('accessToken','token-invalido');")
    got = visit(d, "/aluno/notas", 3.0)
    renewed = d.execute_script("return localStorage.getItem('accessToken')") != "token-invalido"
    rec("NAV-SS01", "aluno", "abrir /aluno/notas com token de acesso inválido e refresh token válido", "/aluno/notas (sessão renovada, token trocado)", f"{got}; token renovado: {renewed}", got == "/aluno/notas" and renewed)
    shot(d, "n04_sessao_renovada", "Sessão — token de acesso inválido: a sessão é renovada pelo refresh token e o aluno continua na tela")
    d.execute_script("localStorage.setItem('accessToken','token-invalido'); localStorage.setItem('refreshToken','refresh-invalido');")
    got = visit(d, "/aluno/notas", 3.0)
    rec("NAV-SS02", "aluno", "abrir /aluno/notas com os dois tokens inválidos", "/login (sessão encerrada)", got, got == "/login")
    shot(d, "n05_sessao_encerrada", "Sessão — sem refresh token válido a sessão é encerrada e a tela de login avisa")
"""
if script == "testes_navegacao.py":
    assert OLD_SS01 in source, "o roteiro da Sprint 09 mudou: revise a troca do caso NAV-SS01"
    source = source.replace(OLD_SS01, NEW_SS01)
# capturas e manifestos vão para docs/sprint-10/evidencias, nunca para a pasta da Sprint 09
source = source.replace('evid.OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidencias")', "evid.OUT = evid._OUT_DIR")
sys.argv = [script, out]
exec(compile(source, str(S9 / script), "exec"), {"__name__": "__main__", "__file__": str(S9 / script)})
