"""Gera o PDF da Sprint 11 (mesmo visual das sprints anteriores) e o junta ao PDF consolidado das Sprints 01 a 10.

    PYTHONPATH=<pasta com o pacote markdown> python gerar_pdf_sprint11.py <pdf das sprints 01-10> <pdf de saída 01-11>

O conteúdo vem dos próprios documentos do repositório (Markdown convertido em HTML e impresso pelo Chrome):
Manual do Usuário, Manual Técnico, índice da documentação final, casos de uso, regras de negócio e o registro da
Sprint 11 (revisão do código, correções, organização do GitHub e pendências). As imagens são embutidas no PDF, os
diagramas Mermaid são desenhados no navegador e os links para arquivos do repositório viram links do GitHub.
Requer o pacote ``markdown`` (pip install markdown) e Chrome com Selenium.
"""
import base64
import html
import os
import re
import sys
import time
from pathlib import Path

import markdown
from pypdf import PdfReader, PdfWriter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
REPO = "https://github.com/PedroBeltraoDev/PlusEduc-MonoRepo"
SRC_PDF, OUT_PDF = sys.argv[1], sys.argv[2]
NAVY = "#1F3864"
PRAZO, ENTREGA = "21/11/2026", "19/11/2026"
e = html.escape


def read(rel: str) -> str:
    return (DOCS / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def section(text: str, start: str, end: str | None = None) -> str:
    """Trecho do Markdown entre o título ``start`` (incluído) e o título ``end`` (excluído)."""
    i = text.index(start)
    j = text.index(end, i + len(start)) if end else len(text)
    return text[i:j].strip() + "\n"


def drop_title_and_toc(text: str) -> str:
    """Tira o título principal (a seção do PDF já tem o seu) e o sumário com âncoras do GitHub."""
    text = re.sub(r"\A# [^\n]*\n", "", text.lstrip())
    text = re.sub(r"\n## Sumário\n.*?\n---\n", "\n", text, flags=re.S)
    return text


def demote(text: str) -> str:
    """Um nível a menos em cada título (## vira ###), para caber sob o título numerado da seção do PDF."""
    return re.sub(r"^(#{2,5}) ", lambda m: "#" + m.group(1) + " ", text, flags=re.M)


def to_html(text: str, base: Path) -> str:
    """Markdown -> HTML com imagens embutidas, Mermaid desenhado no navegador e links do repositório no GitHub."""
    text = re.sub(r"```mermaid\n(.*?)```", lambda m: f'<div class="mermaid">{e(m.group(1))}</div>', text, flags=re.S)
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])

    def image(m):
        src = m.group(1)
        path = (base / src).resolve()
        if path.is_file():
            data = base64.b64encode(path.read_bytes()).decode()
            return f'src="data:image/png;base64,{data}"'
        return m.group(0)

    body = re.sub(r'src="([^"]+\.png)"', image, body)

    def link(m):
        href = m.group(1)
        if re.match(r"^(https?:|mailto:|#)", href):
            return m.group(0)
        target = (base / href.split("#")[0]).resolve()
        try:
            rel = target.relative_to(DOCS.parent).as_posix()
        except ValueError:
            return m.group(0)
        kind = "tree" if target.is_dir() else "blob"
        return f'href="{REPO}/{kind}/main/{rel}"'

    return re.sub(r'href="([^"]+)"', link, body)


def table(rows):
    return "<table><tbody>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows) + "</tbody></table>"


