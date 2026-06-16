import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path


SUPPORTED_TYPES = ('json', 'xml', 'csv')


def detect_file_type(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    ext = path.suffix.lower().lstrip('.')
    if ext in SUPPORTED_TYPES:
        if _validate_content(path, ext):
            return ext

    for file_type in SUPPORTED_TYPES:
        if _validate_content(path, file_type):
            return file_type

    raise ValueError(f"Unable to detect file type for: {file_path}")


def _validate_content(path: Path, file_type: str) -> bool:
    try:
        content = path.read_bytes()
        return _validate_bytes(content, file_type)
    except Exception:
        return False


def _validate_bytes(content: bytes, file_type: str) -> bool:
    try:
        if file_type == 'json':
            json.loads(content)
            return True
        elif file_type == 'xml':
            ET.fromstring(content)
            return True
        elif file_type == 'csv':
            try:
                text = content.decode('utf-8-sig')
                sniffer = csv.Sniffer()
                sniffer.sniff(text[:4096])
                return True
            except csv.Error:
                return False
    except Exception:
        return False
    return False


def detect_type_from_content(content: str) -> str:
    data = content.encode('utf-8')
    for file_type in SUPPORTED_TYPES:
        if _validate_bytes(data, file_type):
            return file_type
    raise ValueError("Unable to detect data type from content")
