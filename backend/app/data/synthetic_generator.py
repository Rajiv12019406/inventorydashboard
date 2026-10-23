"""Deterministic synthetic hospital inventory dataset generator.

Assumptions (documented for demo transparency):
- Fixed random seed for reproducibility
- 150 items across 5 categories and 4 stores
- 365 days of daily consumption ending at a fixed "today"
- Current stock derived from opening stock + receipts − cumulative consumption
- Batches assigned with FEFO-relevant expiry dates
- Controlled data-quality edge cases (~3% missing days, ~8 items with short history)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Sequence

import numpy as np

from app.data.models import (
    BatchLot,
    Category,
    ConsumptionRecord,
    DatasetMetadata,
    DemandPattern,
    IncomingReceipt,
    InventoryItem,
    InventorySnapshot,
    StockBalance,
    Store,
)

ASSUMPTIONS = [
    "Fixed seed=42 for reproducible generation",
    "4 fictional hospital stores / pharmacies",
    "5 clinical supply categories",
    "150 SKUs with distinct demand patterns",
    "365-day daily consumption history",
    "Opening stock calibrated so ending balances remain non-negative for most SKUs",
    "Incoming receipts scheduled within the next 14 days for ~25% of item-store pairs",
    "~3% of consumption observations intentionally missing",
    "~8 item-store series truncated to <30 days (insufficient history)",
    "All names, codes, and locations are fictional — DEMO MODE only",
]

STORES = [
    Store("ST-MAIN", "Main Campus Pharmacy", "Building A — Central Supply"),
    Store("ST-ER", "Emergency Department Store", "Building B — ED Wing"),
    Store("ST-OR", "Surgical Suite Inventory", "Building C — OR Level 2"),
    Store("ST-ICU", "ICU Satellite Pharmacy", "Building A — ICU Floor 4"),
]

CATEGORIES = [
    Category("CAT-MED", "Medications"),
    Category("CAT-IV", "IV Fluids & Solutions"),
    Category("CAT-SURG", "Surgical Supplies"),
    Category("CAT-PPE", "PPE & Infection Control"),
    Category("CAT-DIAG", "Diagnostics & Labs"),
]

# (base_name, unit, category_id, typical_daily_mean, lead_days, min_stock_mult, safety_mult)
ITEM_TEMPLATES: list[tuple[str, str, str, float, int, float, float]] = [
    ("Amoxicillin 500mg Capsules", "caps", "CAT-MED", 42, 7, 5, 3),
    ("Ibuprofen 400mg Tablets", "tabs", "CAT-MED", 55, 5, 5, 3),
    ("Paracetamol 500mg Tablets", "tabs", "CAT-MED", 80, 5, 5, 3),
    ("Metformin 500mg Tablets", "tabs", "CAT-MED", 35, 7, 5, 3),
    ("Atorvastatin 20mg Tablets", "tabs", "CAT-MED", 28, 7, 5, 3),
    ("Omeprazole 20mg Capsules", "caps", "CAT-MED", 30, 7, 5, 3),
    ("Amlodipine 5mg Tablets", "tabs", "CAT-MED", 22, 7, 5, 3),
    ("Losartan 50mg Tablets", "tabs", "CAT-MED", 18, 7, 5, 3),
    ("Ceftriaxone 1g Vial", "vials", "CAT-MED", 12, 10, 7, 4),
    ("Morphine 10mg/ml Ampoule", "amps", "CAT-MED", 8, 10, 7, 4),
    ("Insulin Glargine 100U/ml", "pens", "CAT-MED", 6, 14, 10, 5),
    ("Heparin 5000IU Vial", "vials", "CAT-MED", 10, 10, 7, 4),
    ("Warfarin 5mg Tablets", "tabs", "CAT-MED", 14, 7, 5, 3),
    ("Furosemide 40mg Tablets", "tabs", "CAT-MED", 20, 7, 5, 3),
    ("Dexamethasone 4mg Tablets", "tabs", "CAT-MED", 16, 7, 5, 3),
    ("Azithromycin 250mg Tablets", "tabs", "CAT-MED", 24, 7, 5, 3),
    ("Levothyroxine 50mcg Tablets", "tabs", "CAT-MED", 19, 7, 5, 3),
    ("Sertraline 50mg Tablets", "tabs", "CAT-MED", 15, 7, 5, 3),
    ("Salbutamol Inhaler 100mcg", "units", "CAT-MED", 11, 10, 7, 4),
    ("Prednisolone 5mg Tablets", "tabs", "CAT-MED", 17, 7, 5, 3),
    ("Normal Saline 0.9% 1L", "bags", "CAT-IV", 95, 5, 4, 2),
    ("Lactated Ringer's 1L", "bags", "CAT-IV", 60, 5, 4, 2),
    ("Dextrose 5% 1L", "bags", "CAT-IV", 45, 5, 4, 2),
    ("Dextrose 10% 500ml", "bags", "CAT-IV", 18, 7, 5, 3),
    ("Potassium Chloride 20mEq", "bags", "CAT-IV", 25, 7, 5, 3),
    ("Sodium Bicarbonate 8.4%", "vials", "CAT-IV", 8, 10, 7, 4),
    ("Sterile Water for Injection 10ml", "vials", "CAT-IV", 40, 5, 4, 2),
    ("Plasma-Lyte 1L", "bags", "CAT-IV", 22, 7, 5, 3),
    ("Mannitol 20% 500ml", "bags", "CAT-IV", 5, 14, 10, 5),
    ("Albumin 25% 50ml", "vials", "CAT-IV", 4, 14, 10, 5),
    ("Surgical Gloves Size M", "pairs", "CAT-SURG", 220, 7, 4, 2),
    ("Surgical Gloves Size L", "pairs", "CAT-SURG", 180, 7, 4, 2),
    ("Sterile Gauze Pads 4x4", "packs", "CAT-SURG", 75, 5, 4, 2),
    ("Suture Vicryl 3-0", "packs", "CAT-SURG", 28, 10, 6, 3),
    ("Suture Prolene 4-0", "packs", "CAT-SURG", 18, 10, 6, 3),
    ("Scalpel Blade #10", "pcs", "CAT-SURG", 35, 7, 5, 3),
    ("Scalpel Blade #15", "pcs", "CAT-SURG", 30, 7, 5, 3),
    ("Disposable Syringe 5ml", "pcs", "CAT-SURG", 150, 5, 4, 2),
    ("Disposable Syringe 10ml", "pcs", "CAT-SURG", 120, 5, 4, 2),
    ("IV Cannula 18G", "pcs", "CAT-SURG", 55, 7, 5, 3),
    ("IV Cannula 20G", "pcs", "CAT-SURG", 70, 7, 5, 3),
    ("Surgical Mask Type IIR", "pcs", "CAT-PPE", 400, 5, 3, 2),
    ("N95 Respirator", "pcs", "CAT-PPE", 90, 10, 5, 3),
    ("Isolation Gown", "pcs", "CAT-PPE", 85, 7, 4, 2),
    ("Face Shield", "pcs", "CAT-PPE", 40, 7, 5, 3),
    ("Alcohol Hand Rub 500ml", "bottles", "CAT-PPE", 65, 5, 4, 2),
    ("Surface Disinfectant Wipes", "canisters", "CAT-PPE", 35, 7, 5, 3),
    ("Examination Gloves Latex-Free M", "boxes", "CAT-PPE", 55, 5, 4, 2),
    ("Blood Collection Tubes EDTA", "tubes", "CAT-DIAG", 110, 7, 4, 2),
    ("Blood Collection Tubes SST", "tubes", "CAT-DIAG", 95, 7, 4, 2),
    ("Urine Collection Cups", "pcs", "CAT-DIAG", 60, 5, 4, 2),
    ("Glucose Test Strips", "boxes", "CAT-DIAG", 25, 10, 6, 3),
    ("Rapid Strep Test Kit", "kits", "CAT-DIAG", 12, 14, 8, 4),
    ("COVID Antigen Test Kit", "kits", "CAT-DIAG", 30, 10, 6, 3),
    ("Culture Swabs Sterile", "pcs", "CAT-DIAG", 45, 7, 5, 3),
    ("Lancet Safety 28G", "pcs", "CAT-DIAG", 80, 7, 4, 2),
    ("Pregnancy Test Cassette", "kits", "CAT-DIAG", 8, 14, 8, 4),
    ("HbA1c Cartridge", "pcs", "CAT-DIAG", 14, 14, 8, 4),
    ("Blood Gas Syringe Kit", "kits", "CAT-DIAG", 20, 10, 6, 3),
    ("Coagulation Reagent PT", "vials", "CAT-DIAG", 10, 14, 8, 4),
]


def _fix_name(base: str, variant: int) -> str:
    if variant == 0:
        return base
    suffixes = ["— Pack A", "— Pack B", "— Bulk", "— Unit Dose", "— Ward Pack"]
    return f"{base} {suffixes[(variant - 1) % len(suffixes)]}"


def _build_items(rng: np.random.Generator) -> list[InventoryItem]:
    patterns: Sequence[DemandPattern] = (
        "stable",
        "increasing",
        "decreasing",
        "weekly_seasonal",
        "spike",
        "intermittent",
        "zero_periods",
    )
    items: list[InventoryItem] = []
    idx = 0
    while len(items) < 150:
        base_name, unit, cat_id, mean, lead, min_m, safe_m = ITEM_TEMPLATES[idx % len(ITEM_TEMPLATES)]
        variant = idx // len(ITEM_TEMPLATES)
        name = _fix_name(base_name, variant)
        pattern = patterns[idx % len(patterns)]
        # Slight mean variation per variant
        adj_mean = max(1.0, mean * (0.7 + 0.6 * rng.random()))
        item_id = f"ITM-{idx + 1:03d}"
        items.append(
            InventoryItem(
                item_id=item_id,
                item_code=f"MS-{cat_id.split('-')[1]}-{idx + 1:04d}",
                name=name,
                category_id=cat_id,
                unit=unit,
                min_stock=round(adj_mean * min_m, 1),
                safety_stock=round(adj_mean * safe_m, 1),
                supplier_lead_time_days=int(lead),
                demand_pattern=pattern,
            )
        )
        idx += 1
    return items


def _generate_series(
    rng: np.random.Generator,
    days: int,
    base_mean: float,
    pattern: DemandPattern,
    store_factor: float,
) -> np.ndarray:
    t = np.arange(days, dtype=float)
    mean = base_mean * store_factor

    if pattern == "stable":
        series = rng.poisson(lam=max(0.5, mean), size=days).astype(float)
    elif pattern == "increasing":
        trend = mean * (0.75 + 0.5 * (t / max(days - 1, 1)))
        series = rng.poisson(lam=np.maximum(0.5, trend), size=days).astype(float)
    elif pattern == "decreasing":
        trend = mean * (1.25 - 0.5 * (t / max(days - 1, 1)))
        series = rng.poisson(lam=np.maximum(0.5, trend), size=days).astype(float)
    elif pattern == "weekly_seasonal":
        dow = t % 7
        seasonal = 1.0 + 0.35 * np.sin(2 * np.pi * dow / 7)
        # Weekends lower for elective-ish categories
        seasonal = np.where(dow >= 5, seasonal * 0.65, seasonal)
        series = rng.poisson(lam=np.maximum(0.5, mean * seasonal), size=days).astype(float)
    elif pattern == "spike":
        series = rng.poisson(lam=max(0.5, mean), size=days).astype(float)
        n_spikes = int(rng.integers(3, 8))
        spike_days = rng.choice(days, size=n_spikes, replace=False)
        series[spike_days] *= rng.uniform(2.5, 4.5, size=n_spikes)
    elif pattern == "intermittent":
        series = np.zeros(days, dtype=float)
        active = rng.random(days) < 0.35
        series[active] = rng.poisson(lam=max(1.0, mean * 1.8), size=active.sum()).astype(float)
    else:  # zero_periods
        series = rng.poisson(lam=max(0.5, mean), size=days).astype(float)
        # Carve out 2–3 zero windows of 5–12 days
        for _ in range(int(rng.integers(2, 4))):
            start = int(rng.integers(0, max(1, days - 12)))
            length = int(rng.integers(5, 13))
            series[start : start + length] = 0.0

    return np.round(series, 1)


def generate_synthetic_snapshot(seed: int = 42) -> InventorySnapshot:
    rng = np.random.default_rng(seed)
    today = date(2026, 10, 22)  # fixed "as-of" for determinism
    history_start = today - timedelta(days=364)
    days = 365
    dates = [history_start + timedelta(days=i) for i in range(days)]

    items = _build_items(rng)
    store_factors = {
        "ST-MAIN": 1.15,
        "ST-ER": 1.35,
        "ST-OR": 0.85,
        "ST-ICU": 1.05,
    }

    # Mean demand lookup from templates (approximate via name root)
    template_means = {t[0]: t[3] for t in ITEM_TEMPLATES}

    consumption: list[ConsumptionRecord] = []
    balances: list[StockBalance] = []
    batches: list[BatchLot] = []
    incoming: list[IncomingReceipt] = []
    missing_count = 0
    insufficient_pairs: set[tuple[str, str]] = set()

    # Pre-select insufficient-history item-store pairs (~8)
    all_pairs = [(it.item_id, st.store_id) for it in items for st in STORES]
    insuff_idx = rng.choice(len(all_pairs), size=8, replace=False)
    for i in insuff_idx:
        insufficient_pairs.add(all_pairs[int(i)])

    batch_seq = 0
    receipt_seq = 0

    for item in items:
        root = item.name.split(" — ")[0]
        base_mean = template_means.get(root, 20.0)
        # Slight random drift already baked into item; use safety_stock as proxy for scale
        base_mean = max(1.0, item.safety_stock / 3.0)

        for store in STORES:
            factor = store_factors[store.store_id]
            series = _generate_series(rng, days, base_mean, item.demand_pattern, factor)

            # Truncate history for insufficient pairs
            start_idx = 0
            if (item.item_id, store.store_id) in insufficient_pairs:
                start_idx = days - int(rng.integers(14, 28))

            # Inject missing observations (~3%)
            missing_mask = np.zeros(days, dtype=bool)
            if start_idx < days:
                n_missing = max(1, int(0.03 * (days - start_idx)))
                miss_days = rng.choice(np.arange(start_idx, days), size=min(n_missing, days - start_idx), replace=False)
                missing_mask[miss_days] = True

            for i in range(start_idx, days):
                is_missing = bool(missing_mask[i])
                if is_missing:
                    missing_count += 1
                    qty = 0.0
                else:
                    qty = float(series[i])
                consumption.append(
                    ConsumptionRecord(
                        item_id=item.item_id,
                        store_id=store.store_id,
                        date=dates[i],
                        quantity=qty,
                        is_missing=is_missing,
                    )
                )

            observed = series[start_idx:].copy()
            observed[missing_mask[start_idx:]] = np.nan
            # Impute missing with series mean for average-demand estimates only
            fill = np.nanmean(observed) if np.any(~np.isnan(observed)) else base_mean
            ledger_demand = np.where(np.isnan(observed), fill, observed)
            avg_daily = float(np.nanmean(ledger_demand)) if len(ledger_demand) else base_mean

            # Calibrate current usable stock directly (do not subtract full-year demand
            # from a short opening balance — that collapses most SKUs to zero).
            # Mix of healthy cover and controlled risk scenarios for demo richness.
            force_roll = rng.random()
            if force_roll < 0.06:
                cover_days = float(rng.uniform(0.8, 2.8))  # critical / high stockout risk
            elif force_roll < 0.14:
                cover_days = float(rng.uniform(3.0, 6.5))  # medium risk
            elif force_roll < 0.22:
                cover_days = float(rng.uniform(7.0, 12.0))  # watch list
            else:
                cover_days = float(rng.uniform(18.0, 55.0))  # healthy

            ending = avg_daily * cover_days + float(rng.uniform(0, item.safety_stock * 0.35))
            usable = round(max(0.0, ending), 1)
            balances.append(
                StockBalance(
                    item_id=item.item_id,
                    store_id=store.store_id,
                    usable_qty=usable,
                    as_of_date=today,
                )
            )

            # Batches (1–3) summing approximately to usable qty
            n_batches = int(rng.integers(1, 4)) if usable > 0 else 0
            if n_batches:
                weights = rng.dirichlet(np.ones(n_batches))
                remaining = usable
                for b in range(n_batches):
                    batch_seq += 1
                    qty = round(usable * float(weights[b]), 1) if b < n_batches - 1 else round(remaining, 1)
                    remaining = round(remaining - qty, 1)
                    # Mix of expired, near-expiry, and healthy batches
                    expiry_roll = rng.random()
                    if expiry_roll < 0.05:
                        expiry = today - timedelta(days=int(rng.integers(1, 20)))
                    elif expiry_roll < 0.12:
                        expiry = today + timedelta(days=int(rng.integers(1, 7)))
                    elif expiry_roll < 0.28:
                        expiry = today + timedelta(days=int(rng.integers(8, 30)))
                    elif expiry_roll < 0.50:
                        expiry = today + timedelta(days=int(rng.integers(31, 90)))
                    else:
                        expiry = today + timedelta(days=int(rng.integers(91, 365)))
                    received = today - timedelta(days=int(rng.integers(5, 120)))
                    batches.append(
                        BatchLot(
                            batch_id=f"BAT-{batch_seq:05d}",
                            item_id=item.item_id,
                            store_id=store.store_id,
                            available_qty=max(0.0, qty),
                            expiry_date=expiry,
                            received_date=received,
                        )
                    )

            # Incoming receipts for ~25% of pairs
            if rng.random() < 0.25 and avg_daily > 0:
                receipt_seq += 1
                eta = today + timedelta(days=int(rng.integers(1, min(14, max(2, item.supplier_lead_time_days)))))
                qty_in = round(avg_daily * float(rng.uniform(5, 20)), 1)
                incoming.append(
                    IncomingReceipt(
                        receipt_id=f"RCV-{receipt_seq:05d}",
                        item_id=item.item_id,
                        store_id=store.store_id,
                        expected_qty=qty_in,
                        expected_date=eta,
                    )
                )

    metadata = DatasetMetadata(
        provider_name="Synthetic Data",
        generated_at=datetime(2026, 10, 22, 8, 0, 0, tzinfo=timezone.utc),
        history_start=history_start,
        history_end=today,
        item_count=len(items),
        store_count=len(STORES),
        category_count=len(CATEGORIES),
        missing_observation_count=missing_count,
        insufficient_history_item_count=len(insufficient_pairs),
        seed=seed,
        assumptions=list(ASSUMPTIONS),
    )

    return InventorySnapshot(
        stores=list(STORES),
        categories=list(CATEGORIES),
        items=items,
        balances=balances,
        consumption=consumption,
        batches=batches,
        incoming=incoming,
        metadata=metadata,
    )
