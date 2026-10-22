from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """Serve a interface React compilada: rotas do cliente (ex.: /turmas) devolvem o index.html.

    Caminhos de ``/api`` que não existem continuam respondendo 404 em vez de cair na interface.
    """

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            # No Windows o Starlette entrega o caminho com "\\" em vez de "/".
            normalized = path.replace("\\", "/")
            is_file = "." in normalized.rsplit("/", 1)[-1]  # /assets/x.js ausente deve ser 404, não a interface
            if exc.status_code != 404 or normalized.startswith("api/") or is_file:
                raise
            return await super().get_response("index.html", scope)
