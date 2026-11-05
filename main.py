"""Punto de entrada: valida el catálogo antes de importar la interfaz."""
import sys

from pid_game.textos import TextCatalogError, load_texts


try:
    load_texts()
except TextCatalogError as exc:
    print(f"Error en textos_es.json: {exc}", file=sys.stderr)
    raise SystemExit(2)

from pid_game.ui import main


if __name__ == "__main__":
    main()