# ----------------------------------------------------------------------------- conteúdo
s11 = read("sprint-11/README.md")
plano = read("PLANO_DE_PROJETO_FABRICA_DE_SOFTWARE.md")
parts = []
P = parts.append
P(f"""
<section class="cover">
  <h1 class="cover-title">SPRINT 11</h1>
  <p class="cover-sub">PREPARAÇÃO PARA ENTREGA</p>
  <p class="sub">PlusEduc — Plataforma de Gestão Pedagógica<br>com Análise de Aprendizagem</p>
  {table([
      ("DISCIPLINA", "Fábrica de Software + Tópicos Avançados"),
      ("INSTITUIÇÃO", "UNINASSAU"),
      ("GRUPO", "08"),
      ("SCRUM MASTER", "Pedro Antônio Silva Pedroso Beltrão"),
      ("INTEGRANTES", "Pedro Antônio Silva Pedroso Beltrão — 01605602 (Scrum Master; desenvolvimento backend e frontend)<br>"
                      "André Marcílio da Silva Ferreira — 01616701 (UI/UX, testes e documentação; atualização de segurança e Ultra Motion)<br>"
                      "Evandro Albuquerque do Rêgo Lima — 01607434 (UI/UX, testes e documentação)"),
      ("PRAZO DA SPRINT", PRAZO),
      ("DATA DA ENTREGA", ENTREGA),
      ("VERSÃO", "1.0.0-rc.1 com a atualização de segurança e Ultra Motion"),
      ("REPOSITÓRIO", f'<a href="{REPO}">{REPO}</a> — branch main'),
      ("DOCUMENTAÇÃO", f'<a href="{REPO}/tree/main/docs">{REPO}/tree/main/docs</a>'),
  ])}
  <p class="note">Documento consolidado: as Sprints 01 a 10 (já entregues) estão nas páginas anteriores, seguidas deste documento da Sprint 11.</p>
</section>
<h1>Conteúdo da Sprint 11</h1>
<ol class="toc">
  <li><b>Manual do Usuário</b> — uso do sistema por professor, administrador e aluno, com as telas.</li>
  <li><b>Manual Técnico</b> — arquitetura, instalação, configuração, execução, APIs, componente de IA e manutenção.</li>
  <li><b>Documentação final consolidada</b> — índice dos documentos, casos de uso com a situação real e regras de negócio.</li>
  <li><b>Revisão do código</b> — o que foi verificado e com que ferramentas.</li>
  <li><b>Principais correções e melhorias</b> — defeitos encontrados, correções e verificação.</li>
  <li><b>Repositório GitHub</b> — organização, segurança e histórico.</li>
  <li><b>Pendências e próximos passos</b>.</li>
</ol>
<p>Os manuais e os demais documentos também estão no repositório, na pasta <a href="{REPO}/tree/main/docs">docs/</a>
(<code>MANUAL_DO_USUARIO.md</code>, <code>MANUAL_TECNICO.md</code>, <code>REGRAS_DE_NEGOCIO.md</code> e o índice <code>docs/README.md</code>).</p>
""")

P('<h1 id="manual-usuario">1. Manual do Usuário</h1>' + to_html(demote(drop_title_and_toc(read("MANUAL_DO_USUARIO.md"))), DOCS))
P('<h1 id="manual-tecnico">2. Manual Técnico</h1>' + to_html(demote(drop_title_and_toc(read("MANUAL_TECNICO.md"))), DOCS))

indice = drop_title_and_toc(read("README.md"))
casos = section(plano, "### Principais casos de uso", "### Diagrama de casos de uso")
regras = drop_title_and_toc(read("REGRAS_DE_NEGOCIO.md"))
P('<h1 id="documentacao">3. Documentação final consolidada</h1>'
  + "<p>Os documentos produzidos ao longo das sprints foram revisados para refletir a versão efetivamente desenvolvida. "
  + "Os links abaixo levam aos arquivos no GitHub.</p>"
  + "<h2>3.1 Índice dos documentos</h2>" + to_html(demote(indice), DOCS)
  + "<h2>3.2 Casos de uso — situação real</h2>" + to_html(casos.replace("### Principais casos de uso\n", ""), DOCS)
  + "<h2>3.3 Regras de negócio</h2>" + to_html(demote(demote(regras)), DOCS))

for numero, titulo, inicio, fim in (
    (4, "Revisão do código", "## 2. Revisão do código", "## 3. Correções e melhorias"),
    (5, "Principais correções e melhorias", "## 3. Correções e melhorias", "## 5. Organização do GitHub"),
    (6, "Repositório GitHub", "## 5. Organização do GitHub", "## 6. Pendências e próximos passos"),
    (7, "Pendências e próximos passos", "## 6. Pendências e próximos passos", "## 7. Como reproduzir"),
):
    trecho = re.sub(r"\A## [^\n]*\n", "", section(s11, inicio, fim))
    trecho = trecho.replace("## 4. Verificação", "### Verificação")
    extra = f'<p>Repositório: <a href="{REPO}">{REPO}</a> (branch <code>main</code>).</p>' if numero == 6 else ""
    P(f"<h1>{numero}. {titulo}</h1>" + extra + to_html(trecho, DOCS / "sprint-11"))

