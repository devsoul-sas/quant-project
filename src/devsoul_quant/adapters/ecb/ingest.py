"""Parse ECB euro foreign-exchange reference-rate CSV into observed ticks."""

from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from itertools import pairwise

from devsoul_quant.application.ports.market_data import MarketDataBatch
from devsoul_quant.domain.data_rights import DataRightsManifest
from devsoul_quant.domain.replay import EconomyProvenance, Tick

_ISO_CODE = re.compile(r"^[A-Z]{3}$")


class InvalidEcbCsv(ValueError):
    """Raised when the ECB reference-rate CSV is malformed or unusable."""


def _date_to_epoch(value: str) -> int:
    """Convert a ``YYYY-MM-DD`` date to its UTC-midnight epoch in seconds."""
    try:
        return int(datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())
    except ValueError as exc:
        raise InvalidEcbCsv(f"invalid date {value!r}") from exc


def _require_currency(currency: str) -> None:
    if not isinstance(currency, str) or _ISO_CODE.fullmatch(currency) is None:
        raise InvalidEcbCsv("currency must be a three-letter uppercase ISO code")


def parse_eurofxref_hist(text: str, *, currency: str) -> tuple[Tick, ...]:
    """Parse the ``eurofxref-hist`` CSV into ascending observed ticks.

    ``currency`` is the three-letter ISO code of the quote currency (e.g. ``"USD"``);
    the base currency is always EUR. Rows whose rate is ``N/A`` or blank are skipped.
    The source file lists dates newest-first, so the result is reversed to strict
    ascending order.
    """
    _require_currency(currency)
    if not isinstance(text, str):
        raise InvalidEcbCsv("text must be a string")

    reader = csv.reader(StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise InvalidEcbCsv("CSV is empty") from exc
    if not header or header[0].strip() != "Date":
        raise InvalidEcbCsv("CSV must begin with a Date header column")
    try:
        column_index = header.index(currency)
    except ValueError as exc:
        raise InvalidEcbCsv(f"currency {currency!r} is not a column in the CSV") from exc

    ticks: list[Tick] = []
    for row in reader:
        if len(row) <= column_index:
            raise InvalidEcbCsv("row has fewer columns than the CSV header")
        date_value = row[0].strip()
        rate_value = row[column_index].strip()
        if not date_value or not rate_value or rate_value == "N/A":
            continue
        try:
            quote = Decimal(rate_value)
        except InvalidOperation as exc:
            raise InvalidEcbCsv(f"invalid rate {rate_value!r}") from exc
        if not quote.is_finite() or quote <= 0:
            raise InvalidEcbCsv(f"rate must be a positive finite decimal, got {rate_value!r}")
        ticks.append(Tick(epoch=_date_to_epoch(date_value), quote=quote))

    ticks.reverse()
    if any(current.epoch <= previous.epoch for previous, current in pairwise(ticks)):
        raise InvalidEcbCsv("tick epochs must be strictly increasing")
    return tuple(ticks)


def load_ecb_batch(
    *,
    text: str,
    currency: str,
    manifest: DataRightsManifest,
) -> MarketDataBatch:
    """Parse the CSV and return an observed, provider-neutral market-data batch."""
    ticks = parse_eurofxref_hist(text, currency=currency)
    return MarketDataBatch(
        source="ecb",
        license_reference=manifest.manifest_hash,
        provenance=EconomyProvenance.OBSERVED,
        ticks=ticks,
    )
