import json

from aircontrol import settings


def test_defaults_and_first_run(tmp_path):
    s = settings.load(tmp_path / "x.json")
    assert s["mode"] == "relative" and s["first_run"] is True


def test_bad_values_fall_back_to_defaults(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"mode": "teleport", "region": [0.5, 0.5, 0.52, 0.9], "sound": "yes"}))
    s = settings.load(p)
    assert s["mode"] == "relative" and s["region"] == settings.DEFAULTS["region"] and s["sound"] is True


def test_save_keeps_user_bindings(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"bindings": {"tap_middle": "copy"}}))
    settings.save({"mode": "absolute", "region": [0.1, 0.1, 0.9, 0.9], "sound": False}, p)
    raw = json.loads(p.read_text())
    assert raw["bindings"] == {"tap_middle": "copy"} and raw["mode"] == "absolute"
    assert settings.load(p)["first_run"] is False
