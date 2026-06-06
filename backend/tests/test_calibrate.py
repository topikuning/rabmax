"""Unit tests Stage 5 calibrator (Known Issue #11: audit trail)."""

from app.services.calibrator.calibrate import CalibrationItem, calibrate


def test_calibrate_hits_target():
    items = [
        CalibrationItem(item_id=1, volume=10.0, base_hsp=100.0),  # 1000
        CalibrationItem(item_id=2, volume=5.0, base_hsp=200.0),  # 1000
    ]
    res = calibrate(items, target_value=3000.0)  # base 2000 -> ×1.5
    assert res.multiplier == 1.5
    assert abs(res.calibrated_total - 3000.0) < 0.01
    assert res.items[0].calibrated_hsp == 150.0
    assert "target-calibrated" in res.items[0].audit_label


def test_no_target_passthrough():
    items = [CalibrationItem(1, 1.0, 100.0)]
    res = calibrate(items, target_value=0.0)
    assert res.multiplier == 1.0
    assert res.items[0].calibrated_hsp == 100.0
    assert res.items[0].audit_label == ""


def test_multiplier_clamped_guardrail():
    items = [CalibrationItem(1, 1.0, 100.0)]  # base 100
    res = calibrate(items, target_value=1000.0)  # ×10 -> clamp ke 2.0
    assert res.clamped
    assert res.multiplier == 2.0
    assert any("guard rail" in w for w in res.warnings)


def test_band_check_warns_outside_lkpp():
    items = [CalibrationItem(1, 1.0, 100.0)]
    # target 150% HPS -> di luar band 80-120%
    res = calibrate(items, target_value=120.0, hps_total=80.0)
    assert any("band LKPP" in w for w in res.warnings)


def test_zero_base_total_warns():
    items = [CalibrationItem(1, 1.0, 0.0)]
    res = calibrate(items, target_value=1000.0)
    assert res.multiplier == 1.0
    assert any("Base total = 0" in w for w in res.warnings)
