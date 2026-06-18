from app.analytics.recommend import RatioGainEstimator, generate_recommendations
from app.config import CategoryRule, RecommendConfig

RC = RecommendConfig(
    default_recovery_ratio=0.2,
    recovery_low_factor=0.5,
    recovery_high_factor=1.0,
    rules={
        "DOWNTIME": CategoryRule(0.30, "Duruşları azalt", "neden {detail}", "~%{pct} geri kazanım"),
        "MICROSTOP": CategoryRule(0.20, "Mikro", "yoğun {detail}", "~%{pct}"),
        "SPEED_LOSS": CategoryRule(0.15, "Hız", "standardize et", "~%{pct}"),
        "FILL_LOSS": CategoryRule(0.20, "Doluluk", "artır", "~%{pct}"),
        "QUALITY_REDO": CategoryRule(0.25, "Redo", "kontrol", "~%{pct}"),
    },
)

COST = {
    "categories": [
        {"category": "DOWNTIME", "axis": "minutes", "value": 230.0, "tl": 11500.0, "kind": "visible"},
        {"category": "MICROSTOP", "axis": "minutes", "value": 60.0, "tl": 3000.0, "kind": "visible"},
        {"category": "SPEED_LOSS", "axis": "minutes", "value": 100.0, "tl": 2000.0, "kind": "inferred"},
        {"category": "FILL_LOSS", "axis": "parts", "value": 700.0, "tl": 1400.0, "kind": "inferred"},
        {"category": "QUALITY_REDO", "axis": "parts", "value": 60.0, "tl": 180.0, "kind": "visible"},
    ],
    "total_tl": 18080.0,
}

EVENTS = [
    {"event_type": "DOWNTIME", "duration": 100.0, "reason_code": "ariza_pompa", "station_id": "T3"},
    {"event_type": "DOWNTIME", "duration": 60.0, "reason_code": "ariza_pompa", "station_id": "T3"},
    {"event_type": "DOWNTIME", "duration": 70.0, "reason_code": "kalip_degisim", "station_id": "T1"},
    {"event_type": "MICROSTOP", "duration": 30.0, "reason_code": None, "station_id": "T2"},
    {"event_type": "MICROSTOP", "duration": 30.0, "reason_code": None, "station_id": "T2"},
]


def test_every_recommendation_has_required_fields():
    recs = generate_recommendations(COST, EVENTS, RC, RatioGainEstimator(RC))
    assert recs, "öneri üretilmedi"
    for r in recs:
        assert r["category"]
        assert r["tl"] > 0
        assert r["estimated_gain_tl"] >= 0
        assert r["title"]
        assert r["action"]
        assert r["assumption"]


def test_gain_is_tl_times_recovery_ratio():
    recs = generate_recommendations(COST, EVENTS, RC, RatioGainEstimator(RC))
    by = {r["category"]: r for r in recs}
    assert abs(by["DOWNTIME"]["estimated_gain_tl"] - 11500.0 * 0.30) < 1e-6
    assert abs(by["SPEED_LOSS"]["estimated_gain_tl"] - 2000.0 * 0.15) < 1e-6


def test_gain_has_range_around_point_estimate():
    # Perf-UI: nokta tahmin üst sınır; alt sınır = nokta × low_factor (abartılı kesinlik yok).
    recs = generate_recommendations(COST, EVENTS, RC, RatioGainEstimator(RC))
    for r in recs:
        assert r["estimated_gain_tl_high"] == r["estimated_gain_tl"]
        assert abs(r["estimated_gain_tl_low"] - r["estimated_gain_tl"] * 0.5) < 1e-6
        assert r["estimated_gain_tl_low"] <= r["estimated_gain_tl_high"]


def test_downtime_detail_embeds_top_reason():
    recs = generate_recommendations(COST, EVENTS, RC, RatioGainEstimator(RC))
    by = {r["category"]: r for r in recs}
    # En çok dakikayı tüketen neden: ariza_pompa (160 dk).
    assert "ariza_pompa" in by["DOWNTIME"]["action"]


def test_no_guarantee_language():
    recs = generate_recommendations(COST, EVENTS, RC, RatioGainEstimator(RC))
    banned = ("garanti", "kesin", "kesinlikle")
    for r in recs:
        text = (r["action"] + " " + r["assumption"]).lower()
        assert not any(b in text for b in banned), r
