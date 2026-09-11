import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._last_call = 0.0
        self._min_interval = 1.2  # free tier: ~50 calls/min safe buffer

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict:
        url = f"{COINGECKO_API_BASE}{path}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"

        req = Request(url, headers={"Accept": "application/json"})
        if self.api_key:
            req.add_header("x-cg-demo-api-key", self.api_key)

        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        try:
            resp = urlopen(req, timeout=15)
        except HTTPError as exc:
            # CoinGecko returns 429 with Retry-After sometimes
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                if retry_after:
                    time.sleep(int(retry_after))
                else:
                    time.sleep(60)
                return self._get(path, params)
            raise
        except URLError as exc:
            print(f"network failure: {exc}", file=sys.stderr)
            raise

        self._last_call = time.monotonic()
        data = json.loads(resp.read().decode("utf-8"))
        return data

    def simple_price(self, ids: list[str], vs_currencies: list[str]) -> dict:
        if not ids:
            return {}
        ids_param = ",".join(ids)
        vs_param = ",".join(vs_currencies)
        params = {"ids": ids_param, "vs_currencies": vs_param}
        return self._get("/simple/price", params)
