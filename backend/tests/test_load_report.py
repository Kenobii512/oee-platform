from app.ingest.report import LoadReport


def test_report_accumulates_counts():
    rep = LoadReport()
    rep.accepted["events"] = 10
    rep.rejected.append({"file": "production.csv", "row": 3, "error": "bad"})
    rep.skipped.append("ground_truth.csv")
    d = rep.to_dict()
    assert d["accepted"]["events"] == 10
    assert d["rejected_count"] == 1
    assert d["skipped"] == ["ground_truth.csv"]
    assert d["errors"][0]["row"] == 3


def test_report_caps_error_list():
    rep = LoadReport(max_errors=2)
    for i in range(5):
        rep.add_rejection("f.csv", i, "e")
    assert rep.to_dict()["rejected_count"] == 5  # full count kept
    assert len(rep.to_dict()["errors"]) == 2     # but only first 2 surfaced
