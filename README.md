# crypto-portfolio-alert

I got tired of checking five different apps to see if my positions were tanking, so I wrote this. It pulls current prices from CoinGecko's public API, compares them against the holdings you define, and spits out alerts when things cross thresholds you care about.

It's just a Python script. No web UI, no database, no docker-compose. I run it from cron every 15 minutes and pipe the output to a Telegram bot when there's something worth knowing.

## Install

```bash
pip install -r requirements.txt
```

Or if you already have the deps:

```bash
python -m pip install httpx
```

## Run

With no args it uses embedded demo data so you can see what the alerts look like:

```bash
python portfolio_alert.py
```

Point it at your own holdings file:

```bash
python portfolio_alert.py --holdings my_holdings.json --threshold-pct 5.0
```

## Holdings format

```json
{
  "BTC": 0.45,
  "ETH": 4.2,
  "SOL": 150.0
}
```

## What I use it for

I have a systemd timer that runs this every 15 minutes. When an alert fires, the wrapper script sends me a Telegram message. The `--quiet` flag suppresses the "all clear" output so I only get pinged when something actually moves.

## License

MIT

<!-- last-checked: 2026-10-04 -->
