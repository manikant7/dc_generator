import pytest
from app.services.inferrer import infer_schema, FieldInfo


class TestInferrer:
    def test_empty_records(self):
        with pytest.raises(ValueError, match="No records"):
            infer_schema([])

    def test_basic_types(self):
        records = [
            {"id": 1, "name": "Alice", "score": 95.5, "active": True, "missing": None},
            {"id": 2, "name": "Bob", "score": 87.2, "active": False, "missing": None},
        ]
        fields = infer_schema(records, "Test")
        field_map = {f.name: f for f in fields}

        assert field_map["id"].type_str == "int"
        assert field_map["name"].type_str == "str"
        assert field_map["score"].type_str == "float"
        assert field_map["active"].type_str == "bool"
        assert field_map["missing"].type_str == "Optional[str]"
        assert field_map["missing"].nullable is True

    def test_optional_field(self):
        records = [
            {"a": 1, "b": "hello"},
            {"a": None, "b": "world"},
        ]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert fmap["a"].nullable is True
        assert "Optional" in fmap["a"].type_str

    def test_nested_object(self):
        records = [
            {"user": {"name": "Alice", "age": 30}},
            {"user": {"name": "Bob", "age": 25}},
        ]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert fmap["user"].nested_fields is not None
        assert len(fmap["user"].nested_fields) == 2

    def test_list_field(self):
        records = [
            {"tags": ["a", "b"]},
            {"tags": ["c"]},
        ]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert fmap["tags"].type_str.startswith("List[")

    def test_enum_detection(self):
        records = [
            {"role": "admin"},
            {"role": "user"},
            {"role": "admin"},
            {"role": "user"},
        ]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert len(fmap["role"].enum_values) == 2
        assert "admin" in fmap["role"].enum_values
        assert "user" in fmap["role"].enum_values

    def test_date_detection(self):
        records = [
            {"dt": "2024-01-15"},
            {"dt": "2024-03-20"},
        ]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert "date" in fmap["dt"].type_str

    def test_datetime_detection(self):
        records = [
            {"ts": "2024-01-15T10:30:00"},
            {"ts": "2024-03-20T14:00:00"},
        ]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert "datetime" in fmap["ts"].type_str

    def test_no_enum_when_all_unique(self):
        records = [{"email": f"user{i}@test.com"} for i in range(10)]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert fmap["email"].type_str == "str"
        assert not fmap["email"].enum_values

    def test_list_of_nested(self):
        records = [
            {"items": [{"x": 1}, {"x": 2}]},
            {"items": [{"x": 3}]},
        ]
        fields = infer_schema(records, "Test")
        fmap = {f.name: f for f in fields}
        assert fmap["items"].type_str.startswith("List[")
