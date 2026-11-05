import json
from pathlib import Path

import pytest

from pid_game.controller import Gains
from pid_game.game import Game
from pid_game.storage import Ranking, CHALLENGE


def completed_game(alias="Jugador", final=Gains()):
    game = Game()
    game.begin(alias)
    game.complete_demo()
    for gains in (Gains(2, 1, .5), Gains(1, 0, .2), final):
        game.launch(gains)
        game.finish_playback(10)
        if len(game.attempts) < 3:
            game.continue_editing(13)
    return game


def test_missing_file_persistence_best_attempt_and_idempotence(tmp_path):
    path = tmp_path / "nested" / "ranking.json"
    ranking = Ranking(path)
    assert ranking.records == [] and not path.exists()
    game = completed_game("María")
    record = ranking.add_game(game)
    ranking.add_game(game)
    assert len(ranking.records) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["schema"] == 2
    restored = Ranking(path)
    assert restored.records == [record]
    assert record["iae"] == game.final.iae
    assert record["gains"] == {"kp": 2, "ki": 1, "kd": .5}
    assert record["alias"] == "María"
    assert "fallen" not in record
    assert not path.with_suffix(".json.tmp").exists()


def test_ranking_uses_only_iae_and_stable_tie_order(tmp_path):
    ranking = Ranking(tmp_path / "ranking.json")
    a = ranking.add_game(completed_game("primero"))
    b = ranking.add_game(completed_game("segundo"))
    c = ranking.add_game(completed_game("tercero", Gains(2, 1, .5)))
    assert [r["id"] for r in ranking.ordered()] == [a["id"], b["id"], c["id"]]
    # El éxito no participa en el orden.
    a["iae"], a["success"] = 0.01, False
    assert ranking.ordered()[0] is a


def test_previous_v9_challenge_is_archived_before_new_ranking(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1,
           "challenge": "pivot-v9-dcmotor-r2-l.16-k.333-v12-i6-coulomb.015-step5-45deg-w2-T15-dt.001-iae-deg",
           "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert ranking.records == [] and "incompatible" in ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == old


def test_schema_one_ranking_is_archived_even_with_current_challenge(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1, "challenge": CHALLENGE, "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert ranking.records == [] and "incompatible" in ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == old


@pytest.mark.parametrize("content", ["{broken", "[]", '{"schema": 99}',
    json.dumps({"schema": 1, "challenge": CHALLENGE, "records": [{}]})])
def test_corrupt_or_incompatible_file_preserved(tmp_path, content):
    path = tmp_path / "ranking.json"
    path.write_text(content, encoding="utf-8")
    ranking = Ranking(path)
    assert ranking.records == [] and ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == content
    ranking.add_game(completed_game())
    assert len(Ranking(path).records) == 1


def test_previous_three_second_challenge_is_archived_not_mixed(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1, "challenge": "pivot-v1-m.2-l.3-J.024-b.01-g9.81-w1-T3-dt.001-f.02-u2-iae-deg",
           "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert ranking.records == [] and "incompatible" in ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == old


def test_previous_t6_one_rads_challenge_is_archived_after_push_change(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1, "challenge": "pivot-v2-m.2-l.3-J.024-b.01-g9.81-w1-T6-stable-last1-5deg-dt.001-f.02-u2-iae-deg",
           "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert ranking.records == [] and "incompatible" in ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == old


def test_disk_write_error_keeps_result_in_memory(tmp_path, monkeypatch):
    ranking = Ranking(tmp_path / "ranking.json")
    def fail(*args, **kwargs):
        raise PermissionError("prueba")
    monkeypatch.setattr(Path, "mkdir", fail)
    ranking.add_game(completed_game())
    assert len(ranking.records) == 1
    assert "no se pudo guardar" in ranking.warning


def test_unfinished_game_cannot_be_registered(tmp_path):
    game = Game()
    game.begin("test")
    with pytest.raises(RuntimeError):
        Ranking(tmp_path / "ranking.json").add_game(game)


@pytest.mark.parametrize("field", ["iae", "gains"])
def test_huge_numbers_in_corrupt_ranking_do_not_crash_startup(tmp_path, field):
    path = tmp_path / "ranking.json"
    ranking = Ranking(path)
    record = ranking.add_game(completed_game())
    record[field] = 10**400 if field == "iae" else {"kp": 10**400, "ki": 0, "kd": 0}
    path.write_text(json.dumps({"schema": 2, "challenge": CHALLENGE, "records": [record]}), encoding="utf-8")
    restored = Ranking(path)
    assert restored.records == []
    assert restored.warning
    assert len(list(tmp_path.glob("ranking.json.backup-*"))) == 1


def test_previous_six_second_same_push_challenge_is_archived(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1, "challenge": "pivot-v3-m.2-l.3-J.024-b.01-g9.81-w2-T6-stable-last1-5deg-dt.001-f.02-u2-iae-deg", "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert not ranking.records and "incompatible" in ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == old


def test_previous_instant_actuator_challenge_is_archived(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1, "challenge": "pivot-v4-m.2-l.3-J.024-b.01-g9.81-w2-T10-stable-last1-5deg-dt.001-f.02-u2-iae-deg", "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert not ranking.records and "incompatible" in ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == old


def test_previous_v7_ten_second_challenge_is_archived(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1, "challenge": "pivot-v7-dcmotor-r2-l.16-k.333-v12-i6-coulomb.015-step4-8deg-w2-T10-dt.001-iae-deg", "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert not ranking.records and "incompatible" in ranking.warning
    backups = list(tmp_path.glob("ranking.json.backup-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == old


def test_previous_v8_eight_degree_challenge_is_archived(tmp_path):
    path = tmp_path / "ranking.json"
    old = {"schema": 1, "challenge": "pivot-v8-dcmotor-r2-l.16-k.333-v12-i6-coulomb.015-step5-8deg-w2-T15-dt.001-iae-deg", "records": []}
    path.write_text(json.dumps(old), encoding="utf-8")
    ranking = Ranking(path)
    assert ranking.records == [] and "incompatible" in ranking.warning
