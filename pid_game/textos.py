"""Carga y valida el catálogo editable de textos en español."""
from __future__ import annotations

import json
from pathlib import Path
from string import Formatter
from typing import Any


TEXT_PATH = Path(__file__).with_name("textos_es.json")

# Un marcador declara el nombre y, cuando corresponde, el formato del valor.
# Mantener esta lista permite detectar cambios accidentales en plantillas que
# la interfaz completa en tiempo de ejecución.
TEMPLATE_FIELDS = {
    "game.attempt": {"numero"},
    "game.run": {"numero"},
    "game.playback": {"duracion", "velocidad"},
    "game.reference": {"grados", "tiempo"},
    "game.time": {"duracion"},
    "game.gain_caption": {"nombre", "significado"},
    "game.gain_accessible_name": {"nombre", "significado"},
    "game.gain_accessible_description": {"maximo", "unidad"},
    "game.gain_slider_accessible_name": {"nombre", "significado"},
    "game.analysis_wait": {"segundos"},
    "report.delta": {"cantidad", "direccion"},
    "report.result_detail": {"estado"},
    "report.attempt_title": {"numero", "estado"},
    "report.best_attempt": {"numero", "estado"},
    "ranking.player_title": {"alias"},
    "ranking.result": {"iae", "puesto", "total"},
}


class TextCatalogError(ValueError):
    """El catálogo no se pudo leer o no cumple el formato esperado."""


class TextFormatError(TextCatalogError):
    """Una clave de texto se pidió con marcadores incompatibles."""


TEXTS: dict[str, Any] = {}
_LOADED = False
_FORMATTER = Formatter()


def _field_names(template: str, *, key: str, path: Path) -> set[str]:
    """Devuelve los marcadores y rechaza sintaxis ambigua o no admitida."""
    fields: set[str] = set()
    try:
        parsed = _FORMATTER.parse(template)
        for _literal, field_name, format_spec, conversion in parsed:
            if field_name is None:
                continue
            if not field_name.isidentifier():
                raise TextCatalogError(
                    f"{path}: la plantilla '{key}' usa un marcador inválido "
                    f"({field_name!r}); usa nombres como {{numero}}."
                )
            if conversion is not None or "{" in format_spec or "}" in format_spec:
                raise TextCatalogError(
                    f"{path}: la plantilla '{key}' usa una conversión o formato "
                    "de marcador no admitido."
                )
            fields.add(field_name)
    except ValueError as exc:
        if isinstance(exc, TextCatalogError):
            raise
        raise TextCatalogError(
            f"{path}: la plantilla '{key}' tiene llaves sin cerrar o formato inválido."
        ) from exc
    return fields


def _validate_tree(value: Any, path: Path, prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_key = f"{prefix}.{key}" if prefix else key
            if not isinstance(key, str) or not key:
                raise TextCatalogError(f"{path}: las claves deben ser nombres no vacíos.")
            _validate_tree(child, path, child_key)
        return

    if not isinstance(value, str):
        raise TextCatalogError(
            f"{path}: '{prefix}' debe contener texto o un objeto de textos."
        )

    fields = _field_names(value, key=prefix, path=path)
    expected = TEMPLATE_FIELDS.get(prefix)
    if expected is None and fields:
        raise TextCatalogError(
            f"{path}: la plantilla '{prefix}' usa marcadores sin declarar: "
            f"{', '.join(sorted(fields))}."
        )
    if expected is not None and fields != expected:
        missing = expected - fields
        unexpected = fields - expected
        details = []
        if missing:
            details.append(f"faltan {', '.join(sorted(missing))}")
        if unexpected:
            details.append(f"sobran {', '.join(sorted(unexpected))}")
        raise TextCatalogError(
            f"{path}: la plantilla '{prefix}' no coincide con sus marcadores "
            f"declarados ({'; '.join(details)})."
        )


def load_texts(path: str | Path | None = None) -> dict[str, Any]:
    """Lee y valida un catálogo; admite UTF-8 normal o UTF-8 con BOM.

    Al llamar sin ruta, el resultado queda como catálogo activo para ``text``.
    Una ruta explícita sirve para validar catálogos sin cambiar el global.
    """
    global TEXTS, _LOADED
    source = Path(path) if path is not None else TEXT_PATH
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise TextCatalogError(f"No se pudo leer el catálogo {source}: {exc.strerror or exc}.") from exc

    # UTF-8-SIG permite los archivos guardados por editores que añaden BOM.
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        contents = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        prefix = raw[:exc.start].decode("utf-8", errors="replace")
        line = prefix.count("\n") + 1
        column = len(prefix.rsplit("\n", 1)[-1]) + 1
        raise TextCatalogError(
            f"Catálogo {source} (línea {line}, columna {column}): "
            "codificación UTF-8 inválida; se admite BOM UTF-8."
        ) from exc

    try:
        catalog = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise TextCatalogError(
            f"JSON inválido en {source} (línea {exc.lineno}, columna {exc.colno}): {exc.msg}."
        ) from exc

    if not isinstance(catalog, dict) or not catalog:
        raise TextCatalogError(
            f"{source}: el catálogo debe ser un objeto JSON con al menos una sección."
        )
    _validate_tree(catalog, source)
    if path is None:
        TEXTS = catalog
        _LOADED = True
    return catalog


def text(key: str, **values: Any) -> str:
    """Obtiene un texto por clave y sustituye marcadores nombrados.

    Ejemplo: ``text("game.attempt", numero=2)``.
    """
    if not _LOADED:
        load_texts()

    value: Any = TEXTS
    try:
        for part in key.split("."):
            value = value[part]
    except (KeyError, TypeError) as exc:
        raise TextCatalogError(f"No existe la clave de texto '{key}' en {TEXT_PATH}.") from exc
    if not isinstance(value, str):
        raise TextCatalogError(f"La clave de texto '{key}' en {TEXT_PATH} no contiene un texto.")

    expected = TEMPLATE_FIELDS.get(key, set())
    supplied = set(values)
    if supplied != expected:
        missing = expected - supplied
        unexpected = supplied - expected
        details = []
        if missing:
            details.append(f"faltan valores para {', '.join(sorted(missing))}")
        if unexpected:
            details.append(f"valores no usados: {', '.join(sorted(unexpected))}")
        raise TextFormatError(f"No se pudo completar '{key}': {'; '.join(details)}.")
    try:
        return value.format(**values) if expected else value
    except (IndexError, KeyError, ValueError, TypeError) as exc:
        raise TextFormatError(f"No se pudo completar la plantilla '{key}': {exc}.") from exc
