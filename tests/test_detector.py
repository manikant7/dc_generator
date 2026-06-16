import pytest
from pathlib import Path
from app.services.detector import (
    detect_file_type,
    detect_type_from_content,
    SUPPORTED_TYPES,
)

DATA_DIR = Path(__file__).parent.parent / "test_data"


class TestDetectFileType:
    def test_detect_json(self):
        assert detect_file_type(str(DATA_DIR / "users.json")) == "json"

    def test_detect_xml(self):
        assert detect_file_type(str(DATA_DIR / "employees.xml")) == "xml"

    def test_detect_csv(self):
        assert detect_file_type(str(DATA_DIR / "products.csv")) == "csv"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            detect_file_type("/nonexistent/file.json")

    def test_not_a_file(self):
        with pytest.raises(ValueError, match="not a file"):
            detect_file_type(str(DATA_DIR))


class TestDetectTypeFromContent:
    def test_json_content(self):
        assert detect_type_from_content('[{"a": 1}]') == "json"
        assert detect_type_from_content('{"a": 1}') == "json"

    def test_xml_content(self):
        assert detect_type_from_content("<root><item>a</item></root>") == "xml"

    def test_csv_content(self):
        assert detect_type_from_content("a,b\n1,2") == "csv"

    def test_invalid_content(self):
        with pytest.raises(ValueError, match="Unable to detect"):
            detect_type_from_content("")
