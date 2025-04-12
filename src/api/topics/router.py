from typing import Optional
from fastapi import APIRouter, Response, status, Depends, UploadFile, Query
from sqlalchemy.orm import Session
from typing_extensions import Annotated

from src.api.auth.dependencies import authorization
from src.api.auth.jwt import InvalidJwt
from src.api.auth.service import AuthenticationService
from src.api.exceptions import EntityNotFound, InvalidCsv, InvalidFileType, ServerError
from src.api.topics.repository import TopicRepository
from src.api.topics.schemas import (
    CompleteCategoryResponse,
    SimpleCategory,
    TopicList,
    TopicRequest,
    TopicResponse,
)
from src.api.topics.service import TopicService
from src.api.tutors.repository import TutorRepository
from src.api.users.exceptions import InvalidCredentials
from src.api.utils.response_builder import ResponseBuilder
from src.config.database.database import get_db


router = APIRouter(prefix="/topics", tags=["Topics"])


@router.post(
    "/upload",
    response_model=TopicList,
    summary="Creates a list of topics based on a csv file.",
    responses={
        status.HTTP_201_CREATED: {"description": "Successfully added topics."},
        status.HTTP_400_BAD_REQUEST: {
            "description": "Columns don't match with expected."
        },
        status.HTTP_409_CONFLICT: {"description": "Topic already exists."},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"description": "Invalid file type."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation Error."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error."
        },
    },
    status_code=status.HTTP_201_CREATED,
)
async def upload_csv_file(
    file: UploadFile,
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[dict, Depends(authorization)],
    period: str = Query(pattern="^[1|2]C20[0-9]{2}$", examples=["1C2024"]),
):
    """Endpoint obtener subir los temas a partir de un archivo csv"""
    try:
        auth_service = AuthenticationService(authorization["jwt_resolver"])
        auth_service.assert_only_admin(authorization["token"])
        if file.content_type != "text/csv":
            raise InvalidFileType("CSV file must be provided.")
        content = (await file.read()).decode("utf-8")
        service = TopicService(TopicRepository(session))

        res = service.create_topics_from_string(
            period, content, TutorRepository(session)
        )

        return ResponseBuilder.build_clear_cache_response(res, status.HTTP_201_CREATED)
    except (
        EntityNotFound,
        InvalidFileType,
        InvalidCsv,
    ) as e:
        raise e
    except InvalidJwt:
        raise InvalidCredentials("Invalid Authorization")
    except Exception as e:
        raise ServerError(str(e))


@router.get(
    "/",
    response_model=TopicList,
    summary="Get a list of topics.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Successfully."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error."
        },
    },
)
async def get_topics(
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[dict, Depends(authorization)],
    period: Optional[str] = Query(
        None, pattern="^[1|2]C20[0-9]{2}$", examples=["1C2024"]
    ),
):
    """Endpoint obtener todos los temas"""
    try:
        auth_service = AuthenticationService(authorization["jwt_resolver"])
        auth_service.assert_student_role(authorization["token"])

        service = TopicService(TopicRepository(session))
        if period:
            topics = service.get_topics_by_period(period)
            topics = TopicList.model_validate(topics)
        else:
            topics = service.get_topics()

        return ResponseBuilder.build_private_cache_response(topics)
    except InvalidJwt:
        raise InvalidCredentials("Invalid Authorization")
    except Exception as e:
        raise ServerError(str(e))


@router.post(
    "/category",
    response_model=CompleteCategoryResponse,
    summary="Add a new category",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Successfully."},
        status.HTTP_409_CONFLICT: {"description": "Category duplicated"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error."
        },
    },
)
async def add_category(
    category: SimpleCategory,
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[dict, Depends(authorization)],
):
    """Endpoint para agregar una categoria manualmente"""
    try:
        auth_service = AuthenticationService(authorization["jwt_resolver"])
        auth_service.assert_only_admin(authorization["token"])

        service = TopicService(TopicRepository(session))
        category_saved = service.add_category(category.name)

        return CompleteCategoryResponse.model_validate(category_saved)
    except InvalidJwt:
        raise InvalidCredentials("Invalid Authorization")
    except Exception as e:
        raise ServerError(str(e))


@router.post(
    "/",
    response_model=TopicResponse,
    summary="Add a new topic",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Successfully."},
        status.HTTP_409_CONFLICT: {"description": "Category duplicated"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error."
        },
    },
)
async def add_topic(
    topic: TopicRequest,
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[dict, Depends(authorization)],
    period: str = Query(None, pattern="^[1|2]C20[0-9]{2}$", examples=["1C2024"]),
):
    """Endpoint para agregar un tema manualmente"""
    try:
        auth_service = AuthenticationService(authorization["jwt_resolver"])
        auth_service.assert_only_admin(authorization["token"])

        service = TopicService(TopicRepository(session))
        topic_saved = service.add_topic(period, topic, TutorRepository(session))

        return TopicResponse.model_validate(topic_saved)
    except InvalidJwt:
        raise InvalidCredentials("Invalid Authorization")
    except Exception as e:
        raise ServerError(str(e))


@router.delete(
    "/{topic_id}",
    summary="Deletes topic by id",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_202_ACCEPTED: {"description": "Successfully."},
        status.HTTP_404_NOT_FOUND: {"description": "Topic not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error."
        },
    },
)
async def add_topic(
    topic_id: int,
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[dict, Depends(authorization)],
):
    """Endpoint para borrar un tema manualmente"""
    try:
        auth_service = AuthenticationService(authorization["jwt_resolver"])
        auth_service.assert_only_admin(authorization["token"])

        service = TopicService(TopicRepository(session))
        service.delete_topic(topic_id)

        return Response(status_code=status.HTTP_202_ACCEPTED)
    except InvalidJwt:
        raise InvalidCredentials("Invalid Authorization")
    except EntityNotFound as e:
        raise e
    except Exception as e:
        raise ServerError(str(e))
