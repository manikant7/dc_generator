import json
import csv
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path
from collections import Counter


def parse_file(file_path: str, file_type: str) -> list[dict]:
    path = Path(file_path)

    if file_type == 'json':
        return _parse_json(path)
    elif file_type == 'xml':
        return _parse_xml(path)
    elif file_type == 'csv':
        return _parse_csv(path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _parse_json(path: Path) -> list[dict]:
    data = json.loads(path.read_bytes())
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if len(data) == 1:
            key, value = next(iter(data.items()))
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
        return [data]
    else:
        raise ValueError(f"JSON root must be object or array, got {type(data).__name__}")


def _parse_xml(path: Path) -> list[dict]:
    tree = ET.parse(path)
    root = tree.getroot()

    records = _find_record_elements(root)

    if not records:
        raise ValueError("No repeating record elements found in XML")

    return [_xml_element_to_dict(r) for r in records]


def _find_record_elements(root: ET.Element) -> list[ET.Element]:
    children = list(root)
    if not children:
        return []

    tag_counts = Counter(child.tag for child in children)
    most_common_tag, count = tag_counts.most_common(1)[0]

    if count > 1 and count >= len(children) * 0.5:
        return children

    deeper = []
    for child in children:
        deeper.extend(_find_record_elements(child))

    if deeper:
        return deeper

    return children


def _xml_element_to_dict(element: ET.Element) -> dict:
    result = {}

    for key, value in element.attrib.items():
        result[f"@{key}"] = value

    child_tags = Counter(child.tag for child in element)
    for child in element:
        tag = child.tag
        child_dict = _xml_element_to_dict(child)

        if child_dict:
            is_simple_text = list(child_dict.keys()) == ['#text']
            value = child_dict['#text'] if is_simple_text else child_dict
            if child_tags[tag] > 1:
                result.setdefault(tag, [])
                result[tag].append(value)
            else:
                result[tag] = value
        else:
            text = (child.text or '').strip()
            if child_tags[tag] > 1:
                result.setdefault(tag, [])
                result[tag].append(text)
            else:
                result[tag] = text

    if not result:
        text = (element.text or '').strip()
        if text:
            return {'#text': text}

    if element.text and element.text.strip() and not result:
        result['#text'] = element.text.strip()

    return result


def _parse_csv(path: Path) -> list[dict]:
    text = path.read_text(encoding='utf-8-sig')

    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text[:4096])
        has_header = sniffer.has_header(text[:4096])
    except csv.Error:
        dialect = csv.excel
        has_header = True

    if has_header:
        reader = csv.DictReader(StringIO(text), dialect=dialect)
    else:
        text_io = StringIO(text)
        sample = text_io.readline().strip().split(dialect.delimiter)
        fieldnames = [f"col_{i+1}" for i in range(len(sample))]
        text_io.seek(0)
        reader = csv.DictReader(text_io, fieldnames=fieldnames, dialect=dialect)
        next(reader)

    records = []
    for row in reader:
        cleaned = {}
        for key, value in row.items():
            if key is None:
                continue
            clean_key = key.strip()
            if not clean_key:
                clean_key = f"col_{len(cleaned) + 1}"
            cleaned[clean_key] = value.strip() if value and value.strip() else None
        records.append(cleaned)

    return records
