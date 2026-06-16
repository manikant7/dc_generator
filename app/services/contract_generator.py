import datetime
from pathlib import Path
from typing import Tuple, List
from .inferrer import FieldInfo


def generate_contract(
    fields: list[FieldInfo],
    class_name: str,
    source: str = 'unknown',
    output_path: Path = None,
) -> str:
    timestamp = datetime.datetime.now().isoformat()

    all_models = _collect_models(fields, class_name)

    has_enums = any(f.enum_values for _, fs, _ in all_models for f in fs)
    has_datetime = any(
        f.type_str.replace('Optional[', '').rstrip(']') in ('date', 'datetime')
        for _, fs, _ in all_models for f in fs
    )

    lines = []
    lines.append("# Auto-generated Data Contract")
    lines.append(f"# Source: {source}")
    lines.append(f"# Generated: {timestamp}")
    lines.append("")
    lines.append("from pydantic import BaseModel, Field")
    lines.append("from typing import Optional, List")
    if has_enums:
        lines.append("from enum import Enum")
    if has_datetime:
        lines.append("from datetime import date, datetime")
    lines.append("")

    for model_name, model_fields, kind in all_models:
        if kind == 'enum':
            lines.extend(_generate_enum(model_name, model_fields))
        else:
            lines.extend(_generate_model(model_name, model_fields))
        lines.append("")

    code = '\n'.join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code)

    return code


def _collect_models(
    fields: list[FieldInfo], class_name: str
) -> List[Tuple[str, List[FieldInfo], str]]:
    models = []
    seen = set()

    def walk(field_list):
        for field in field_list:
            if field.enum_values and field.type_str not in seen:
                models.append((field.type_str, [field], 'enum'))
                seen.add(field.type_str)
            if field.nested_fields and field.nested_name not in seen:
                walk(field.nested_fields)
                models.append((field.nested_name, field.nested_fields, 'model'))
                seen.add(field.nested_name)

    walk(fields)
    models.append((class_name, fields, 'model'))

    return models


def _generate_enum(name: str, fields: list[FieldInfo]) -> list[str]:
    field = fields[0]
    lines = [f"class {name}(str, Enum):"]
    for v in field.enum_values:
        key = _safe_enum_key(v)
        lines.append(f"    {key} = {repr(v)}")
    return lines


def _generate_model(name: str, fields: list[FieldInfo]) -> list[str]:
    lines = [f"class {name}(BaseModel):"]

    has_fields = False
    for field in fields:
        has_fields = True
        type_str = field.type_str
        if field.nullable and not type_str.startswith('Optional['):
            type_str = f"Optional[{type_str}]"

        sanitized_name = field.name.replace('@', 'attr_').replace('.', '_').replace('-', '_')
        if not sanitized_name.isidentifier():
            sanitized_name = f"field_{hash(sanitized_name) % (10**8)}"

        if field.nullable:
            lines.append(f"    {sanitized_name}: {type_str} = Field(None, description={repr(field.description)})")
        else:
            lines.append(f"    {sanitized_name}: {type_str} = Field(..., description={repr(field.description)})")

    if not has_fields:
        lines.append("    pass")

    return lines


def _safe_enum_key(value: str) -> str:
    key = value.upper().replace('-', '_').replace(' ', '_').replace('.', '_')
    key = ''.join(c for c in key if c.isalnum() or c == '_')
    if not key or key[0].isdigit():
        key = 'VALUE_' + key
    return key
