import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.api.tutors.router import router as tutor_router
from src.api.periods.router import router as period_router

from src.config.database.database import create_tables, drop_tables

from tests.integration.api.helper import ApiHelper

PREFIX = "/tutors"


@pytest.fixture(scope="function")
def tables():
    # Create all tables
    create_tables()
    yield
    # Drop all tables
    drop_tables()


@pytest.fixture(scope="session")
def fastapi():
    app = FastAPI()
    app.include_router(tutor_router)
    app.include_router(period_router)
    client = TestClient(app)
    yield client


@pytest.mark.integration
def test_upload_file_and_create_tutors(fastapi, tables):
    helper = ApiHelper()
    helper.create_period("1C2024")
    admin_token = helper.create_admin_token()

    with open("tests/integration/api/tutors/data/test_data.csv", "rb") as file:
        content = file.read()

    filename = "test_data"
    content_type = "text/csv"
    files = {"file": (filename, content, content_type)}
    params = {"period": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/upload",
        params=params,
        files=files,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.json()) == 15


@pytest.mark.integration
def test_upload_file_with_invalid_columns_raise_exception(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    with open("tests/integration/api/tutors/data/wrong_data.csv", "rb") as file:
        content = file.read()

    filename = "wrong_data"
    content_type = "text/csv"
    files = {"file": (filename, content, content_type)}
    params = {"period": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/upload",
        files=files,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    http_exception = response.json()

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert http_exception.get("detail") == "Columns don't match with expected ones"


@pytest.mark.integration
def test_upload_file_with_duplicates_rows_in_csv_raise_exception(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    with open("tests/integration/api/tutors/data/duplicate_data.csv", "rb") as file:
        content = file.read()

    filename = "duplicate_data"
    content_type = "text/csv"
    files = {"file": (filename, content, content_type)}
    params = {"period": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/upload",
        files=files,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    http_exception = response.json()

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    assert http_exception.get("detail") == "Duplicate values inside the csv file"


@pytest.mark.integration
def test_upload_file_raise_exception_if_type_is_not_csv(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    filename = "test_data"
    content_type = "application/json"
    files = {"file": (filename, "test".encode(), content_type)}
    params = {"period": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/upload",
        files=files,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


@pytest.mark.integration
def test_upload_file_with_existing_tutors(fastapi, tables):
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("Juan", "Perez", "12345678", "juan.perez@fi.uba.ar")
    helper.create_tutor("Paula", "Diaz", "33456789", "paula.diaz@fi.uba.ar")
    admin_token = helper.create_admin_token()

    with open("tests/integration/api/tutors/data/test_data.csv", "rb") as file:
        content = file.read()

    filename = "test_data"
    content_type = "text/csv"
    files = {"file": (filename, content, content_type)}
    params = {"period": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/upload",
        params=params,
        files=files,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.json()) == 15


@pytest.mark.integration
def test_add_new_tutor_period_with_success(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("Juan", "Perez", "10600", "email@fi.uba.ar")
    admin_token = helper.create_admin_token()
    params = {"period_id": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/{10600}/periods",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
def test_if_id_is_not_tutor_raises_a_404(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_student("Juan", "Perez", "105600", "email@fi.uba.ar")
    admin_token = helper.create_admin_token()
    params = {"period_id": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/{105600}/periods",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
def test_add_same_period_to_two_tutors_with_success(fastapi, tables):

    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("Juan", "Perez", "105600", "email@fi.uba.ar")
    helper.create_tutor("Juan", "Perez", "105601", "email2@fi.uba.ar")
    admin_token = helper.create_admin_token()
    params = {"period_id": "1C2024"}

    # Act
    response1 = fastapi.post(
        f"{PREFIX}/{105600}/periods",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    response2 = fastapi.post(
        f"{PREFIX}/{105601}/periods",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response1.status_code == status.HTTP_201_CREATED
    assert response2.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
def test_get_tutors_period_with_admin_success(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("Juan", "Perez", "105600", "email@fi.uba.ar")
    helper.create_tutor_period("105600", "1C2024")
    admin_token = helper.create_admin_token()

    # Act
    response = fastapi.get(
        f"{PREFIX}/{105600}/periods",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    # Assert
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
def test_raise_404_if_tutor_not_exists(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    admin_token = helper.create_admin_token()
    tutor_id = 10600

    # Act
    response = fastapi.get(
        f"{PREFIX}/{tutor_id}/periods",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
def test_add_same_period_to_same_tutor_raise_error(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("Juan", "Perez", "105600", "email@fi.uba.ar")
    helper.create_tutor_period("105600", "1C2024")
    admin_token = helper.create_admin_token()
    params = {"period_id": "1C2024"}

    # Act
    response = fastapi.post(
        f"{PREFIX}/{105600}/periods",
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.integration
def test_new_upload_override_tutor_periods(fastapi, tables):
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("Juan", "Perez", "12345678", "juan.perez@fi.uba.ar")
    helper.create_tutor_period("12345678", "1C2024", 5)
    admin_token = helper.create_admin_token()

    tutor = helper.get_tutor_by_tutor_id(12345678)
    assert tutor.tutor_periods[0].capacity == 5

    with open("tests/integration/api/tutors/data/test_data.csv", "rb") as file:
        content = file.read()

    filename = "test_data"
    content_type = "text/csv"
    files = {"file": (filename, content, content_type)}
    params = {"period": "1C2024"}

    response = fastapi.post(
        f"{PREFIX}/upload",
        files=files,
        params=params,
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    response = fastapi.get(
        f"{PREFIX}/{12345678}/periods",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["tutor_periods"][0]["capacity"] == 1


@pytest.mark.integration
def test_delete_tutor_no_affects_global_periods(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    periods = ["1C2024", "2C2024", "1C2025"]
    helper.create_tutor("Juan", "Perez", "105600", "email@fi.uba.ar")
    admin_token = helper.create_admin_token()

    for p in periods:
        helper.create_period(p)
        helper.create_tutor_period("105600", p)

    tutor = helper.get_tutor_by_tutor_id(105600)
    assert len(tutor.tutor_periods) == 3

    # Act
    response = fastapi.delete(
        f"{PREFIX}/{105600}",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED

    response = fastapi.get(
        "periods",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3


@pytest.mark.integration
def test_delete_tutor_by_id_deletes_its_related_periods_also(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    periods = ["1C2024", "2C2024", "1C2025"]
    helper.create_tutor("Juan", "Perez", "105600", "email@fi.uba.ar")
    admin_token = helper.create_admin_token()

    for p in periods:
        helper.create_period(p)
        helper.create_tutor_period("105600", p)

    tutor = helper.get_tutor_by_tutor_id(105600)
    assert len(tutor.tutor_periods) == 3

    # Act
    response = fastapi.delete(
        f"{PREFIX}/{105600}",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )

    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED

    response = fastapi.get(
        f"{PREFIX}/{105600}/periods",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
def test_all_topics_from_tutors_in_specific_period(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_period("2C2024")
    helper.create_tutor("Juan", "Perez", "105600", "email@fi.uba.ar")
    helper.create_tutor_period("105600", "1C2024")
    helper.create_tutor_period("105600", "2C2024")
    admin_token = helper.create_admin_token()

    response = fastapi.get(
        f"{PREFIX}/periods/1C2024",
        headers={"Authorization": f"Bearer {admin_token.access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data[0]["tutor_periods"]) == 1


@pytest.mark.integration
def test_create_tutor(fastapi, tables):
    helper = ApiHelper()
    token = helper.create_admin_token()
    helper.create_period("1C2024")

    tutor = {
        "id": 110000,
        "name": "Juan",
        "last_name": "Perez",
        "email": "juanperez123@fi.uba.ar",
        "period": "1C2024",
        "capacity": 4,
    }

    response = fastapi.post(
        f"{PREFIX}",
        json=tutor,
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert response.status_code == 201
    assert response.json()["id"] == 110000
    assert response.json()["name"] == "Juan"
    assert response.json()["last_name"] == "Perez"
    assert response.json()["email"] == "juanperez123@fi.uba.ar"


@pytest.mark.integration
def test_create_duplicated_tutor(fastapi, tables):
    helper = ApiHelper()
    token = helper.create_admin_token()
    helper.create_period("1C2024")

    tutor = {
        "id": 110001,
        "name": "Jose",
        "last_name": "Perez",
        "email": "joseperez@fi.uba.ar",
        "period": "1C2024",
        "capacity": 4,
    }

    response = fastapi.post(
        f"{PREFIX}",
        json=tutor,
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert response.status_code == 201
    assert response.json()["id"] == 110001
    assert response.json()["name"] == "Jose"
    assert response.json()["last_name"] == "Perez"
    assert response.json()["email"] == "joseperez@fi.uba.ar"

    response = fastapi.post(
        f"{PREFIX}",
        json=tutor,
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Duplicated tutor"


@pytest.mark.integration
def test_create_tutor_with_invalid_token(fastapi, tables):
    helper = ApiHelper()
    token = helper.create_student_token()
    helper.create_period("1C2024")

    tutor = {
        "id": 110002,
        "name": "Josefa",
        "last_name": "Perez",
        "email": "josefaperez@fi.uba.ar",
        "period": "1C2024",
        "capacity": 4,
    }

    response = fastapi.post(
        f"{PREFIX}",
        json=tutor,
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Authorization"


@pytest.mark.integration
def test_get_groups_assigned_to_tutor(fastapi, tables):
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("pepe", "tutor", "12345678", "pepe@fi.uba.ar")
    period = helper.create_tutor_period(12345678, "1C2024")
    helper.create_default_topics(["topic1", "topic2"])
    helper.add_tutor_to_topic("1C2024", "pepe@fi.uba.ar", ["topic1", "topic2"], [1, 1])
    helper.create_student("john", "Student", "105285", "student@fi.uba.ar")
    helper.create_student("juan", "Student2", "105286", "student2@fi.uba.ar")
    helper.create_group([105285], period.id, 1, "1C2024")
    helper.create_group([105286], period.id, 2, "1C2024")
    token = helper.create_tutor_token_with_id(12345678)

    params = {"period_id": "1C2024"}
    response = fastapi.get(
        f"{PREFIX}/my-groups",
        params=params,
        headers={"Authorization": f"Bearer {token.access_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.integration
def test_get_tutors_periods_with_tutor_success(fastapi, tables):
    # Arrange
    helper = ApiHelper()
    helper.create_period("1C2024")
    helper.create_tutor("Juan", "Perez", "105600", "email@fi.uba.ar")
    helper.create_tutor_period("105600", "1C2024")
    student_token = helper.create_tutor_token_with_id("105600")

    # Act
    response = fastapi.get(
        f"{PREFIX}/{105600}/periods",
        headers={"Authorization": f"Bearer {student_token.access_token}"},
    )
    # Assert
    assert response.status_code == status.HTTP_200_OK
