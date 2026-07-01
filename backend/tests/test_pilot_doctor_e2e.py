"""Pilot doctor uçtan uca testleri: gerçek fixture'lar + geçici DuckDB.

`run_doctor` gerçek dosyalarla koşar; gerçek `oee.duckdb`'ye asla dokunmaz
(cwd'de DB kalıntısı testi). CLI (`main`) testleri exit kodu + stdout üstünden.
"""
import json

from tests.conftest import DIRTY, FIXTURES, LINE_CONFIG, RAW
from tools.pilot_doctor import FAIL, PASS, SKIP, main, run_doctor

BASELINE = FIXTURES / "baseline"


def _by_name(rep, name: str):
    return next(c for c in rep.checks if c.name == name)


# ---- run_doctor: mutlu yol -----------------------------------------------


def test_baseline_is_go():
    rep = run_doctor(BASELINE, LINE_CONFIG, adapter=None)
    assert rep.go() is True
    assert _by_name(rep, "oee").status == PASS
    assert _by_name(rep, "sufficiency").status == PASS
    assert _by_name(rep, "adapter").status == SKIP  # adapter verilmedi


def test_baseline_surfaces_ground_truth_skipped():
    rep = run_doctor(BASELINE, LINE_CONFIG, adapter=None)
    assert rep.ingest is not None
    assert rep.ingest["skipped"] == ["ground_truth.csv"]  # firewall görünür
    assert "ground_truth.csv" in _by_name(rep, "ingest").detail


# ---- run_doctor: kirli veri / eşikler --------------------------------------


def test_dirty_type_corruption_is_nogo():
    rep = run_doctor(DIRTY / "type_corruption", LINE_CONFIG, adapter=None)
    assert rep.go() is False
    rej = _by_name(rep, "rejection")
    assert rej.status == FAIL  # ~%9.6 > %5
    assert rej.value is not None and rej.value > 0.05


def test_max_reject_override_turns_go():
    rep = run_doctor(DIRTY / "type_corruption", LINE_CONFIG, adapter=None, max_reject=0.5)
    assert _by_name(rep, "rejection").status == PASS


def test_min_sufficiency_override_fails_baseline():
    rep = run_doctor(BASELINE, LINE_CONFIG, adapter=None, min_sufficiency=1.01)
    assert rep.go() is False
    assert _by_name(rep, "sufficiency").status == FAIL


# ---- run_doctor: hat tanımı kenar durumları --------------------------------


def test_invalid_line_yaml_is_nogo_but_ingest_runs(tmp_path):
    bad = tmp_path / "line.yaml"
    bad.write_text("line:\n  id: hat-1\ntanks: []\n", encoding="utf-8")
    rep = run_doctor(BASELINE, bad, adapter=None)
    assert rep.go() is False
    assert _by_name(rep, "line").status == FAIL
    assert _by_name(rep, "oee").status == SKIP  # hat yok -> hesaplanamaz
    assert _by_name(rep, "sufficiency").status == SKIP
    assert _by_name(rep, "ingest").status == PASS  # ingest hatta bagimli degil


def test_unreadable_line_yaml_is_nogo(tmp_path):
    bad = tmp_path / "line.yaml"
    bad.write_text(":: not yaml [", encoding="utf-8")
    rep = run_doctor(BASELINE, bad, adapter=None)  # exception yok
    assert rep.go() is False
    assert _by_name(rep, "line").status == FAIL


# ---- run_doctor: adaptör yolu (H2) ------------------------------------------


def test_adapter_raw_fixture_maps_and_ingests():
    # raw fixture kucuk (13 olay) -> yeterlilik dusuk; adaptor+ingest'i test ediyoruz
    rep = run_doctor(RAW, LINE_CONFIG, adapter="generic_plant", min_sufficiency=0.0)
    assert _by_name(rep, "adapter").status == PASS
    assert _by_name(rep, "ingest").status == PASS
    assert rep.ingest is not None and rep.ingest["accepted"].get("events", 0) > 0


def test_adapter_raw_default_sufficiency_is_nogo():
    rep = run_doctor(RAW, LINE_CONFIG, adapter="generic_plant")
    assert rep.go() is False
    assert _by_name(rep, "sufficiency").status == FAIL  # 13 olay ~0.4 < 0.6


def test_adapter_mapping_error_skips_downstream(tmp_path):
    # sozlesme-sekilli baseline'i HAM diye adaptorden gecir -> event_type eslenemez
    rep = run_doctor(BASELINE, LINE_CONFIG, adapter="generic_plant")
    assert _by_name(rep, "adapter").status == FAIL
    assert _by_name(rep, "ingest").status == SKIP
    assert _by_name(rep, "oee").status == SKIP
    assert _by_name(rep, "sufficiency").status == SKIP
    assert _by_name(rep, "rejection").status == SKIP
    assert rep.go() is False


# ---- run_doctor: boş veri / izolasyon --------------------------------------


def test_empty_data_dir_is_nogo_not_crash(tmp_path):
    empty = tmp_path / "bos"
    empty.mkdir()
    rep = run_doctor(empty, LINE_CONFIG, adapter=None)
    assert rep.go() is False
    assert _by_name(rep, "ingest").status == FAIL
    assert _by_name(rep, "rejection").status == FAIL  # "hic satir yok"
    assert _by_name(rep, "oee").status == SKIP  # veri yok -> hesap yok
    assert _by_name(rep, "sufficiency").status == SKIP


def test_no_db_files_left_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_doctor(BASELINE, LINE_CONFIG, adapter=None)
    assert list(tmp_path.glob("*.duckdb*")) == []  # gercek/kalinti DB yok


# ---- CLI main: exit kodları + çıktı -----------------------------------------


def test_main_baseline_is_exit_0_go(capsys):
    assert main([str(BASELINE)]) == 0
    out = capsys.readouterr().out
    assert "SONUC: GO" in out
    out.encode("ascii")  # cp1252 konsol guvenligi


def test_main_dirty_is_exit_1(capsys):
    assert main([str(DIRTY / "type_corruption")]) == 1
    assert "SONUC: NO-GO" in capsys.readouterr().out


def test_main_max_reject_override(capsys):
    assert main([str(DIRTY / "type_corruption"), "--max-reject", "0.5"]) == 0


def test_main_min_sufficiency_override(capsys):
    assert main([str(BASELINE), "--min-sufficiency", "1.01"]) == 1


def test_main_missing_data_dir_is_usage_error(tmp_path, capsys):
    assert main([str(tmp_path / "yok")]) == 2


def test_main_missing_line_file_is_usage_error(tmp_path, capsys):
    assert main([str(BASELINE), "--line", str(tmp_path / "yok.yaml")]) == 2


def test_main_unknown_adapter_is_usage_error(capsys):
    assert main([str(RAW), "--adapter", "yok_profil"]) == 2
    assert "yok_profil" in capsys.readouterr().err


def test_main_json_output_shape(capsys):
    assert main([str(BASELINE), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["go"] is True
    assert payload["exit_code"] == 0
    assert payload["thresholds"] == {"min_sufficiency": 0.6, "max_reject": 0.05}
    assert [c["name"] for c in payload["checks"]] == [
        "line", "adapter", "ingest", "oee", "sufficiency", "rejection",
    ]
    assert payload["ingest"]["skipped"] == ["ground_truth.csv"]
    assert 0.0 < payload["oee"]["oee"] <= 1.0
    assert payload["adapter"] is None
    assert payload["data_dir"] == str(BASELINE)


def test_main_json_nogo_consistent(capsys):
    assert main([str(DIRTY / "type_corruption"), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["go"] is False
    assert payload["exit_code"] == 1