CSS = f"""
@page {{ size: A4; margin: 22mm 16mm 18mm 16mm; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #222; }}
h1, h2, h3, h4 {{ color: {NAVY}; page-break-after: avoid; }}
h1 {{ font-size: 17pt; border-bottom: 2px solid {NAVY}; padding-bottom: 3px; page-break-before: always; margin-top: 0; }}
h2 {{ font-size: 13.5pt; margin: 18px 0 6px; }}
h3 {{ font-size: 11.5pt; margin: 14px 0 6px; }}
h4 {{ font-size: 10.5pt; margin: 12px 0 4px; }}
p, li {{ line-height: 1.4; }}
a {{ color: #1E5AA8; text-decoration: none; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 8.6pt; }}
th {{ background: {NAVY}; color: #fff; text-align: left; padding: 4px 5px; }}
td {{ border-bottom: 1px solid #d9dde5; padding: 3px 5px; vertical-align: top; }}
tr:nth-child(even) td {{ background: #eef2f8; }}
tr {{ page-break-inside: avoid; }}
code {{ font-family: "Courier New", monospace; font-size: 8.6pt; background: #f2f4f8; padding: 0 2px; }}
pre {{ font-family: "Courier New", monospace; font-size: 8pt; background: #f2f4f8; padding: 8px; border-left: 3px solid {NAVY}; white-space: pre-wrap; page-break-inside: avoid; }}
pre code {{ background: none; padding: 0; }}
img {{ max-width: 100%; max-height: 215mm; border: 1px solid #c8cdd6; display: block; margin: 4px auto; }}
td img {{ max-height: 110mm; }}
p:has(> img) {{ page-break-inside: avoid; }}
blockquote {{ border-left: 3px solid #4FC3F7; margin: 8px 0; padding: 2px 10px; color: #333; background: #f5f9fc; }}
.mermaid {{ text-align: center; margin: 10px 0; page-break-inside: avoid; }}
.cover {{ text-align: center; padding-top: 50px; }}
.cover-title {{ font-size: 32pt; border: 0; page-break-before: avoid; margin: 0; }}
.cover-sub {{ font-size: 17pt; color: {NAVY}; font-weight: bold; margin: 4px 0 18px; }}
.cover .sub {{ font-size: 12pt; color: #333; }}
.cover table {{ text-align: left; font-size: 9pt; margin-top: 18px; }}
.cover td:first-child {{ background: #dce4f0; font-weight: bold; color: {NAVY}; width: 28%; }}
.cover .note {{ text-align: left; font-size: 10.5pt; margin-top: 16px; }}
.toc li {{ margin: 4px 0; }}
"""
MERMAID = ('<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>'
           '<script>window.__done=false;try{mermaid.initialize({startOnLoad:false,theme:"neutral"});'
           'mermaid.run({querySelector:".mermaid"}).finally(()=>{window.__done=true;});}catch(err){window.__done=true;}</script>')
doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Sprint 11</title><style>{CSS}</style></head>'
       f'<body>{"".join(parts)}{MERMAID}</body></html>')
html_path = Path(os.environ.get("TEMP", ".")) / "pluseduc_sprint11.html"
html_path.write_text(doc, encoding="utf-8")

opts = Options()
opts.add_argument("--headless=new")
driver = webdriver.Chrome(options=opts)
try:
    driver.get(html_path.as_uri())
    for _ in range(40):  # até 20 s para os diagramas
        if driver.execute_script("return window.__done === true || typeof mermaid === 'undefined'"):
            break
        time.sleep(0.5)
    desenhados = driver.execute_script("return document.querySelectorAll('.mermaid svg').length")
    header = f'<div style="width:100%;margin:0 16mm;background:{NAVY};color:#fff;font:bold 7pt Arial;padding:5px 8px;-webkit-print-color-adjust:exact">PLUS EDUC &nbsp;|&nbsp; FÁBRICA DE SOFTWARE</div>'
    footer = ('<div style="width:100%;margin:0 16mm;border-top:1px solid #ccc;font:7pt Arial;color:#666;padding-top:4px;display:flex;justify-content:space-between">'
              f'<span>Grupo 08 • Sprint 11 • {ENTREGA}</span><span class="pageNumber"></span></div>')
    pdf = driver.execute_cdp_cmd("Page.printToPDF", {
        "printBackground": True, "preferCSSPageSize": True, "displayHeaderFooter": True,
        "headerTemplate": header, "footerTemplate": footer,
    })
finally:
    driver.quit()
secao = Path(os.environ.get("TEMP", ".")) / "pluseduc_sprint11_secao.pdf"
secao.write_bytes(base64.b64decode(pdf["data"]))

# marcadores: a Sprint 11 e cada parte dela, achados pelo título na página
leitor = PdfReader(str(secao))
paginas = [page.extract_text() or "" for page in leitor.pages]
titulos = ["1. Manual do Usuário", "2. Manual Técnico", "3. Documentação final consolidada", "4. Revisão do código",
           "5. Principais correções e melhorias", "6. Repositório GitHub", "7. Pendências e próximos passos"]
writer = PdfWriter()
writer.append(SRC_PDF)
inicio = len(writer.pages)
writer.append(str(secao))
raiz = writer.add_outline_item("Sprint 11 — Preparação para entrega", inicio)
procurar_a_partir = 2
for titulo in titulos:
    pagina = next((i for i in range(procurar_a_partir, len(paginas)) if paginas[i].lstrip().startswith(titulo)), None)
    if pagina is not None:
        writer.add_outline_item(titulo, inicio + pagina, parent=raiz)
        procurar_a_partir = pagina + 1
writer.add_metadata({"/Title": "Grupo 08 — PlusEduc — Sprints 01 a 11",
                     "/Author": "Grupo 08 — PlusEduc (Fábrica de Software + Tópicos Avançados, UNINASSAU)"})
with open(OUT_PDF, "wb") as fh:
    writer.write(fh)
print(f"diagramas desenhados: {desenhados}; seção da Sprint 11: {len(leitor.pages)} páginas; "
      f"consolidado: {len(writer.pages)} páginas -> {OUT_PDF}")
