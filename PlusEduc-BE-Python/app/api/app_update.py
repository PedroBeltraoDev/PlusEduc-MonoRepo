from fastapi import APIRouter, Header, HTTPException, Request, status

from app.schemas.app_update import AppVersionResponse, UpdateStatusResponse
from app.services.update_service import UpdateError, UpdateManager

router = APIRouter(prefix="/api/app", tags=["Application"])

# Cabeçalho exigido por quem dispara a instalação: obriga o navegador a fazer uma checagem CORS prévia, então um site
# qualquer aberto no mesmo computador não consegue acionar o instalador no endereço local.
UPDATE_HEADER = "x-pluseduc-update"


def manager(request: Request) -> UpdateManager:
    return request.app.state.update_manager


@router.get("/version", response_model=AppVersionResponse, summary="Versão instalada do aplicativo")
def app_version(request: Request) -> AppVersionResponse:
    return AppVersionResponse(version=manager(request).current_version)


@router.get("/update", response_model=UpdateStatusResponse, summary="Estado da verificação de atualização")
def update_status(request: Request) -> UpdateStatusResponse:
    return UpdateStatusResponse(**manager(request).snapshot())


@router.post("/update/check", response_model=UpdateStatusResponse, summary="Verificar agora se há versão nova")
def check_update(request: Request) -> UpdateStatusResponse:
    update_manager = manager(request)
    update_manager.check_if_allowed()
    return UpdateStatusResponse(**update_manager.snapshot())


@router.post(
    "/update/install",
    response_model=UpdateStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Baixar o instalador da nova versão e executá-lo",
)
def install_update(request: Request, x_pluseduc_update: str | None = Header(default=None)) -> UpdateStatusResponse:
    if x_pluseduc_update != "1":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cabeçalho {UPDATE_HEADER}: 1 obrigatório")
    update_manager = manager(request)
    try:
        update_manager.request_install()
    except UpdateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, exc.message) from exc
    return UpdateStatusResponse(**update_manager.snapshot())
