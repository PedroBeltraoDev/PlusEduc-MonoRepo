"""Regressão funcional da Sprint 10 (release candidate), contra a API em execução e um banco descartável.

Reaproveita o catálogo de 92 casos da Sprint 09 (docs/sprint-09/scripts/testes_funcionais.py) e acrescenta os
casos das pendências fechadas nesta sprint: renovação de sessão (SES), troca de senha (SEN), aprovação do cadastro
de professor (APR) e professor responsável ativo na turma (TUR-16, TUR-17).

    PLUSEDUC_EVAL_PASSWORD=... python regressao_api.py http://127.0.0.1:8093 pluseduc_sprint10_eval saida.json

O caso AUT-10 da Sprint 09 esperava acesso imediato no cadastro público de professor; agora o esperado é 202 com
o cadastro pendente (RF04), por isso ele é substituído aqui.
"""
import importlib.util
import sys
from pathlib import Path

S9 = Path(__file__).resolve().parents[2] / "sprint-09" / "scripts" / "testes_funcionais.py"
spec = importlib.util.spec_from_file_location("testes_funcionais_s9", S9)
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)  # registra os 92 casos (lê BASE, banco e saída de sys.argv)

c, db, H, TOK, X, PW, RUN, CREATED, st, caso, login = t.c, t.db, t.H, t.TOK, t.X, t.PW, t.RUN, t.CREATED, t.st, t.caso, t.login
ANTES = len(t.CASES)


# ------------------------------------------------------------------ RF04: aprovação do cadastro de professor
@caso("AUT-10", "Autenticação", "Cadastro público de professor fica pendente",
      "POST /api/auth/register/teacher com dados válidos",
      "202, status PENDING_APPROVAL, nenhum token, registros pendentes em users e teachers")
def _(x):
    email = f"prof.s10.{RUN}@professor.local"
    r = c.post("/api/auth/register/teacher", json={"name": "Professor Teste Sprint Dez", "email": email, "password": PW})
    CREATED["users"].append(email)
    CREATED["teachers"].append(email)
    j = r.json()
    user, teacher = db.users.find_one({"email": email}), db.teachers.find_one({"email": email})
    ok = (r.status_code == 202 and j.get("status") == "PENDING_APPROVAL" and "accessToken" not in j
          and user and user.get("active") is False and user.get("pendingApproval") is True
          and teacher and teacher.get("approval_status") == "PENDING")
    X["new_teacher_email"] = email
    X["new_teacher_id"] = str(teacher["_id"]) if teacher else ""
    return f"HTTP {r.status_code}; status={j.get('status')}; token na resposta: {'accessToken' in j}; pendente no banco: {bool(user and user.get('pendingApproval'))}", bool(ok)


@caso("APR-01", "Aprovação de professor", "Professor pendente não entra",
      "Login do professor pendente com a senha certa e com senha errada",
      "403 com aviso de aprovação pendente; com senha errada, 401 genérico (não revela o cadastro)")
def _(x):
    a = login(X["new_teacher_email"])
    b = login(X["new_teacher_email"], "senha-errada")
    return f"senha certa: {st(a, 403)[0]}; senha errada: HTTP {b.status_code}", a.status_code == 403 and b.status_code == 401


@caso("APR-02", "Aprovação de professor", "Só o ADMIN vê os cadastros pendentes",
      "GET /api/teachers/pending como professora e como administrador; GET /api/teachers",
      "professora 403; administrador 200 com o cadastro; pendente fora da lista de professores")
def _(x):
    a = c.get("/api/teachers/pending", headers=H(TOK["prof"]))
    b = c.get("/api/teachers/pending", headers=H(TOK["admin"]))
    pend = [i["email"] for i in b.json()] if b.status_code == 200 else []
    lista = [i["email"] for i in c.get("/api/teachers", headers=H(TOK["admin"])).json()]
    ok = a.status_code == 403 and X["new_teacher_email"] in pend and X["new_teacher_email"] not in lista
    return f"professora: {a.status_code}; admin: {b.status_code} ({len(pend)} pendente(s)); aparece na lista de professores: {X['new_teacher_email'] in lista}", ok


@caso("APR-03", "Aprovação de professor", "ADMIN aprova e o professor passa a entrar",
      "POST /api/teachers/{id}/approve como professora e como administrador; depois login do professor",
      "professora 403; administrador 200; login 200 com papel TEACHER; aprovar de novo 404")
