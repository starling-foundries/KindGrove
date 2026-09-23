"""The network budget: a stalled Earth Search read fails within seconds, and the loaders fall back."""
from __future__ import annotations

import time

import pytest
import rasterio

import earthsearch as es


def test_gdal_budget_fails_fast_on_a_black_hole():
    """A non-routable address never answers. With the budget, GDAL gives up in seconds; without it, this hangs."""
    t = time.time()
    with pytest.raises(rasterio.errors.RasterioIOError):
        with rasterio.Env(**{**es.GDAL_NETWORK, "GDAL_HTTP_CONNECTTIMEOUT": 2, "GDAL_HTTP_MAX_RETRY": 1, "GDAL_HTTP_RETRY_DELAY": 1}):
            rasterio.open("/vsicurl/http://10.255.255.1/never.tif")
    assert time.time() - t < 30


def test_gdal_env_carries_the_budget_into_stackstac():
    always = es.GDAL_ENV.always.options  # a rasterio.Env
    for k, v in es.GDAL_NETWORK.items():
        assert always[k] == v
    assert always["GDAL_HTTP_MULTIRANGE"] == "YES"  # stackstac's own defaults are kept


def test_fetch_first_falls_back_then_fails_loudly():
    calls = []

    def load(item):
        calls.append(item)
        if item in ("a", "b"):
            raise TimeoutError(f"stalled on {item}")
        return f"data of {item}"

    logs = []
    item, data = es.fetch_first(["a", "b", "c", "d"], load, tries=3, log=logs.append)
    assert (item, data) == ("c", "data of c") and calls == ["a", "b", "c"]
    assert len(logs) == 2 and "next candidate" in logs[0]

    with pytest.raises(RuntimeError, match="none of 2 candidate"):
        es.fetch_first(["a", "b"], load, tries=3, log=logs.append)
    with pytest.raises(RuntimeError, match="none of 3 candidate"):
        es.fetch_first(["a", "b", "a", "b"], load, tries=3, log=logs.append)  # the budget caps the attempts
    with pytest.raises(RuntimeError, match="no candidate"):
        es.fetch_first([], load)


def test_deadline_abandons_a_wedged_fetch():
    """A fetch that never returns (a wedged worker, not a slow read) is abandoned at the deadline
    and the next candidate is tried; the process is not held hostage by the stuck thread."""
    import threading

    stuck = threading.Event()

    def load(item):
        if item == "wedged":
            stuck.wait()  # never set: this call never returns
        return f"data of {item}"

    t = time.time()
    item, data = es.fetch_first(["wedged", "fine"], load, deadline=0.5, log=lambda m: None)
    assert (item, data) == ("fine", "data of fine")
    assert time.time() - t < 5
    with pytest.raises(RuntimeError, match="per scene"):
        es.fetch_first(["wedged"], load, deadline=0.2, log=lambda m: None)
    stuck.set()
