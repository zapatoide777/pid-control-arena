import codecs

import pytest

from pid_game.textos import TextCatalogError, TextFormatError, load_texts, text


def test_default_catalog_loads_and_formats_named_templates():
    catalog = load_texts()

    assert catalog["menu"]["ranking_rule"] == "Se guarda el mejor intento."
    assert text("game.attempt", numero=2) == "Intento 2 de 3"
    assert text("report.best_attempt", numero=3, estado="Estable") == (
        "Mejor intento: 3 · Estable · Menor IAE es mejor"
    )
    assert text("ranking.result", iae=12.345, puesto=2, total=6) == (
        "12.35 pts · puesto 2 de 6"
    )


def test_load_texts_accepts_utf8_bom(tmp_path):
    path = tmp_path / "textos.json"
    path.write_bytes(codecs.BOM_UTF8 + b'{"menu":{"title":"Hola"}}')

    assert load_texts(path) == {"menu": {"title": "Hola"}}


def test_json_error_includes_path_line_and_column(tmp_path):
    path = tmp_path / "textos.json"
    path.write_text('{\n  "menu": {\n    "title": "Hola",\n  }\n}', encoding="utf-8")

    with pytest.raises(TextCatalogError) as error:
        load_texts(path)

    message = str(error.value)
    assert str(path) in message
    assert "línea 4" in message
    assert "columna" in message


def test_invalid_utf8_reports_location_and_bom_support(tmp_path):
    path = tmp_path / "textos.json"
    path.write_bytes(b'{"menu": "ok"}\n\xff')

    with pytest.raises(TextCatalogError) as error:
        load_texts(path)

    message = str(error.value)
    assert str(path) in message
    assert "línea 2, columna 1" in message
    assert "BOM UTF-8" in message


def test_malformed_or_changed_template_markers_are_rejected(tmp_path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"game":{"attempt":"Intento {numero"}}', encoding="utf-8")
    with pytest.raises(TextCatalogError, match="plantilla 'game.attempt'"):
        load_texts(malformed)

    changed = tmp_path / "changed.json"
    changed.write_text('{"game":{"attempt":"Intento {n}"}}', encoding="utf-8")
    with pytest.raises(TextCatalogError, match="no coincide con sus marcadores"):
        load_texts(changed)


def test_text_requires_the_declared_template_values():
    with pytest.raises(TextFormatError, match="faltan valores para numero"):
        text("game.attempt")
    with pytest.raises(TextFormatError, match="valores no usados: extra"):
        text("game.attempt", numero=1, extra=2)

