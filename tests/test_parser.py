import pytest
from pathlib import Path
from app.services.parser import parse_file, parse_string

DATA_DIR = Path(__file__).parent.parent / "test_data"


class TestParseJson:
    def test_parse_json_file(self):
        records = parse_file(str(DATA_DIR / "users.json"), "json")
        assert len(records) == 3
        assert records[0]["name"] == "Alice Johnson"
        assert records[0]["id"] == 1
        assert records[0]["address"]["city"] == "New York"

    def test_parse_json_string_array(self):
        data = '[{"x": 1}, {"x": 2}]'
        records = parse_string(data, "json")
        assert len(records) == 2
        assert records[0]["x"] == 1

    def test_parse_json_string_object(self):
        data = '{"x": 1, "y": 2}'
        records = parse_string(data, "json")
        assert len(records) == 1
        assert records[0]["x"] == 1

    def test_parse_json_string_wrapped(self):
        data = '{"items": [{"a": 1}, {"a": 2}]}'
        records = parse_string(data, "json")
        assert len(records) == 2

    def test_invalid_json(self):
        with pytest.raises(Exception):
            parse_string("not json", "json")


class TestParseXml:
    def test_parse_xml_file(self):
        records = parse_file(str(DATA_DIR / "employees.xml"), "xml")
        assert len(records) == 3
        assert records[0]["@id"] == "E001"
        assert records[0]["name"] == "Jane Doe"
        assert records[0]["department"] == "Engineering"

    def test_parse_xml_string(self):
        xml = """<?xml version="1.0"?>
<items>
  <item id="1"><name>Foo</name><val>10</val></item>
  <item id="2"><name>Bar</name><val>20</val></item>
</items>"""
        records = parse_string(xml, "xml")
        assert len(records) == 2
        assert records[0]["@id"] == "1"
        assert records[0]["name"] == "Foo"

    def test_invalid_xml(self):
        with pytest.raises(Exception):
            parse_string("not xml", "xml")


class TestParseCsv:
    def test_parse_csv_file(self):
        records = parse_file(str(DATA_DIR / "products.csv"), "csv")
        assert len(records) == 5
        assert records[0]["product_id"] == "P001"
        assert records[0]["name"] == "Wireless Mouse"

    def test_parse_csv_string_with_header(self):
        csv = "a,b,c\n1,2,3\n4,5,6"
        records = parse_string(csv, "csv")
        assert len(records) == 2
        assert records[0]["a"] == "1"
        assert records[1]["c"] == "6"

    def test_parse_csv_string_without_header(self):
        csv = "1,2,3\n4,5,6\n7,8,9"
        records = parse_string(csv, "csv")
        assert len(records) == 2
        assert "col_1" in records[0]
        assert records[0]["col_1"] == "4"
