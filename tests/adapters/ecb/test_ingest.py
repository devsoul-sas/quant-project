"""ECB euro-reference-rate CSV ingestion tests."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from devsoul_quant.adapters.ecb.ingest import (
    InvalidEcbCsv,
    load_ecb_batch,
    parse_eurofxref_hist,
)
from devsoul_quant.adapters.ecb.manifest import build_ecb_manifest
from devsoul_quant.domain.replay import EconomyProvenance

CSV = (
    "Date,USD,JPY,GBP,\n"
    "2026-11-04,1.1267,178.3,0.83460,\n"
    "2026-11-03,1.1179,176.95,0.83358,\n"
    "2026-11-02,1.1205,177.1,N/A,\n"
    "2026-10-30,1.1250,175.9,0.83000,\n"
)


def test_parses_newest_first_csv_into_ascending_ticks() -> None:
    ticks = parse_eurofxref_hist(CSV, currency="USD")

    assert [tick.quote for tick in ticks] == [
        Decimal("1.1250"),
        Decimal("1.1205"),
        Decimal("1.1179"),
        Decimal("1.1267"),
    ]
    assert [tick.epoch for tick in ticks] == sorted(tick.epoch for tick in ticks)


def test_maps_date_to_utc_midnight_epoch() -> None:
    ticks = parse_eurofxref_hist(CSV, currency="USD")

    assert ticks[0].epoch == int(datetime(2026, 10, 30, tzinfo=UTC).timestamp())
    assert ticks[-1].epoch == int(datetime(2026, 11, 4, tzinfo=UTC).timestamp())


def test_skips_na_rows() -> None:
    ticks = parse_eurofxref_hist(CSV, currency="GBP")

    assert [tick.quote for tick in ticks] == [
        Decimal("0.83000"),
        Decimal("0.83358"),
        Decimal("0.83460"),
    ]


def test_rejects_unknown_currency() -> None:
    with pytest.raises(InvalidEcbCsv, match="not a column"):
        parse_eurofxref_hist(CSV, currency="XXX")


def test_rejects_lowercase_currency() -> None:
    with pytest.raises(InvalidEcbCsv, match="uppercase"):
        parse_eurofxref_hist(CSV, currency="usd")


def test_rejects_empty_csv() -> None:
    with pytest.raises(InvalidEcbCsv, match="empty"):
        parse_eurofxref_hist("", currency="USD")


def test_rejects_missing_date_header() -> None:
    with pytest.raises(InvalidEcbCsv, match="Date"):
        parse_eurofxref_hist("Foo,USD\n2026-11-04,1.1\n", currency="USD")


def test_rejects_invalid_date() -> None:
    with pytest.raises(InvalidEcbCsv, match="date"):
        parse_eurofxref_hist("Date,USD\n2026-13-99,1.1\n", currency="USD")


def test_rejects_invalid_rate() -> None:
    with pytest.raises(InvalidEcbCsv, match="rate"):
        parse_eurofxref_hist("Date,USD\n2026-11-04,abc\n", currency="USD")


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(InvalidEcbCsv, match="positive"):
        parse_eurofxref_hist("Date,USD\n2026-11-04,0\n", currency="USD")


def test_rejects_duplicate_dates() -> None:
    with pytest.raises(InvalidEcbCsv, match="strictly increasing"):
        parse_eurofxref_hist("Date,USD\n2026-11-04,1.1\n2026-11-04,1.2\n", currency="USD")


def test_load_ecb_batch_binds_observed_provenance() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    batch = load_ecb_batch(text=CSV, currency="USD", manifest=manifest)

    assert batch.source == "ecb"
    assert batch.license_reference == manifest.manifest_hash
    assert batch.provenance is EconomyProvenance.OBSERVED
    assert len(batch.ticks) == 4
