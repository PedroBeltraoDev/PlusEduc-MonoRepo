from fastapi import APIRouter, Depends, Request, Response, status

from app.core.auth import UserPrincipal
from app.dependencies import require_roles
from app.schemas.subject_topic import (
    SubjectTopicCreateRequest,
    SubjectTopicResponse,
    SubjectTopicUpdateRequest,
)
from app.services.subject_topic_service import SubjectTopicService

router = APIRouter(prefix="/api/subject-topics", tags=["Subject Topics"])


def service(request: Request) -> SubjectTopicService:
    return SubjectTopicService(
        request.app.state.subject_topic_repository,
        request.app.state.subject_repository,
    )


teacher_user = require_roles("TEACHER", "ADMIN")


@router.get("", response_model=list[SubjectTopicResponse])
def list_subject_topics(
    request: Request,
    current_user: UserPrincipal = Depends(teacher_user),
):
    return service(request).list(current_user)


@router.post("", response_model=SubjectTopicResponse, status_code=status.HTTP_201_CREATED)
def create_subject_topic(
    payload: SubjectTopicCreateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(teacher_user),
):
    return service(request).create(payload, current_user)


@router.put("/{item_id}", response_model=SubjectTopicResponse)
def update_subject_topic(
    item_id: str,
    payload: SubjectTopicUpdateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(teacher_user),
):
    return service(request).update(item_id, payload, current_user)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject_topic(
    item_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(teacher_user),
):
    service(request).delete(item_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
