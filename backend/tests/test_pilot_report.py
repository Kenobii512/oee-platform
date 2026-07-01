"""Pilot rapor aracı testleri: veri çekirdeği (build_report_data) + HTML render + CLI.

Rapor karar VERMEZ (doctor'ın işi); belgeler — eşik ihlali ✗ olarak görünür.
Veri çekirdeği saf dict üretir (HTML bilmez); render veri kaynağını bilmez.
"""
import pytest

from app.config import load_line_definition
from tests.conftest import FIXTURES, LINE_CONFIG, RAW
from tools.pilot_report import build_report_data, main, render_html

SCENARIOS = FIXTURES / "scenarios"
STORM = SCENARIOS / "breakdown_storm"


@pytest.fixture(scope="module")
def line_def_m():
    return load_line_definition(LINE_CONFIG)


@pytest.fixture(scope="module")
def storm_data(line_def_m):
    return build_report_data(STORM, line_def_m)


# ---- build_report_data: mutlu yol (golden senaryo) ---------------------------


def test_storm_has_data_and_oee(storm_data):
    assert storm_data["has_data"] is True
    oee = storm_data["oee"]
    assert oee is not None
    assert 0.0 < oee["oee"] <= 1.0


def test_storm_losses_tl_descending_with_bands(storm_data):
    cats = storm_data["losses"]["categories"]
    assert cats[0]["category"] == "DOWNTIME"  # senaryonun adlı baskın kaybı
    tls = [c["tl"] for c in cats]
    assert tls == sorted(tls, reverse=True)
    for c in cats:
        assert {"tl_low", "tl_high", "kind", "confidence"} <= set(c)
    assert storm_data["losses"]["total_tl"] > 0


def test_storm_recommendations_have_ranges(storm_data):
    recs = storm_data["recommendations"]
    assert recs["total_gain_tl"] > 0
    top = recs["items"][0]
    assert 0 < top["estimated_gain_tl_low"] <= top["estimated_gain_tl_high"]


def test_storm_trend_and_quality(storm_data):
    assert len(storm_data["trend"]) >= 1
    q = storm_data["quality"]
    assert q["event_count"] > 0
    assert q["sufficiency"] > 0.0
    assert q["reject_rate"] == 0.0  # temiz golden fixture


def test_storm_criteria_auto_evaluation(storm_data):
    crit = storm_data["criteria"]
    for key in ("k1", "k2", "k3"):
        assert isinstance(crit[key]["auto_pass"], bool)
        assert crit[key]["detail"]  # gerekçe metni boş değil
    assert crit["k2"]["auto_pass"] is True  # total_gain > 0 + low > 0
    assert crit["k3"]["auto_pass"] is True  # red 0 <= %5, H3 yeterli


# ---- build_report_data: kenarlar ---------------------------------------------


def test_empty_dir_report_still_builds(tmp_path, line_def_m):
    empty = tmp_path / "bos"
    empty.mkdir()
    data = build_report_data(empty, line_def_m)
    assert data["has_data"] is False
    assert data["oee"] is None
    assert data["losses"] is None
    assert data["trend"] == []
    # Değerlendirilemedi (None) — sahte ✓/✗ yok.
    assert data["criteria"]["k1"]["auto_pass"] is None


def test_adapter_raw_report_data(line_def_m):
    data = build_report_data(RAW, line_def_m, adapter="generic_plant")
    assert data["has_data"] is True
    assert data["quality"]["accepted"].get("events", 0) > 0


# ---- render_html: kendine-yeten tek dosya ------------------------------------


@pytest.fixture(scope="module")
def storm_html(storm_data):
    data = dict(storm_data)
    data["meta"] = {**storm_data["meta"], "generated_at": "2026-07-02 12:00"}
    return render_html(data)


def test_render_is_self_contained(storm_html):
    assert storm_html.lstrip().lower().startswith("<!doctype html")
    # Harici istek yok: CDN/font/stylesheet/script kaynağı bulunmaz.
    assert "http://" not in storm_html
    assert "https://" not in storm_html
    assert "<link" not in storm_html
    assert "@import" not in storm_html
    assert "<script" not in storm_html


def test_render_has_faz3_sections(storm_html):
    for text in (
        "Pilot Raporu",
        "OEE",
        "En büyük kayıplar",
        "TL fırsatı",
        "Güven notu",
        "Başarı kriterleri",
        "üst sınır",  # önerilerin örtüşme çekincesi
    ):
        assert text in storm_html, text


def test_render_criteria_marks_and_fillables(storm_html):
    # Otomatik kısımlar isaretli, insan alanları boş.
    assert "✓" in storm_html
    assert "☐ GO" in storm_html and "☐ İyileştir" in storm_html and "☐ Durdur" in storm_html
    assert "____" in storm_html  # elle doldurulacak alan


def test_render_pareto_bars_and_turkish_labels(storm_html):
    assert storm_html.count('class="bar"') == 5  # 5 kayıp kategorisi
    assert "Duruş" in storm_html  # catLabel karşılığı (ham kod değil)
    assert "₺" in storm_html  # para standardı


def test_render_trend_needs_history_note(storm_data):
    data = dict(storm_data)
    data["meta"] = {**storm_data["meta"], "generated_at": "x"}
    data["trend"] = storm_data["trend"][:2]  # <3 nokta
    html_out = render_html(data)
    assert "yeterli geçmiş yok" in html_out


def test_render_escapes_untrusted_text(storm_data):
    data = dict(storm_data)
    data["meta"] = {**storm_data["meta"], "line_name": "<script>alert(1)</script>",
                    "generated_at": "x"}
    html_out = render_html(data)
    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;" in html_out


def test_render_empty_data_shows_placeholder(tmp_path, line_def_m):
    empty = tmp_path / "bos"
    empty.mkdir()
    data = build_report_data(empty, line_def_m)
    data["meta"] = {**data["meta"], "generated_at": "x"}
    html_out = render_html(data)
    assert "veri yok" in html_out  # çökme yok, bölümler işaretli


# ---- CLI main ------------------------------------------------------------


def test_main_writes_report_file(tmp_path, capsys):
    out = tmp_path / "rapor.html"
    assert main([str(STORM), "-o", str(out)]) == 0
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Pilot Raporu" in text
    capsys.readouterr().out.encode("ascii")  # konsol mesaji ASCII


def test_main_deterministic_with_generated_at(tmp_path):
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    args = [str(STORM), "--generated-at", "2026-07-02 12:00"]
    assert main([*args, "-o", str(a)]) == 0
    assert main([*args, "-o", str(b)]) == 0
    assert a.read_bytes() == b.read_bytes()  # bayt-es tekrar uretilebilir


def test_main_missing_dir_is_usage_error(tmp_path, capsys):
    assert main([str(tmp_path / "yok")]) == 2
    err = capsys.readouterr().err
    err.encode("ascii")
    assert "HATA" in err


def test_main_unknown_adapter_is_usage_error(capsys):
    assert main([str(STORM), "--adapter", "yok_profil"]) == 2


def test_main_bad_date_is_usage_error(capsys):
    assert main([str(STORM), "--from", "31-02-2026"]) == 2
