"""Synthetic dataset consistency tests."""

from app.data.synthetic_generator import generate_synthetic_snapshot


def test_dataset_dimensions():
    snap = generate_synthetic_snapshot(seed=42)
    assert snap.metadata.item_count == 150
    assert snap.metadata.store_count == 4
    assert snap.metadata.category_count == 5
    assert len(snap.items) == 150
    assert len(snap.stores) == 4
    assert len(snap.balances) == 150 * 4


def test_reproducible_seed():
    a = generate_synthetic_snapshot(seed=42)
    b = generate_synthetic_snapshot(seed=42)
    assert a.balances[0].usable_qty == b.balances[0].usable_qty
    assert a.consumption[100].quantity == b.consumption[100].quantity
    assert len(a.batches) == len(b.batches)


def test_history_span():
    snap = generate_synthetic_snapshot(seed=42)
    assert (snap.metadata.history_end - snap.metadata.history_start).days == 364


def test_non_negative_stock():
    snap = generate_synthetic_snapshot(seed=42)
    assert all(b.usable_qty >= 0 for b in snap.balances)


def test_controlled_data_quality_edge_cases():
    snap = generate_synthetic_snapshot(seed=42)
    assert snap.metadata.missing_observation_count > 0
    assert snap.metadata.insufficient_history_item_count == 8
    assert snap.metadata.missing_observation_count < len(snap.consumption) * 0.05