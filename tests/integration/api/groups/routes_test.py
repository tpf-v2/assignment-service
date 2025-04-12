import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.api.groups.dependencies import get_email_sender
from src.api.groups.router import router
from src.config.database.database import create_tables, drop_tables, engine
from sqlalchemy.orm import sessionmaker, scoped_session

from tests.integration.api.helper import ApiHelper

PREFIX = "/groups"


class MockSendGrid:

    def notify_attachement(self, group, type):
        return 200


async def override_get_email_sender():
    yield MockSendGrid()


@pytest.fixture(scope="function")
def tables():
    # Create all tables
    create_tables()
    yield
    # Drop all tables
    drop_tables()


SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)


@pytest.fixture(scope="module")
def fastapi():
    app = FastAPI()

    app.include_router(router)
    client = TestClient(app)
    yield client


@pytest.mark.integration
def test_add_assigned_group_and_get_one_group(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")

    user_token = helper.create_student_token()

    body = {
        "students_ids": [105001, 105002, 105003],
        "tutor_email": "perez@gmail.com",
        "topic": "My custom topic",
    }
    params = {"period": "1C2025"}
    response = fastapi.post(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
def test_get_groups_by_period(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    user_token = helper.create_student_token()
    admin_token = helper.create_admin_token()

    body = {
        "students_ids": [105001, 105002, 105003],
        "tutor_email": "perez@gmail.com",
        "topic": "My custom topic",
    }
    params = {"period": "1C2025"}
    response = fastapi.post(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Act
    params = {"period": "1C2025"}
    response = fastapi.get(
        f"{PREFIX}/",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1


@pytest.mark.integration
def test_post_groups_with_tutor_not_in_db_returns_not_found(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    user_token = helper.create_student_token()

    body = {
        "students_ids": [105001, 105002, 105003],
        "tutor_email": "perez@gmail.com",
        "topic": "My custom topic",
    }
    params = {"period": "1C2025"}
    response = fastapi.post(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        response.json()["detail"]
        == "The tutor does not exist or this period is not present"
    )


@pytest.mark.integration
def test_post_groups_with_one_student_not_in_db_returns_not_found(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    user_token = helper.create_student_token()

    body = {
        "students_ids": [105001, 105002, 105003],
        "tutor_email": "perez@gmail.com",
        "topic": "My custom topic",
    }
    params = {"period": "1C2025"}
    response = fastapi.post(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Some ids are not in database"


@pytest.mark.integration
def test_post_groups_without_token(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")

    body = {
        "students_ids": [105001, 105002, 105003],
        "tutor_email": "perez@gmail.com",
        "topic": "My custom topic",
    }
    params = {"period": "1C2025"}
    response = fastapi.post(f"{PREFIX}/", json=body, params=params)

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
def test_put_confirmed_groups(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    helper.create_topic("Basic topic")
    group = helper.create_basic_group([105001, 105002, 105003], [1, 2, 3], "1C2025")
    admin_token = helper.create_admin_token()

    body = [{"id": group.id, "tutor_period_id": 1, "assigned_topic_id": 1}]
    params = {"period": "1C2025"}
    response = fastapi.put(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    groups = response.json()
    assert len(groups) == 1
    first = groups[0]
    assert first["id"] == 1
    assert first["topic"]["id"] == 1
    assert first["tutor_period_id"] == 1


@pytest.mark.integration
def test_put_confirmed_groups_tutor_period_id_not_exist(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    helper.create_topic("Basic topic")
    group = helper.create_basic_group([105001, 105002, 105003], [1, 2, 3], "1C2025")
    admin_token = helper.create_admin_token()

    body = [
        {
            "id": group.id,
            "tutor_period_id": 10,
            "assigned_topic_id": 1,
            "reviewer_id": 1,
        }
    ]
    params = {"period": "1C2025"}
    response = fastapi.put(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
def test_put_confirmed_groups_topic_id_not_exist(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    helper.create_topic("Basic topic")
    group = helper.create_basic_group([105001, 105002, 105003], [1, 2, 3], "1C2025")
    admin_token = helper.create_admin_token()

    body = [{"id": group.id, "tutor_period_id": 1, "assigned_topic_id": 3}]
    params = {"period": "1C2025"}
    response = fastapi.put(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
def test_put_approve_pre_report(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    helper.create_topic("Basic topic")
    group = helper.create_basic_group([105001, 105002, 105003], [1, 2, 3], "1C2025")
    admin_token = helper.create_admin_token()

    body = [{"id": group.id, "pre_report_approved": True}]
    params = {"period": "1C2025"}
    response = fastapi.put(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    # Assert
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
def test_put_approve_intermediate_assigment(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    helper.create_topic("Basic topic")
    group = helper.create_basic_group([105001, 105002, 105003], [1, 2, 3], "1C2025")
    admin_token = helper.create_admin_token()

    body = [{"id": group.id, "intermediate_assigment_approved": True}]
    params = {"period": "1C2025"}
    response = fastapi.put(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    # Assert
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
def test_put_approve_final_report_assigment(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    helper.create_topic("Basic topic")
    group = helper.create_basic_group([105001, 105002, 105003], [1, 2, 3], "1C2025")
    admin_token = helper.create_admin_token()

    body = [{"id": group.id, "final_report_approved": True}]
    params = {"period": "1C2025"}
    response = fastapi.put(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    # Assert
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
def test_add_reviewer(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    helper.create_topic("Basic topic")
    group = helper.create_basic_group([105001, 105002, 105003], [1, 2, 3], "1C2025")
    admin_token = helper.create_admin_token()

    body = [{"id": group.id, "reviewer_id": 1}]
    params = {"period": "1C2025"}
    response = fastapi.put(
        f"{PREFIX}/",
        json=body,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
@pytest.mark.azure
def test_post_groups_initial_project(fastapi, tables):
    # Arrange
    fastapi.app.dependency_overrides[get_email_sender] = override_get_email_sender
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Celeste", "Perez", "105000", "cdituro@fi.uba.ar")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Victoria", "A", "105001", "vlopez@fi.uba.ar")
    helper.create_student("Ivan", "B", "105002", "ipfaab@fi.uba.ar")
    helper.create_student("Joaquin", "C", "105003", "joagomez@fi.uba.ar")
    topic = helper.create_topic("TopicCustom")
    group = helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    user_token = helper.create_student_token()

    with open("tests/test.pdf", "rb") as file:
        content = file.read()

    filename = "test"
    content_type = "application/pdf"
    files = {"file": (filename, content, content_type)}
    params = {"project_title": "My title"}
    response = fastapi.post(
        f"{PREFIX}/{group.id}/initial-project",
        files=files,
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.azure
def test_download_group_initial_project(fastapi):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/1/initial-project",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    with open("tests/test.pdf", "rb") as file:
        expected_file = file.read()
    assert expected_file == response.content


@pytest.mark.integration
@pytest.mark.azure
def test_all_groups_initial_project_details(fastapi):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/initial-project",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    blob = response.json()[0]
    blob["name"] = "1C2025/1/initial-project.pdf"
    blob["container"] = "dev"


@pytest.mark.integration
def test_get_groups_by_id(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    group = helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    user_token = helper.create_student_token(105001)
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/states/{group.id}",
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
def test_get_groups_by_id_fails_if_user_doesnt_belong_to_group(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    user_token = helper.create_student_token(105001)
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/states/{10}",
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
def test_get_groups_by_id_being_admin(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    group = helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    admin_token = helper.create_admin_token()
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/states/{group.id}",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
def test_get_groups_by_id_being_tutor(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    group = helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    tutor_token = helper.create_tutor_token(105000)
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/states/{group.id}",
        params=params,
        headers={"Authorization": f"Bearer {tutor_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.azure
def test_post_groups_final_project(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    group = helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    user_token = helper.create_student_token()

    with open("tests/test.pdf", "rb") as file:
        content = file.read()

    filename = "test"
    content_type = "application/pdf"
    files = {"file": (filename, content, content_type)}
    params = {"project_title": "Proyecto Final"}
    response = fastapi.post(
        f"{PREFIX}/{group.id}/final-project",
        files=files,
        params=params,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.azure
def test_download_group_final_project(fastapi):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/1/final-project",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK

    with open("tests/test.pdf", "rb") as file:
        expected_file = file.read()
    assert expected_file == response.content


@pytest.mark.integration
@pytest.mark.azure
def test_all_groups_final_project_details(fastapi):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    params = {"period": "1C2025"}

    response = fastapi.get(
        f"{PREFIX}/final-project",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    blob = response.json()[0]
    blob["name"] = "1C2025/1/informe-final.pdf"
    blob["container"] = "dev"


@pytest.mark.integration
@pytest.mark.azure
def test_post_groups_intermediate_project(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    group = helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    user_token = helper.create_student_token(105001)
    youtube_link = "https://www.youtube.com/watch?v=IGjE_zgs2Hw"

    body = {"url": youtube_link}

    response = fastapi.post(
        f"{PREFIX}/{group.id}/intermediate-report",
        json=body,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.integration
@pytest.mark.azure
def test_get_groups_intermediate_project(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    group = helper.create_group(
        ids=[105001, 105002, 105003],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    user_token = helper.create_student_token(105001)
    youtube_link = "https://www.youtube.com/watch?v=IGjE_zgs2Hw"

    body = {"url": youtube_link}

    response = fastapi.post(
        f"{PREFIX}/{group.id}/intermediate-report",
        json=body,
        headers={"Authorization": f"Bearer {user_token.access_token}"},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED

    tutor_token = helper.create_tutor_token(105000)
    response = fastapi.get(
        f"{PREFIX}/{group.id}/intermediate-report",
        headers={"Authorization": f"Bearer {tutor_token.access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["intermediate_assigment"] == youtube_link


@pytest.mark.integration
@pytest.mark.azure
def test_get_all_intermediate_project(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2025")
    helper.create_tutor("Juan", "Perez", "105000", "perez@gmail.com")
    period = helper.create_tutor_period("105000", "1C2025")
    helper.create_student("Pedro", "A", "105001", "a@gmail.com")
    helper.create_student("Alejo", "B", "105002", "b@gmail.com")
    helper.create_student("Tomas", "C", "105003", "c@gmail.com")
    topic = helper.create_topic("TopicCustom")
    topic2 = helper.create_topic("TopicCustom2")

    group1 = helper.create_group(
        ids=[105001, 105002],
        tutor_period_id=period.id,
        topic_id=topic.id,
        period_id="1C2025",
    )
    group2 = helper.create_group(
        ids=[105003],
        tutor_period_id=period.id,
        topic_id=topic2.id,
        period_id="1C2025",
    )
    user_g1_token = helper.create_student_token(105001)
    user_g2_token = helper.create_student_token(105003)

    youtube_link = "https://www.youtube.com/watch?v=IGjE_zgs2Hw"
    youtube_link2 = "https://www.youtube.com/watch?v=PN1qAgbCmdE"

    body = {"url": youtube_link}
    response = fastapi.post(
        f"{PREFIX}/{group1.id}/intermediate-report",
        json=body,
        headers={"Authorization": f"Bearer {user_g1_token.access_token}"},
    )

    body = {"url": youtube_link2}
    response = fastapi.post(
        f"{PREFIX}/{group2.id}/intermediate-report",
        json=body,
        headers={"Authorization": f"Bearer {user_g2_token.access_token}"},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED

    tutor_token = helper.create_tutor_token(105000)
    params = {"period": "1C2025"}
    response = fastapi.get(
        f"{PREFIX}/intermediate-report",
        params=params,
        headers={"Authorization": f"Bearer {tutor_token.access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["intermediate_assigment"] == youtube_link
    assert data[1]["intermediate_assigment"] == youtube_link2