def _(x):
    a = c.post(f"/api/teachers/{X['new_teacher_id']}/approve", headers=H(TOK["prof"]))
    b = c.post(f"/api/teachers/{X['new_teacher_id']}/approve", headers=H(TOK["admin"]))
    lg = login(X["new_teacher_email"])
    again = c.post(f"/api/teachers/{X['new_teacher_id']}/approve", headers=H(TOK["admin"]))
    if lg.status_code == 200:
        X["new_teacher_tokens"] = lg.json()
    ok = a.status_code == 403 and b.status_code == 200 and lg.status_code == 200 and lg.json().get("role") == "TEACHER" and again.status_code == 404
    return f"professora: {a.status_code}; admin: {b.status_code}; login: {lg.status_code}; aprovar de novo: {again.status_code}", ok


@caso("APR-04", "Aprovação de professor", "ADMIN recusa e o cadastro é removido",
      "Novo cadastro público; POST /api/teachers/{id}/reject como administrador; login; novo cadastro com o mesmo e-mail",
      "204; registros removidos de users e teachers; login 401; e-mail liberado (202)")
def _(x):
    email = f"prof.recusado.{RUN}@professor.local"
    CREATED["users"].append(email)
    CREATED["teachers"].append(email)
    c.post("/api/auth/register/teacher", json={"name": "Professor Recusado Teste", "email": email, "password": PW})
    tid = str(db.teachers.find_one({"email": email})["_id"])
    r = c.post(f"/api/teachers/{tid}/reject", headers=H(TOK["admin"]))
    sobrou = bool(db.users.find_one({"email": email}) or db.teachers.find_one({"email": email}))
    lg = login(email)
    again = c.post("/api/auth/register/teacher", json={"name": "Professor Recusado Teste", "email": email, "password": PW})
    ok = r.status_code == 204 and not sobrou and lg.status_code == 401 and again.status_code == 202
    return f"recusa: {r.status_code}; sobrou no banco: {sobrou}; login: {lg.status_code}; novo cadastro: {again.status_code}", ok


NOVOS_APR = t.CASES[ANTES:]
del t.CASES[ANTES:]
# o AUT-10 novo substitui o antigo e os casos de aprovação entram logo depois do AUT-12 (o TUR-15 usa esse professor já ativo)
pos = next(i for i, case in enumerate(t.CASES) if case[0] == "AUT-10")
t.CASES[pos] = NOVOS_APR[0]
pos12 = next(i for i, case in enumerate(t.CASES) if case[0] == "AUT-12")
t.CASES[pos12 + 1:pos12 + 1] = NOVOS_APR[1:]


# ------------------------------------------------------------------ RF01: renovação de sessão
@caso("SES-01", "Sessão", "Renovar a sessão com o refresh token",
      "POST /api/auth/refresh com o refreshToken do login; usar o novo token de acesso",
      "200 com novo par de tokens; o novo token abre GET /api/classrooms")
def _(x):
    r = c.post("/api/auth/refresh", json={"refreshToken": X["new_teacher_tokens"]["refreshToken"]})
    j = r.json()
    use = c.get("/api/classrooms", headers=H(j.get("accessToken", "x")))
    return f"renovação: HTTP {r.status_code}; papel: {j.get('role')}; uso do novo token: {use.status_code}", r.status_code == 200 and use.status_code == 200


@caso("SES-02", "Sessão", "Refresh recusa token de acesso e token inválido",
      "POST /api/auth/refresh com o accessToken, com texto qualquer e sem corpo",
      "401, 401 e 422")
def _(x):
    a = c.post("/api/auth/refresh", json={"refreshToken": X["new_teacher_tokens"]["accessToken"]})
    b = c.post("/api/auth/refresh", json={"refreshToken": "nao-e-um-token"})
    d = c.post("/api/auth/refresh", json={})
    return f"token de acesso: {a.status_code}; inválido: {b.status_code}; sem corpo: {d.status_code}", (a.status_code, b.status_code, d.status_code) == (401, 401, 422)


@caso("SES-03", "Sessão", "Refresh token continua sem abrir a API",
      "GET /api/classrooms com o refreshToken no cabeçalho Authorization",
      "401")
def _(x):
    r = c.get("/api/classrooms", headers=H(X["new_teacher_tokens"]["refreshToken"]))
    return st(r, 401)


