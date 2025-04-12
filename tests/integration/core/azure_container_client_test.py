import pytest
from src.config.config import api_config
from src.core.azure_container_client import AzureContainerClient


class TestAzureContainerClient:
    @pytest.mark.integration
    @pytest.mark.azure
    def test_azure_container_client_exists(self):
        # Arrange
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )  # Act & Assert
        assert az_client.exists() is True

    @pytest.mark.integration
    @pytest.mark.azure
    def test_upload_test_file_to_azure(self):  # Arrange
        filename = "upload.txt"
        file_path = "tests/integration/core/upload.txt"
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )
        with open(file_path, "rb") as file:
            content = file.read()
        # Act
        blob = az_client.upload(content, filename, True)  # Assert
        assert blob.blob_name == filename

    @pytest.mark.integration
    @pytest.mark.azure
    def test_download_test_file_to_azure(self):  # Arrange
        filename = "test_data.txt"  # test_data is already in the storage
        expected_content = (
            "This is a txt file just for uploading and downloading for azure storage"
        )
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )
        bytes = az_client.download(filename)
        file_content = bytes.decode("utf-8")

        assert (
            file_content == expected_content
        ), f"Content does not match. Expected: '{expected_content}', \
            Found: '{file_content}'"

    @pytest.mark.integration
    def test_try_to_download_file_not_exists(self):
        # Arrange
        filename = "not_exists.txt"

        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )

        # Act & Assert
        with pytest.raises(Exception):
            az_client.download(filename)

    @pytest.mark.integration
    @pytest.mark.azure
    def test_list_blob_with_prefix_existence(self):
        # Arrange
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )  # Act & Assert
        assert az_client.exists() is True

    @pytest.mark.integration
    @pytest.mark.azure
    def test_upload_existing_test_file_to_azure(self):  # Arrange
        filename = "upload.txt"
        file_path = "tests/integration/core/upload.txt"
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )
        with open(file_path, "rb") as file:
            content = file.read()
        # Act
        blob = az_client.upload(content, filename, True)  # Assert
        assert blob.blob_name == filename

    @pytest.mark.integration
    @pytest.mark.azure
    def test_download_existing_test_file_to_azure(self):  # Arrange
        filename = "test_data.txt"  # test_data is already in the storage
        expected_content = (
            "This is a txt file just for uploading and downloading for azure storage"
        )
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )
        bytes = az_client.download(filename)
        file_content = bytes.decode("utf-8")

        assert (
            file_content == expected_content
        ), f"Content does not match. Expected: '{expected_content}', \
            Found: '{file_content}'"

    @pytest.mark.integration
    def test_try_downloading_not_existing_file(self):
        # Arrange
        filename = "not_exists.txt"

        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )

        # Act & Assert
        with pytest.raises(Exception):
            az_client.download(filename)

    @pytest.mark.integration
    @pytest.mark.azure
    def test_list_blob_with_prefix_length(self):
        # Arrange
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )

        # Act
        blobs = az_client.list_blobs(prefix="test_data")

        # Assert
        assert len(blobs) == 1

    @pytest.mark.integration
    @pytest.mark.azure
    def test_list_blob_with_prefix_and_pattern(self):
        # Arrange
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )
        pattern = "^1C2025\/[0-9]+\/initial-project\.pdf$"

        # Act
        blobs = az_client.list_blobs(prefix="1C2025", pattern=pattern)

        # Assert
        assert len(blobs) == 1

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "blobname, expected",
        [
            ("1C2025/1/initial-project.pdf", True),
            ("1C2025/2/initial-project.pdf", True),
            ("1C2025/123/initial-project.pdf", True),
            ("1C2025//1/initial-project.pdf", False),
            ("1C2025/initial-project.pdf", False),
            ("1C2025//1/initial-project.pdf", False),
        ],
    )
    def test_matches_pattern(self, blobname, expected):
        # Arrange
        container_name = api_config.container
        access_key = api_config.storage_access_key
        az_client = AzureContainerClient(
            container=container_name, access_key=access_key
        )
        pattern = "^1C2025\\/[0-9]+\\/initial-project\\.pdf$"

        # Act
        result = az_client._matches_pattern(blobname=blobname, pattern=pattern)

        # Assert
        assert result is expected
