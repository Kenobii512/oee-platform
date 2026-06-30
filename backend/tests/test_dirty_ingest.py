"""H1 — kirli-veri ingest dayanıklılığı.

Her kirlilik türünde: sağlam satır yüklenir, bozuk satır LoadReport'a raporlanır,
sistem ÇÖKMEZ. Ham-CSV/encoding hataları da satır/dosya bazında zarifçe ele alınır.
"""
from app.ingest.loader import load_csv_dir
from tests.conftest import fresh_repo

_EVENTS_HEADER = (
    "timestamp,line_id,carrier_id,station_id,event_type,duration,"
    "reason_code,operator_entered_reason,operator_entry_ts\n"
)
_GOOD_EVENT = "2026-01-01 00:00:00.000,LINE-01,CAR-1,,MICROSTOP,30,jam,,\n"


def _write_events(tmp_path, body: str):
    d = tmp_path / "data"
    d.mkdir()
    (d / "events.csv").write_text(_EVENTS_HEADER + body, encoding="utf-8")
    return d


def test_type_corruption_rejected_good_loaded(tmp_path):
    body = _GOOD_EVENT + "2026-01-01 00:01:00.000,LINE-01,CAR-2,,MICROSTOP,NOTANUMBER,jam,,\n"
    d = _write_events(tmp_path, body)
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    rep = load_csv_dir(d, repo).to_dict()
    assert repo.count("events") == 1
    assert rep["rejected_count"] == 1
    repo.close()


def test_negative_duration_rejected(tmp_path):
    body = _GOOD_EVENT + "2026-01-01 00:02:00.000,LINE-01,CAR-3,,MICROSTOP,-99,jam,,\n"
    d = _write_events(tmp_path, body)
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    rep = load_csv_dir(d, repo).to_dict()
    assert repo.count("events") == 1  # negatif duration reddedildi
    assert rep["rejected_count"] == 1
    repo.close()


def test_nul_byte_does_not_crash(tmp_path):
    # CSV içinde NUL baytı -> csv.Error; dosya bazında reddedilmeli, çökmemeli.
    d = tmp_path / "data"
    d.mkdir()
    (d / "events.csv").write_bytes(
        _EVENTS_HEADER.encode() + b"2026-01-01 00:00:00.000,LINE-01,CAR-1,,MICRO\x00STOP,30,jam,,\n"
    )
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    rep = load_csv_dir(d, repo).to_dict()  # çökmez
    assert rep["rejected_count"] >= 1
    repo.close()


def test_bad_encoding_does_not_crash(tmp_path):
    # Geçersiz UTF-8 baytları -> eskiden UnicodeDecodeError ile çökerdi.
    d = tmp_path / "data"
    d.mkdir()
    bad = _EVENTS_HEADER.encode() + b"2026-01-01 00:00:00.000,L\xff\xfeNE,CAR-1,,MICROSTOP,30,jam,,\n"
    (d / "events.csv").write_bytes(bad)
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    rep = load_csv_dir(d, repo)  # çökmez (utf-8-sig + errors=replace)
    assert rep.to_dict()["accepted"].get("events", 0) >= 1  # satır yüklendi (bozuk karakter değiştirildi)
    repo.close()


def test_disposition_violation_rejected(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "production.csv").write_text(
        "carrier_id,order_id,loaded_qty,good_count,redo_count,scrap_count\n"
        "CAR-1,ORD-1,100,100,0,0\n"
        "CAR-2,ORD-1,100,90,0,5\n",  # 90+5 != 100
        encoding="utf-8",
    )
    repo = fresh_repo(str(tmp_path / "t.duckdb"))
    rep = load_csv_dir(d, repo).to_dict()
    assert repo.count("production") == 1
    assert rep["rejected_count"] == 1
    repo.close()