# ------------------------------------------------------------------ RF03: troca de senha logado
@caso("SEN-01", "Troca de senha", "Senha atual incorreta ou nova senha inválida",
      "POST /api/auth/change-password com senha atual errada, com nova senha de 3 caracteres e com a mesma senha",
      "400 \"Senha atual incorreta\", 422 e 400")
def _(x):
    h = H(X["new_teacher_tokens"]["accessToken"])
    a = c.post("/api/auth/change-password", headers=h, json={"currentPassword": "errada", "newPassword": "Nova@12345"})
    b = c.post("/api/auth/change-password", headers=h, json={"currentPassword": PW, "newPassword": "123"})
    d = c.post("/api/auth/change-password", headers=h, json={"currentPassword": PW, "newPassword": PW})
    return f"atual errada: {st(a, 400)[0]}; curta: {b.status_code}; igual à atual: {d.status_code}", (a.status_code, b.status_code, d.status_code) == (400, 422, 400)


@caso("SEN-02", "Troca de senha", "Trocar a própria senha",
      "POST /api/auth/change-password com a senha atual correta; login com a senha antiga e com a nova",
      "200; senha antiga 401; senha nova 200; hash novo em users e teachers")
def _(x):
    from app.core.passwords import verify_password
    nova = "Nova@" + RUN
    r = c.post("/api/auth/change-password", headers=H(X["new_teacher_tokens"]["accessToken"]), json={"currentPassword": PW, "newPassword": nova})
    old, new = login(X["new_teacher_email"]), login(X["new_teacher_email"], nova)
    hashes = all(verify_password(nova, db[coll].find_one({"email": X["new_teacher_email"]})["password"]) for coll in ("users", "teachers"))
    return f"troca: {r.status_code}; senha antiga: {old.status_code}; senha nova: {new.status_code}; hash atualizado nas duas coleções: {hashes}", (r.status_code, old.status_code, new.status_code) == (200, 401, 200) and hashes


@caso("SEN-03", "Troca de senha", "Troca de senha exige login",
      "POST /api/auth/change-password sem token",
      "401")
def _(x):
    return st(c.post("/api/auth/change-password", json={"currentPassword": PW, "newPassword": "Nova@12345"}), 401)


# ------------------------------------------------------------------ turma: professor responsável ativo
@caso("TUR-16", "Turmas", "Turma não aceita professor inativo",
      "POST /api/classrooms com professor excluído (inativo); PUT trocando para professor inexistente",
      "400 \"Professor responsável não encontrado ou inativo\" nos dois")
def _(x):
    email = f"prof.inativo.{RUN}@professor.local"
    CREATED["teachers"].append(email)
    tid = str(db.teachers.insert_one({"name": "Professor Inativo Teste", "email": email, "active": False, "subjects": []}).inserted_id)
    a = c.post("/api/classrooms", headers=H(TOK["admin"]), json={"name": f"Turma Inativo {RUN}", "year": 2026, "gradeLevel": "6º Ano do Ensino Fundamental", "teacherId": tid})
    if a.status_code == 201:
        CREATED["classrooms"].append(a.json()["id"])
    b = c.put(f"/api/classrooms/{X['class_id']}", headers=H(TOK["admin"]), json={"teacherId": "000000000000000000000000"})
    return f"criar: {st(a, 400)[0]}; editar: {b.status_code}", a.status_code == 400 and b.status_code == 400


@caso("TUR-17", "Turmas", "ADMIN cria turma escolhendo o professor",
      "POST /api/classrooms como administrador com teacherId de uma professora ativa (o que a tela envia)",
      "201 e turma gravada com a professora escolhida")
def _(x):
    name = f"Turma Admin {RUN}"
    r = c.post("/api/classrooms", headers=H(TOK["admin"]), json={"name": name, "year": 2026, "gradeLevel": "8º Ano do Ensino Fundamental", "teacherId": x["teacher2"], "subjects": []})
    if r.status_code == 201:
        CREATED["classrooms"].append(r.json()["id"])
    saved = db.classrooms.find_one({"name": name}) or {}
    return f"{st(r, 201)[0]}; professora gravada: {str(saved.get('teacher_id')) == x['teacher2']}", r.status_code == 201 and str(saved.get("teacher_id")) == x["teacher2"]


t.VALIDACAO.update({"APR-01", "SES-02", "SES-03", "SEN-01", "SEN-03", "TUR-16"})

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "PlusEduc-BE-Python"))
    print(f"{ANTES} casos da Sprint 09 + {len(t.CASES) - ANTES} novos = {len(t.CASES)}")
    t.main()
