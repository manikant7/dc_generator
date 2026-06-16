import json
import datetime
from pathlib import Path
from .inferrer import FieldInfo


def generate_tests(
    records: list[dict],
    fields: list[FieldInfo],
    class_name: str,
    source_path: str,
    file_type: str,
    output_dir: Path,
) -> str:
    contract_module = f"{class_name.lower()}_contract"
    sample_filename = f"{class_name.lower()}_sample.json"
    sample_path = output_dir / sample_filename

    sample_data = [_sanitize_keys(r) for r in records[:10]]
    sample_path.write_text(json.dumps(sample_data, indent=2, default=str), encoding='utf-8')

    relative_source = Path(source_path).name if source_path else sample_filename

    lines = []
    lines.append('"""')
    lines.append(f"Tests for {class_name} data contract.")
    lines.append(f"Source: {relative_source}")
    lines.append('"""')
    lines.append("import json")
    lines.append("from pathlib import Path")
    lines.append(f"from {contract_module} import {class_name}")
    for field in _all_fields(fields):
        if field.nested_name:
            lines.append(f"from {contract_module} import {field.nested_name}")
        if field.enum_values:
            lines.append(f"from {contract_module} import {field.type_str}")
    lines.append("")

    lines.append(f'SAMPLE_PATH = Path(__file__).parent / "{sample_filename}"')
    lines.append("")

    lines.append("")
    lines.append("def load_sample_data():")
    lines.append('    """Load sample records from the sample JSON file."""')
    lines.append("    with open(SAMPLE_PATH, 'r') as f:")
    lines.append("        return json.load(f)")
    lines.append("")

    lines.append("")
    lines.append("def test_all_records_validate():")
    lines.append(f'    """Every sample record should validate against {class_name}."""')
    lines.append("    records = load_sample_data()")
    lines.append("    assert len(records) > 0, \"No sample records to validate\"")
    lines.append("    for i, record in enumerate(records):")
    lines.append(f"        instance = {class_name}(**record)")
    lines.append("        assert instance is not None, f\"Record {i} failed to validate\"")
    lines.append("")

    lines.append("")
    lines.append("def test_field_types():")
    lines.append(f'    """Verify specific field types on {class_name}."""')
    lines.append("    records = load_sample_data()")
    lines.append("    assert len(records) > 0")
    lines.append("    instance = records[0]")
    lines.append(f"    model = {class_name}(**instance)")

    _add_type_assertions(lines, fields, "model", "instance", 1)

    lines.append("")

    lines.append("")
    lines.append("def test_serialization_roundtrip():")
    lines.append(f'    """Serialized data re-validates against the contract."""')
    lines.append("    records = load_sample_data()")
    lines.append("    for record in records:")
    lines.append(f"        model = {class_name}(**record)")
    lines.append("        reloaded = model.model_dump(mode='python')")
    lines.append(f"        {class_name}(**reloaded)")

    code = '\n'.join(lines)

    test_filename = f"{class_name.lower()}_test.py"
    test_path = output_dir / test_filename
    test_path.write_text(code, encoding='utf-8')

    return code


def _all_fields(fields: list[FieldInfo]) -> list[FieldInfo]:
    result = []
    for f in fields:
        result.append(f)
        if f.nested_fields:
            result.extend(_all_fields(f.nested_fields))
    return result


def _sanitize_keys(record: dict) -> dict:
    result = {}
    for k, v in record.items():
        sk = k.replace('@', 'attr_').replace('.', '_').replace('-', '_')
        if isinstance(v, dict):
            result[sk] = _sanitize_keys(v)
        elif isinstance(v, list):
            result[sk] = [_sanitize_keys(item) if isinstance(item, dict) else item for item in v]
        else:
            result[sk] = v
    return result


def _add_type_assertions(
    lines: list[str],
    fields: list[FieldInfo],
    model_var: str,
    data_var: str,
    indent: int,
):
    prefix = "    " * indent
    for field in fields:
        safe_name = field.name.replace('@', 'attr_').replace('.', '_').replace('-', '_')
        if not safe_name.isidentifier():
            safe_name = f"field_{abs(hash(field.name)) % (10**8)}"
        base_type = field.type_str.replace('Optional[', '').rstrip(']')
        if field.nested_fields:
            lines.append(f"{prefix}assert isinstance({model_var}.{safe_name}, {field.nested_name}) or {model_var}.{safe_name} is None")
        elif field.enum_values:
            lines.append(f"{prefix}assert {model_var}.{safe_name} is None or isinstance({model_var}.{safe_name}, {field.type_str})")
        elif base_type in ('int', 'float', 'str', 'bool'):
            py_type = {'int': 'int', 'float': 'float', 'str': 'str', 'bool': 'bool'}[base_type]
            lines.append(f"{prefix}if \"{safe_name}\" in {data_var} and {data_var}[\"{safe_name}\"] is not None:")
            lines.append(f"{prefix}    assert isinstance({model_var}.{safe_name}, {py_type}), f\"{safe_name} should be {py_type}, got {{type({model_var}.{safe_name})}}\"")
        elif base_type in ('date', 'datetime'):
            lines.append(f"{prefix}if \"{safe_name}\" in {data_var} and {data_var}[\"{safe_name}\"] is not None:")
            lines.append(f"{prefix}    assert hasattr({model_var}.{safe_name}, 'isoformat'), f\"{safe_name} should be date/datetime\"")
