import inspect

from app.analytics.loss_tree import extract_loss_tree


def test_extract_loss_tree_signature_excludes_ground_truth():
    # Firewall imza düzeyinde: çıkarım fonksiyonu ground_truth'u parametre olarak ALMAZ.
    params = inspect.signature(extract_loss_tree).parameters
    assert set(params) == {"events", "production", "line"}
    assert all("truth" not in name.lower() for name in params)
