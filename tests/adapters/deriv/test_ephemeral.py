"""Ephemeral tick cache and Deriv tick parser tests."""

from decimal import Decimal

import pytest

from devsoul_quant.adapters.deriv.ephemeral import (
    MAX_CACHE_SECONDS,
    OPERATIONAL_MARGIN_SECONDS,
    EphemeralTickCache,
    InvalidDerivTick,
    InvalidEphemeralConfig,
    parse_deriv_tick,
)
from devsoul_quant.domain.replay import InvalidTick, Tick

EPOCH = 1_700_000_000


def _tick(epoch: int = EPOCH, quote: str = "100.0000") -> Tick:
    return Tick(epoch=epoch, quote=Decimal(quote))


class TestEphemeralTickCache:
    def test_default_ttl_is_the_operational_margin(self) -> None:
        cache = EphemeralTickCache()

        assert cache.ttl_seconds == OPERATIONAL_MARGIN_SECONDS
        assert cache.ttl_seconds < MAX_CACHE_SECONDS

    @pytest.mark.parametrize("ttl", [0, -1, MAX_CACHE_SECONDS + 1, "100"])
    def test_rejects_ttl_outside_the_permitted_window(self, ttl: object) -> None:
        with pytest.raises(InvalidEphemeralConfig):
            EphemeralTickCache(ttl_seconds=ttl)  # type: ignore[arg-type]

    def test_store_and_read_ticks_in_receipt_order(self) -> None:
        cache = EphemeralTickCache(ttl_seconds=60)
        first = _tick(EPOCH, "1.0000")
        second = _tick(EPOCH + 1, "2.0000")

        cache.store(first, now_epoch=EPOCH + 1)
        cache.store(second, now_epoch=EPOCH + 2)

        assert cache.ticks == (first, second)
        assert len(cache) == 2

    def test_store_rejects_a_future_tick(self) -> None:
        cache = EphemeralTickCache()

        with pytest.raises(InvalidTick):
            cache.store(_tick(EPOCH + 10), now_epoch=EPOCH)

    def test_store_requires_an_integer_now_epoch(self) -> None:
        cache = EphemeralTickCache()

        with pytest.raises(InvalidEphemeralConfig):
            cache.store(_tick(), now_epoch="now")  # type: ignore[arg-type]

    def test_expire_requires_an_integer_now_epoch(self) -> None:
        cache = EphemeralTickCache()

        with pytest.raises(InvalidEphemeralConfig):
            cache.expire(now_epoch=None)  # type: ignore[arg-type]

    def test_expire_drops_entries_older_than_the_ttl(self) -> None:
        cache = EphemeralTickCache(ttl_seconds=60)

        cache.store(_tick(EPOCH), now_epoch=EPOCH)
        cache.store(_tick(EPOCH + 1), now_epoch=EPOCH + 120)

        dropped = cache.expire(now_epoch=EPOCH + 120)

        assert dropped == 1
        assert len(cache) == 1

    def test_clear_discards_everything(self) -> None:
        cache = EphemeralTickCache()
        cache.store(_tick(), now_epoch=EPOCH)

        cache.clear()

        assert len(cache) == 0
        assert cache.ticks == ()


class TestParseDerivTick:
    def test_parses_an_integer_epoch_and_numeric_quote(self) -> None:
        tick = parse_deriv_tick({"tick": {"epoch": EPOCH, "quote": 1234.56}})

        assert tick == Tick(epoch=EPOCH, quote=Decimal("1234.56"))

    def test_parses_a_string_quote(self) -> None:
        tick = parse_deriv_tick({"tick": {"epoch": EPOCH, "quote": "9.8765"}})

        assert tick.quote == Decimal("9.8765")

    @pytest.mark.parametrize(
        "message",
        [
            "not-a-mapping",
            {"no_tick_here": {}},
            {"tick": "not-a-mapping"},
            {"tick": {"epoch": "1", "quote": "1.0"}},
            {"tick": {"epoch": EPOCH, "quote": "nope"}},
            {"tick": {"epoch": EPOCH, "quote": "Infinity"}},
        ],
    )
    def test_rejects_malformed_messages(self, message: object) -> None:
        with pytest.raises(InvalidDerivTick):
            parse_deriv_tick(message)  # type: ignore[arg-type]
