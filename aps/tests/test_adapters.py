"""数据适配器单元测试"""

import tempfile
from pathlib import Path

import pytest

from aps.adapters.base import DataConfig


class TestDataConfig:
    """DataConfig测试"""

    def test_config_creation(self):
        config = DataConfig(source_type="file", file_path="/data/orders.json")
        assert config.source_type == "file"
        assert config.file_path == "/data/orders.json"

    def test_config_defaults(self):
        config = DataConfig(source_type="database")
        assert config.refresh_interval == 300
        assert config.timeout == 30
        assert config.retry_count == 3

    def test_config_api(self):
        config = DataConfig(
            source_type="api",
            api_url="https://api.example.com",
            api_key="secret_key",
        )
        assert config.api_url == "https://api.example.com"
        assert config.api_key == "secret_key"

    def test_config_database(self):
        config = DataConfig(
            source_type="database",
            connection_string="sqlite:///test.db",
        )
        assert config.connection_string == "sqlite:///test.db"


class TestFileAdapter:
    """FileAdapter测试"""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_file_adapter_creation(self, temp_dir):
        from aps.adapters.file import FileAdapter

        file_path = temp_dir / "test.json"
        file_path.write_text("{}")

        config = DataConfig(source_type="file", file_path=str(file_path))
        adapter = FileAdapter(config)
        assert adapter is not None


class TestDatabaseAdapter:
    """DatabaseAdapter测试"""

    def test_sqlite_adapter_creation(self):
        from aps.adapters.database import DatabaseAdapter

        config = DataConfig(
            source_type="database",
            connection_string="sqlite:///:memory:",
        )

        adapter = DatabaseAdapter(config)
        assert adapter is not None


class TestRESTAdapter:
    """RESTAdapter测试"""

    def test_rest_adapter_config(self):
        config = DataConfig(
            source_type="api",
            api_url="https://api.example.com",
            api_key="test_key",
        )
        assert config.api_url == "https://api.example.com"
        assert config.api_key == "test_key"
