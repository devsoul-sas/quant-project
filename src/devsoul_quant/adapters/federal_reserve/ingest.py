"""Parse Federal Reserve H.10 HTML tables into observed FX ticks."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from itertools import pairwise

from devsoul_quant.application.ports.market_data import MarketDataBatch
from devsoul_quant.domain.data_rights import DataRightsManifest
from devsoul_quant.domain.replay import EconomyProvenance, Tick


class InvalidH10Html(ValueError):
    """Raised when a Federal Reserve H.10 table is malformed or unusable."""


class _TableRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str, ...]] = []
        self._in_cell = False
        self._cell_parts: list[str] = []
        self._row: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._in_cell = True
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            if self._row is not None:
                self._row.append("".join(self._cell_parts).strip())
            self._in_cell = False
            self._cell_parts = []
        elif tag == "tr" and self._row is not None:
            self.rows.append(tuple(self._row))
            self._row = None


def _date_to_epoch(value: str) -> int:
    try:
        day, month, short_year = value.split("-")
        year_value = int(short_year)
        year = (2000 if year_value <= 68 else 1900) + year_value
        parsed = datetime.strptime(f"{day}-{month}-{year}", "%d-%b-%Y")
    except (TypeError, ValueError) as error:
        raise InvalidH10Html(f"invalid H.10 date {value!r}") from error
    return int(parsed.replace(tzinfo=UTC).timestamp())


def parse_h10_series(text: str) -> tuple[Tick, ...]:
    """Parse one H.10 historical-rate HTML table in ascending date order."""
    if not isinstance(text, str):
        raise InvalidH10Html("text must be a string")
    parser = _TableRows()
    parser.feed(text)
    ticks: list[Tick] = []
    for row in parser.rows:
        if not row:
            continue
        if row[0].upper() == "DATE":
            continue
        if len(row) != 2:
            raise InvalidH10Html(f"unexpected {len(row)} cells in an H.10 data row")
        date_value, rate_value = row
        if rate_value == "ND":
            continue
        epoch = _date_to_epoch(date_value)
        try:
            quote = Decimal(rate_value)
        except InvalidOperation as error:
            raise InvalidH10Html(f"invalid H.10 rate {rate_value!r}") from error
        if not quote.is_finite() or quote <= 0:
            raise InvalidH10Html(f"H.10 rate must be positive and finite, got {rate_value!r}")
        ticks.append(Tick(epoch=epoch, quote=quote))
    if not ticks:
        raise InvalidH10Html("no usable H.10 rows found")
    if any(current.epoch <= previous.epoch for previous, current in pairwise(ticks)):
        raise InvalidH10Html("H.10 dates must be strictly increasing")
    return tuple(ticks)


def load_fed_h10_eurgbp_batch(
    *,
    usd_per_eur_html: str,
    usd_per_gbp_html: str,
    manifest: DataRightsManifest,
) -> MarketDataBatch:
    """Derive GBP per EUR from matching USD/EUR and USD/GBP H.10 dates."""
    if "Historical Rates for the EU Euro" not in usd_per_eur_html:
        raise InvalidH10Html("expected the H.10 EU Euro series")
    if "Historical Rates for the Great British Pound" not in usd_per_gbp_html:
        raise InvalidH10Html("expected the H.10 Great British Pound series")
    euros = {tick.epoch: tick.quote for tick in parse_h10_series(usd_per_eur_html)}
    pounds = {tick.epoch: tick.quote for tick in parse_h10_series(usd_per_gbp_html)}
    ticks = tuple(
        Tick(epoch=epoch, quote=euros[epoch] / pounds[epoch])
        for epoch in sorted(euros.keys() & pounds.keys())
    )
    if not ticks:
        raise InvalidH10Html("H.10 EUR and GBP series have no common dates")
    return MarketDataBatch(
        source="federal-reserve-h10",
        license_reference=manifest.manifest_hash,
        provenance=EconomyProvenance.OBSERVED,
        ticks=ticks,
    )
