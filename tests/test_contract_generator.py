import pytest
from pathlib import Path
from app.services.inferrer import FieldInfo
from app.services.contract_generator import generate_contract


class TestContractGenerator:
    def test_generate_basic_model(self):
        fields = [
            FieldInfo(name="id", type_str="int", description="Id", example=1),
            FieldInfo(name="name", type_str="str", description="Name", example="Alice"),
        ]
        code = generate_contract(fields, "User", "test")
        assert "class User(BaseModel):" in code
        assert "id: int = Field(..." in code
        assert "name: str = Field(..." in code
        assert "from pydantic import BaseModel, Field" in code

    def test_generate_with_optional(self):
        fields = [
            FieldInfo(name="nickname", type_str="Optional[str]", nullable=True, description="Nickname"),
        ]
        code = generate_contract(fields, "Test", "test")
        assert "Optional[str]" in code
        assert "Field(None" in code

    def test_generate_with_enum(self):
        fields = [
            FieldInfo(
                name="status",
                type_str="StatusEnum",
                description="Status",
                enum_values=["active", "inactive"],
            ),
        ]
        code = generate_contract(fields, "Test", "test")
        assert "class StatusEnum(str, Enum):" in code
        assert "ACTIVE = 'active'" in code
        assert "INACTIVE = 'inactive'" in code

    def test_generate_with_nested_model(self):
        addr = FieldInfo(name="city", type_str="str", description="City")
        fields = [
            FieldInfo(
                name="address",
                type_str="Address",
                description="Address",
                nested_fields=[addr],
                nested_name="Address",
                nullable=True,
            ),
        ]
        code = generate_contract(fields, "User", "test")
        assert "class Address(BaseModel):" in code
        assert "class User(BaseModel):" in code

    def test_generate_writes_file(self, tmp_path):
        fields = [FieldInfo(name="x", type_str="int", description="X")]
        out = tmp_path / "out.py"
        code = generate_contract(fields, "Test", "test", output_path=out)
        assert out.exists()
        assert out.read_text() == code

    def test_datetime_import(self):
        fields = [FieldInfo(name="created", type_str="date", description="Created")]
        code = generate_contract(fields, "Test", "test")
        assert "from datetime import date, datetime" in code
