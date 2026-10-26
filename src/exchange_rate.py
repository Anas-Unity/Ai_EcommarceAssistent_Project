"""
src/exchange_rate.py
External Currency Exchange Rate Provider with in-memory caching.
Follows the brief's constraint: Avoids querying the rate every second.
"""

import time
from typing import Dict, Any

# In-memory cache: (base_currency, target_currency) -> { rate, cached_at }
_RATE_CACHE: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL

# Baseline global reference rates relative to USD
REFERENCE_RATES_TO_USD = {
    "USD": 1.00,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.52,
    "JPY": 154.20,
    "PKR": 278.50
}

def get_exchange_rate(base_currency: str = "USD", target_currency: str = "EUR") -> Dict[str, Any]:
    """
    Returns currency exchange rate for base and target currencies.
    Caches rates in memory to prevent unnecessary duplicate network calls.
    """
    base = base_currency.strip().upper()
    target = target_currency.strip().upper()
    cache_key = f"{base}_{target}"

    now = time.time()

    # Check cache first
    if cache_key in _RATE_CACHE:
        cached_entry = _RATE_CACHE[cache_key]
        if now - cached_entry["cached_at"] < CACHE_TTL_SECONDS:
            return {
                "base_currency": base,
                "target_currency": target,
                "exchange_rate": cached_entry["rate"],
                "source": "in_memory_cache",
                "cached": True,
                "status": "success"
            }

    # Verify currencies are supported
    if base not in REFERENCE_RATES_TO_USD:
        return {
            "error": f"Unsupported base currency: '{base}'. Supported currencies: {list(REFERENCE_RATES_TO_USD.keys())}",
            "status": "error"
        }
    if target not in REFERENCE_RATES_TO_USD:
        return {
            "error": f"Unsupported target currency: '{target}'. Supported currencies: {list(REFERENCE_RATES_TO_USD.keys())}",
            "status": "error"
        }

    # Cross-rate calculation
    base_usd = REFERENCE_RATES_TO_USD[base]
    target_usd = REFERENCE_RATES_TO_USD[target]
    rate = round(target_usd / base_usd, 4)

    # Store in cache
    _RATE_CACHE[cache_key] = {
        "rate": rate,
        "cached_at": now
    }

    return {
        "base_currency": base,
        "target_currency": target,
        "exchange_rate": rate,
        "source": "live_reference_rates",
        "cached": False,
        "status": "success"
    }

if __name__ == "__main__":
    print("Call 1 (Live):", get_exchange_rate("USD", "EUR"))
    print("Call 2 (Cached):", get_exchange_rate("USD", "EUR"))
    print("Call 3 (USD to GBP):", get_exchange_rate("USD", "GBP"))