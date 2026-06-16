import pytest
from pathlib import Path
from app.services.inferrer import FieldInfo
from app.services.test_generator import generate_tests


class TestTestGenerator:
    def test_generates_test_file(self, tmp_path):
        records = [{"id": 1, "name": "Alice"}]
        fields = [
            FieldInfo(name="id", type_str="int", description="Id"),
            FieldInfo(name="name", type_str="str", description="Name"),
        ]
        code = generate_tests(records, fields, "User", "test.json", "json", tmp_path)
        assert "test_all_records_validate" in code
        assert "test_field_types" in code
        assert "test_serialization_roundtrip" in code
        assert "User(**record)" in code
        assert "from user_contract import User" in code

    def test_creates_sample_file(self, tmp_path):
        records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        fields = [FieldInfo(name="id", type_str="int", description="Id")]
        generate_tests(records, fields, "Test", "test.json", "json", tmp_path)
        sample = tmp_path / "test_sample.json"
        assert sample.exists()
        import json
        data = json.loads(sample.read_text())
        assert len(data) == 2

    def test_generates_with_nested_imports(self, tmp_path):
        records = [{"addr": {"city": "NYC"}}]
        fields = [
            FieldInfo(
                name="addr",
                type_str="Address",
                description="Addr",
                nested_fields=[FieldInfo(name="city", type_str="str", description="City")],
                nested_name="Address",
            ),
        ]
        code = generate_tests(records, fields, "User", "test.json", "json", tmp_path)
        assert "from user_contract import Address" in code

    def test_generates_with_enum_imports(self, tmp_path):
        records = [{"status": "active"}]
        fields = [
            FieldInfo(
                name="status",
                type_str="StatusEnum",
                description="Status",
                enum_values=["active", "inactive"],
            ),
        ]
        code = generate_tests(records, fields, "User", "test.json", "json", tmp_path)
        assert "from user_contract import StatusEnum" in code

    def test_limits_sample_to_10(self, tmp_path):
        records = [{"i": i} for i in range(20)]
        fields = [FieldInfo(name="i", type_str="int", description="I")]
        generate_tests(records, fields, "Test", "test.json", "json", tmp_path)
        import json
        data = json.loads((tmp_path / "test_sample.json").read_text())
        assert len(data) == 10
