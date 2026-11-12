"""Rotas exclusivas do administrador: aprovação dos cadastros públicos de professor."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.access import require_admin
from app.core.audit_middleware import set_audit
from app.core.auth import UserPrincipal
from app.schemas.teacher import TeacherRequestResponse

router = APIRouter(prefix="/api/admin", tags=["Administração"])


def _pending_user(request: Request, user_id: str) -> dict:
    user = request.app.state.user_repository.find_by_id(user_id)
    if not user or user.get("role") != "TEACHER" or user.get("approvalStatus") != "PENDING":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido de cadastro não encontrado")
    return user


@router.get("/teacher-requests", response_model=list[TeacherRequestResponse])
def list_teacher_requests(request: Request, current_user: UserPrincipal = Depends(require_admin)):
    return [
        TeacherRequestResponse(
            userId=str(user["_id"]),
            name=user.get("name"),
            email=str(user.get("email", "")),
            status=str(user.get("approvalStatus")),
            createdAt=user.get("createdAt"),
        )
        for user in request.app.state.user_repository.find_pending_teachers()
    ]


@router.post("/teacher-requests/{user_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
def approve_teacher_request(user_id: str, request: Request, current_user: UserPrincipal = Depends(require_admin)):
    user = _pending_user(request, user_id)
    email = str(user["email"])
    now = datetime.now(timezone.utc)
    request.app.state.user_repository.update_fields(
        email, {"active": True, "approvalStatus": "APPROVED", "approvedBy": current_user.email, "approvedAt": now}
    )
    request.app.state.teacher_repository.set_status_by_email(
        email, {"active": True, "approvalStatus": "APPROVED", "updated_at": now, "updated_by": current_user.email}
    )
    set_audit(request, entityId=user_id, summary=f"Cadastro de professor aprovado: {email}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/teacher-requests/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_teacher_request(user_id: str, request: Request, current_user: UserPrincipal = Depends(require_admin)):
    user = _pending_user(request, user_id)
    email = str(user["email"])
    now = datetime.now(timezone.utc)
    request.app.state.user_repository.update_fields(
        email, {"active": False, "approvalStatus": "REJECTED", "rejectedBy": current_user.email, "rejectedAt": now}
    )
    request.app.state.teacher_repository.set_status_by_email(
        email, {"active": False, "approvalStatus": "REJECTED", "updated_at": now, "updated_by": current_user.email}
    )
    set_audit(request, entityId=user_id, summary=f"Cadastro de professor recusado: {email}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
