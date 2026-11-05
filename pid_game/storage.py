"""Ranking local versionado, validado y escrito mediante reemplazo atómico."""
from dataclasses import asdict
from datetime import datetime
import json
import math
from pathlib import Path
import os
from .controller import Gains
from .game import Game

# Identifica planta, prueba, PID y métrica. Cambiar si se cambia el desafío.
CHALLENGE = "pivot-v10-dcmotor-r2-l.16-k.333-v12-i6-coulomb.015-step5-45deg-w2-T15-dt.001-iae-deg"


class Ranking:
    def __init__(self, path: Path):
        self.path = path
        self.warning = ""
        self.records: list[dict] = []
        self.writable = True
        self.load()

    def load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema") != 2 or data.get("challenge") != CHALLENGE:
                raise ValueError("Versión o desafío incompatible.")
            records = data["records"]
            if not isinstance(records, list):
                raise ValueError("Lista de resultados inválida.")
            ids = set()
            for r in records:
                if not isinstance(r, dict):
                    raise ValueError("Registro inválido.")
                if not isinstance(r["id"], str) or not r["id"] or r["id"] in ids:
                    raise ValueError("Identificador inválido o repetido.")
                ids.add(r["id"])
                if not isinstance(r["alias"], str) or not 1 <= len(r["alias"]) <= 32:
                    raise ValueError("Alias inválido.")
                datetime.fromisoformat(r["date"])
                if type(r["iae"]) not in (float, int) or not math.isfinite(r["iae"]) or r["iae"] < 0:
                    raise ValueError("Error integrado inválido.")
                Gains(**r["gains"])
                if type(r["success"]) is not bool:
                    raise ValueError("Estado inválido.")
            self.records = records
        except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            self.records = []
            self.warning = f"No se pudo leer el ranking ({exc}). "
            # Conservar original dañado/incompatible antes de permitir nuevas escrituras.
            backup = self.path.with_name(self.path.name + ".backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
            try:
                self.path.replace(backup)
                self.warning += f"Se conservó el archivo original en {backup.name}."
            except OSError:
                self.writable = False
                self.warning += "El original se conserva; los nuevos resultados serán solo de esta sesión."

    def add_game(self, game: Game) -> dict:
        result = game.final
        existing = next((r for r in self.records if r["id"] == game.record_id), None)
        if existing:
            return existing
        record = {"id": game.record_id, "alias": game.alias,
                  "date": datetime.now().astimezone().isoformat(timespec="seconds"),
                  "gains": asdict(result.gains), "iae": result.iae,
                  "success": result.success}
        self.records.append(record)
        try:
            if not self.writable:
                raise OSError("No se puede escribir conservando el archivo original.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump({"schema": 2, "challenge": CHALLENGE, "records": self.records},
                          stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        except OSError as exc:
            self.warning = f"Resultado disponible en esta sesión, pero no se pudo guardar: {exc}"
        return record

    def ordered(self) -> list[dict]:
        # Orden estable: la posición de registro desempata IAE idénticos.
        return sorted(self.records, key=lambda r: r["iae"])
