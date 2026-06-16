from datetime import datetime
from typing import Any
from dataclasses import dataclass, field
import re


@dataclass
class FieldInfo:
    name: str
    type_str: str = 'str'
    nullable: bool = False
    example: Any = None
    description: str = ''
    nested_fields: list['FieldInfo'] = field(default_factory=list)
    nested_name: str = ''
    enum_values: list[str] = field(default_factory=list)


def infer_schema(records: list[dict], class_name: str = 'DataRecord') -> list[FieldInfo]:
    if not records:
        raise ValueError("No records to infer schema from")

    coerced = [_coerce_record(r) for r in records]

    all_keys = set()
    for record in coerced:
        all_keys.update(record.keys())

    field_values = {key: [] for key in all_keys}
    for record in coerced:
        for key in all_keys:
            field_values[key].append(record.get(key))

    return [_infer_field_type(k, field_values[k], class_name) for k in sorted(all_keys)]


def _coerce_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    lower = stripped.lower()
    if lower in ('true', 'false'):
        return lower == 'true'
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return value


def _coerce_record(record: dict) -> dict:
    result = {}
    for k, v in record.items():
        if isinstance(v, dict):
            result[k] = _coerce_record(v)
        elif isinstance(v, list):
            result[k] = [
                _coerce_record(item) if isinstance(item, dict) else _coerce_string(item)
                for item in v
            ]
        else:
            result[k] = _coerce_string(v)
    return result


def _infer_field_type(name: str, values: list, parent_class: str) -> FieldInfo:
    non_null = [v for v in values if v is not None and v != '' and v != [] and v != {}]
    nullable = any(v is None or v == '' for v in values)

    if not non_null:
        return FieldInfo(name=name, type_str='Optional[str]', nullable=True, example=None)

    example = non_null[0]

    if all(isinstance(v, dict) for v in non_null):
        nested_name = _to_class_name(name, parent_class)
        nested_fields = _infer_nested_fields(non_null, nested_name)
        return FieldInfo(
            name=name,
            type_str=nested_name,
            nullable=nullable,
            example=_truncate(str(example)),
            nested_fields=nested_fields,
            nested_name=nested_name,
            description=_describe(name),
        )

    if all(isinstance(v, list) for v in non_null):
        inner_values = [item for sublist in non_null for item in sublist]
        inner_field = _infer_field_type(f'{name}_item', inner_values, parent_class)

        if inner_field.nested_fields:
            inner_type = inner_field.nested_name
        elif inner_field.enum_values:
            inner_type = inner_field.type_str
        else:
            inner_type = inner_field.type_str.replace('Optional[', '').rstrip(']')

        nested = list(inner_field.nested_fields)
        if inner_field.enum_values and inner_field.type_str not in {f.type_str for f in nested}:
            enum_placeholder = FieldInfo(
                name=inner_field.name,
                type_str=inner_field.type_str,
                enum_values=inner_field.enum_values,
            )
            nested.append(enum_placeholder)

        return FieldInfo(
            name=name,
            type_str=f'List[{inner_type}]',
            nullable=nullable,
            example=_truncate(str(example)),
            nested_fields=nested,
            nested_name=inner_field.nested_name,
            description=_describe(name),
        )

    if all(isinstance(v, bool) for v in non_null):
        return FieldInfo(
            name=name,
            type_str=_opt('bool', nullable),
            nullable=nullable,
            example=example,
            description=_describe(name),
        )

    if all(isinstance(v, int) and not isinstance(v, bool) for v in non_null):
        return FieldInfo(
            name=name,
            type_str=_opt('int', nullable),
            nullable=nullable,
            example=example,
            description=_describe(name),
        )

    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_null):
        return FieldInfo(
            name=name,
            type_str=_opt('float', nullable),
            nullable=nullable,
            example=example,
            description=_describe(name),
        )

    str_values = [str(v) for v in non_null]

    date_count = 0
    datetime_count = 0
    for v in str_values:
        try:
            parsed = datetime.fromisoformat(v.replace('Z', '+00:00').replace('z', '+00:00'))
            datetime_count += 1
            if 'T' not in v:
                date_count += 1
        except (ValueError, TypeError):
            pass

    if datetime_count == len(str_values) and len(str_values) > 0:
        is_date = date_count == len(str_values)
        type_name = 'date' if is_date else 'datetime'
        return FieldInfo(
            name=name,
            type_str=_opt(type_name, nullable),
            nullable=nullable,
            example=_truncate(str(example)),
            description=_describe(name),
        )

    unique = set(str_values)
    if 2 <= len(unique) <= 5 and len(unique) < len(str_values) and len(unique) / len(str_values) >= 0.5:
        enum_name = _to_class_name(f'{name}_enum', parent_class)
        return FieldInfo(
            name=name,
            type_str=enum_name,
            nullable=nullable,
            example=_truncate(str(example)),
            enum_values=sorted(unique),
            description=_describe(name),
        )

    return FieldInfo(
        name=name,
        type_str=_opt('str', nullable),
        nullable=nullable,
        example=_truncate(str(example)),
        description=_describe(name),
    )


def _infer_nested_fields(records: list[dict], parent_class: str) -> list[FieldInfo]:
    if not records:
        return []
    all_keys = set()
    for record in records:
        all_keys.update(record.keys())
    field_values = {key: [] for key in all_keys}
    for record in records:
        for key in all_keys:
            field_values[key].append(record.get(key))
    return [_infer_field_type(k, field_values[k], parent_class) for k in sorted(all_keys)]


def _opt(type_name: str, nullable: bool) -> str:
    return f"Optional[{type_name}]" if nullable else type_name


def _to_class_name(name: str, parent: str = '') -> str:
    name = re.sub(r'[-.\s]+', '_', name)
    name = re.sub(r'_item$', '', name)
    name = name.lstrip('@#')
    parts = name.split('_')
    result = ''.join(p.capitalize() for p in parts if p)
    if result == parent:
        result += 'Field'
    return result


def _describe(name: str) -> str:
    return name.replace('_', ' ').replace('@', '').strip().title()


def _truncate(s: str, max_len: int = 100) -> str:
    return s[:max_len] + '...' if len(s) > max_len else s
