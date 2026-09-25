"""Chainlink Data Feeds reader via eth_call (stdlib). Fail-closed."""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("baitcoin.chainlink")
_LATEST, _DECIMALS = "0xfeaf968c", "0x313ce567"
MAINNET_FEEDS = {
    "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
    "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
    "USDT/USD": "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D",
    "USDC/USD": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
}
DEFAULT_RPCS = ("https://rpc.mevblocker.io", "https://eth.drpc.org", "https://1rpc.io/eth")

class ChainlinkError(RuntimeError):
    pass

@dataclass(frozen=True)
class FeedReading:
    pair: str
    feed_address: str
    price: float
    answer_raw: int
    decimals: int
    updated_at: int
    round_id: int
    age_seconds: float
    rpc: str
    fetched_at: float
    def to_dict(self) -> dict[str, Any]:
        return self.__dict__
    def to_ppm(self, reference: float = 1.0) -> int:
        if self.price <= 0 or reference <= 0:
            raise ChainlinkError("price and reference must be positive")
        return int(round((self.price / reference) * 1_000_000))

def _u256(w: str) -> int:
    return int(w, 16)

def _i256(w: str) -> int:
    v = int(w, 16)
    return v - 2**256 if v >= 2**255 else v

class ChainlinkFeedReader:
    def __init__(self, *, rpcs=DEFAULT_RPCS, feeds=None, max_age_seconds=3600, timeout=12.0, clock=None):
        if max_age_seconds < 1 or not rpcs:
            raise ChainlinkError("invalid config")
        self.rpcs, self.feeds = tuple(rpcs), dict(feeds or MAINNET_FEEDS)
        self.max_age_seconds, self.timeout = max_age_seconds, timeout
        self.clock = clock or time.time

    def _eth_call(self, rpc: str, to: str, data: str) -> str:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                           "params": [{"to": to, "data": data}, "latest"]}).encode()
        req = Request(rpc, data=body, headers={"Content-Type": "application/json",
                      "User-Agent": "BAITHex-chainlink-feed/1.0"}, method="POST")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ChainlinkError(f"RPC call failed ({rpc}): {exc}") from exc
        if "error" in payload:
            raise ChainlinkError(f"RPC error ({rpc}): {payload['error']}")
        result = payload.get("result")
        if not isinstance(result, str) or not result.startswith("0x"):
            raise ChainlinkError(f"invalid eth_call result from {rpc}")
        return result

    def _read_on_rpc(self, rpc: str, pair: str, address: str) -> FeedReading:
        decimals = _u256(self._eth_call(rpc, address, _DECIMALS)[2:] or "0")
        if decimals > 18:
            raise ChainlinkError(f"unexpected decimals={decimals}")
        raw = self._eth_call(rpc, address, _LATEST)[2:]
        if len(raw) < 320:
            raise ChainlinkError("latestRoundData payload too short")
        words = [raw[i:i+64] for i in range(0, 320, 64)]
        round_id, answer, updated_at = _u256(words[0]), _i256(words[1]), _u256(words[3])
        now = float(self.clock())
        if answer <= 0:
            raise ChainlinkError(f"{pair}: non-positive answer")
        if updated_at <= 0:
            raise ChainlinkError(f"{pair}: incomplete round")
        age = now - updated_at
        if age > self.max_age_seconds:
            raise ChainlinkError(f"{pair}: stale age={age:.0f}s")
        if age < -60:
            raise ChainlinkError(f"{pair}: updatedAt in the future")
        return FeedReading(pair, address, answer / (10 ** decimals), answer, decimals,
                           updated_at, round_id, age, rpc, now)

    def get_price(self, pair: str) -> FeedReading:
        address = self.feeds.get(pair)
        if not address:
            raise ChainlinkError(f"unknown pair {pair!r}")
        errors = []
        for rpc in self.rpcs:
            try:
                return self._read_on_rpc(rpc, pair, address)
            except ChainlinkError as exc:
                errors.append(str(exc))
        raise ChainlinkError(f"all RPCs failed for {pair}: " + " | ".join(errors[:3]))

    def get_prices(self, pairs: Sequence[str]) -> dict[str, FeedReading]:
        return {p: self.get_price(p) for p in pairs}

def compare_with_bait_oracle(chainlink, bait_prices, *, max_bps=150):
    report = {"max_bps": max_bps, "pairs": {}, "ok": True}
    for pair, reading in chainlink.items():
        base = pair.split("/")[0]
        bait_val = bait_prices.get(base)
        if bait_val is None:
            report["pairs"][pair] = {"status": "missing_in_bait"}
            continue
        if bait_val <= 0:
            report["pairs"][pair] = {"status": "invalid_bait_price"}
            report["ok"] = False
            continue
        bps = abs(reading.price - bait_val) / bait_val * 10_000
        report["pairs"][pair] = {"chainlink": reading.price, "bait": bait_val,
                                  "diff_bps": round(bps, 2),
                                  "status": "ok" if bps <= max_bps else "diverge"}
        if bps > max_bps:
            report["ok"] = False
    return report
