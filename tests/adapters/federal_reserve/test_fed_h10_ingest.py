"""Federal Reserve H.10 ingestion tests."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from devsoul_quant.adapters.federal_reserve.ingest import (
    InvalidH10Html,
    load_fed_h10_eurgbp_batch,
    parse_h10_series,
)
from devsoul_quant.adapters.federal_reserve.manifest import build_fed_h10_manifest
from devsoul_quant.domain.replay import EconomyProvenance


def _html(*rows: tuple[str, str], label: str = "EU Euro") -> str:
    body = "".join(
        f"<tr><td class='left'>{date}</td><td class='right'>{rate}</td></tr>" for date, rate in rows
    )
    return (
        f"<!doctype html><html><body><h5>Historical Rates for the {label}</h5>"
        f"<table>{body}</table></body></html>"
    )


def test_parses_h10_table_into_ascending_observed_ticks() -> None:
    text = _html(("3-JAN-00", "1.0155"), ("4-JAN-00", "1.0309"), ("5-JAN-00", "ND"))

    ticks = parse_h10_series(text)

    assert [tick.quote for tick in ticks] == [Decimal("1.0155"), Decimal("1.0309")]
    assert ticks[0].epoch == int(datetime(2000, 1, 3, tzinfo=UTC).timestamp())
    assert ticks[1].epoch == int(datetime(2000, 1, 4, tzinfo=UTC).timestamp())


def test_derives_eurgbp_on_intersection_of_fed_dates() -> None:
    usd_per_eur = _html(
        ("3-JAN-00", "1.0200"),
        ("4-JAN-00", "1.0400"),
        ("5-JAN-00", "1.0500"),
    )
    usd_per_gbp = _html(
        ("3-JAN-00", "1.5000"),
        ("5-JAN-00", "1.5000"),
        label="Great British Pound",
    )
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    batch = load_fed_h10_eurgbp_batch(
        usd_per_eur_html=usd_per_eur,
        usd_per_gbp_html=usd_per_gbp,
        manifest=manifest,
    )

    assert batch.source == "federal-reserve-h10"
    assert batch.license_reference == manifest.manifest_hash
    assert batch.provenance is EconomyProvenance.OBSERVED
    assert [tick.quote for tick in batch.ticks] == [
        Decimal("1.0200") / Decimal("1.5000"),
        Decimal("1.0500") / Decimal("1.5000"),
    ]


def test_rejects_document_without_h10_rows() -> None:
    with pytest.raises(InvalidH10Html, match=r"no usable H\.10 rows"):
        parse_h10_series("<html><body>not a table</body></html>")


def test_rejects_malformed_data_date_instead_of_skipping_it() -> None:
    text = _html(("32-JAN-00", "1.0200"))

    with pytest.raises(InvalidH10Html, match=r"invalid H\.10 date"):
        parse_h10_series(text)


def test_rejects_unexpected_cell_count_in_data_region() -> None:
    text = (
        "<!doctype html><html><body><h5>Historical Rates for the EU Euro</h5><table>"
        "<tr><td>DATE</td><td>RATE</td></tr>"
        "<tr><td>3-JAN-00</td><td>1.0200</td><td>footnote</td></tr>"
        "</table></body></html>"
    )

    with pytest.raises(InvalidH10Html, match="cells"):
        parse_h10_series(text)


def test_rejects_swapped_series_before_deriving_cross() -> None:
    euros = _html(("3-JAN-00", "1.0200"))
    pounds = _html(("3-JAN-00", "1.5000"), label="Great British Pound")
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    with pytest.raises(InvalidH10Html, match="EU Euro"):
        load_fed_h10_eurgbp_batch(
            usd_per_eur_html=pounds,
            usd_per_gbp_html=euros,
            manifest=manifest,
        )


def test_skips_explicit_header_and_nd_rows() -> None:
    text = _html(("DATE", "RATE"), ("3-JAN-00", "ND"), ("4-JAN-00", "1.0309"))

    assert [tick.quote for tick in parse_h10_series(text)] == [Decimal("1.0309")]


@pytest.mark.parametrize("rate", ["bad", "0", "-1", "NaN", "Infinity"])
def test_rejects_invalid_or_non_positive_rate(rate: str) -> None:
    with pytest.raises(InvalidH10Html, match="rate"):
        parse_h10_series(_html(("3-JAN-00", rate)))


def test_rejects_non_string_document() -> None:
    with pytest.raises(InvalidH10Html, match="string"):
        parse_h10_series(None)  # type: ignore[arg-type]


def test_rejects_duplicate_or_descending_dates() -> None:
    with pytest.raises(InvalidH10Html, match="strictly increasing"):
        parse_h10_series(_html(("4-JAN-00", "1.01"), ("3-JAN-00", "1.02")))


def test_maps_pre_2000_two_digit_year_to_twentieth_century() -> None:
    tick = parse_h10_series(_html(("31-DEC-99", "1.02")))[0]

    assert tick.epoch == int(datetime(1999, 12, 31, tzinfo=UTC).timestamp())


def test_rejects_missing_pound_series_identity() -> None:
    euros = _html(("3-JAN-00", "1.02"))
    wrong = _html(("3-JAN-00", "1.50"))
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    with pytest.raises(InvalidH10Html, match="Great British Pound"):
        load_fed_h10_eurgbp_batch(
            usd_per_eur_html=euros,
            usd_per_gbp_html=wrong,
            manifest=manifest,
        )


def test_rejects_series_without_common_dates() -> None:
    euros = _html(("3-JAN-00", "1.02"))
    pounds = _html(("4-JAN-00", "1.50"), label="Great British Pound")
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    with pytest.raises(InvalidH10Html, match="no common dates"):
        load_fed_h10_eurgbp_batch(
            usd_per_eur_html=euros,
            usd_per_gbp_html=pounds,
            manifest=manifest,
        )
