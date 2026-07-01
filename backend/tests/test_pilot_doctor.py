"""Pilot doctor saf kontrol çekirdeği birim testleri (DB'siz, dosyasız).

`tools.pilot_doctor` saf fonksiyonları: her kontrol PASS/FAIL/SKIP + eyleme dönük
detay üretir; GO = hiç FAIL yok (SKIP nötr). Red oranı LoadReport'un TAM
`rejected` listesinden hesaplanır (to_dict'in 50'de kırpılan `errors`'ından DEĞİL).
"""
from app.analytics.oee import OeeResult
from app.ingest.report import LoadReport
from tools.pilot_doctor import (
    FAIL,
    PASS,
    SKIP,
    CheckResult,
    DoctorReport,
    check_ingest,
    check_line,
    check_oee,
    check_rejection,
    check_sufficiency,
    decide,
    format_report,
    rejection_rate,
)

# ---- check_line ----------------------------------------------------------

_VALID_LINE = {
    "line": {"id": "hat-1"},
    "tanks": [{"id": "T1", "time_min": 1, "time_max": 2, "bottleneck": True}],
}


def test_check_line_valid_passes():
    res = check_line(_VALID_LINE)
    assert res.name == "line"
    assert res.status == PASS


def test_check_line_invalid_lists_errors():
    res = check_line({"line": {}, "tanks": []})
    assert res.status == FAIL
    assert "tanks" in res.detail  # doğrulayıcı mesajı detayda görünür


def test_check_line_non_dict_fails():
    assert check_line(None).status == FAIL
    assert check_line("yanlis").status == FAIL


# ---- check_oee -----------------------------------------------------------


def _oee(value: float) -> OeeResult:
    return OeeResult(0.8, 0.9, 0.9, value, 0.5, 0.0, 1.0)


def test_check_oee_zero_fails():
    res = check_oee(OeeResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    assert res.status == FAIL


def test_check_oee_in_range_passes():
    assert check_oee(_oee(0.6)).status == PASS
    assert check_oee(_oee(1.0)).status == PASS  # sınır dahil


def test_check_oee_detail_has_components():
    res = check_oee(_oee(0.6))
    # FAIL teşhis edilebilir olsun diye A/P/Q bileşenleri detayda
    assert "A=" in res.detail and "P=" in res.detail and "Q=" in res.detail


# ---- check_sufficiency ---------------------------------------------------


def test_check_sufficiency_threshold_boundary():
    assert check_sufficiency(0.59, 0.6).status == FAIL
    assert check_sufficiency(0.6, 0.6).status == PASS


def test_check_sufficiency_records_value_and_threshold():
    res = check_sufficiency(0.42, 0.6)
    assert res.value == 0.42
    assert res.threshold == 0.6


# ---- rejection -----------------------------------------------------------


def test_rejection_rate_no_rows_is_none():
    assert rejection_rate({}, 0) is None


def test_check_rejection_empty_report_fails_without_crash():
    res = check_rejection(LoadReport(), 0.05)  # hic satir yok -> ZeroDivision YOK
    assert res.status == FAIL


def test_check_rejection_over_and_under():
    over = LoadReport(accepted={"events": 94})
    for i in range(6):
        over.add_rejection("events.csv", i, "bozuk")
    assert check_rejection(over, 0.05).status == FAIL  # 6/100 > %5

    under = LoadReport(accepted={"events": 95})
    for i in range(5):
        under.add_rejection("events.csv", i, "bozuk")
    assert check_rejection(under, 0.05).status == PASS  # 5/100 == %5 (sınır dahil)


def test_rejection_uses_full_rejected_list_not_truncated_errors():
    # to_dict()["errors"] 50'de kırpılır; oran TAM listeden gelmeli (60/100)
    rep = LoadReport(accepted={"events": 40})
    for i in range(60):
        rep.add_rejection("events.csv", i, "bozuk")
    res = check_rejection(rep, 0.05)
    assert res.status == FAIL
    assert res.value == 0.6


# ---- check_ingest --------------------------------------------------------


def test_check_ingest_accepts_rows_and_surfaces_skipped():
    rep = LoadReport(accepted={"events": 10, "production": 3}, skipped=["ground_truth.csv"])
    res = check_ingest(rep)
    assert res.status == PASS
    assert "ground_truth.csv" in res.detail  # firewall kanıtı görünür


def test_check_ingest_zero_rows_fails():
    assert check_ingest(LoadReport()).status == FAIL


# ---- decide / rapor ------------------------------------------------------


def _c(name: str, status: str) -> CheckResult:
    return CheckResult(name=name, status=status, detail="x")


def test_decide_skip_is_neutral():
    assert decide([_c("line", PASS), _c("adapter", SKIP)]) is True
    assert decide([_c("line", PASS), _c("oee", FAIL)]) is False


def test_doctor_report_go_and_to_dict():
    rep = DoctorReport(checks=[_c("line", PASS)], ingest=None, oee=None)
    assert rep.go() is True
    d = rep.to_dict()
    assert d["go"] is True
    assert d["checks"][0]["name"] == "line"


def test_format_report_is_ascii():
    # Türkçe detaylar (doğrulayıcı mesajları) ASCII'ye katlanır — cp1252 konsolu patlamaz
    rep = DoctorReport(
        checks=[
            CheckResult(name="line", status=FAIL, detail="tanks boş olamaz; şu ğüıçö İIĞÜŞÇÖ"),
            _c("rejection", PASS),
        ],
        ingest={"accepted": {"events": 1}, "rejected_count": 0, "skipped": [], "errors": []},
        oee=None,
    )
    text = format_report(rep, data_dir="veri", line_path="hat.yaml", adapter=None)
    text.encode("ascii")  # raise etmemeli
    assert "SONUC: NO-GO" in text


def test_format_report_go_line():
    rep = DoctorReport(checks=[_c("line", PASS)], ingest=None, oee=None)
    text = format_report(rep, data_dir="veri", line_path="hat.yaml", adapter=None)
    assert "SONUC: GO" in text
