"""Bounded access to Earth Search. Stalls happen; a job must fail fast and fall back, never hang.

Every HTTP request gets a timeout and a retry budget, on the STAC search (pystac-client) and on
the byte-range reads GDAL makes for stackstac. A scene that cannot be fetched inside the budget is
skipped for the next candidate; when no candidate can be fetched the caller gets a RuntimeError
with the reasons, which a CWL runner turns into a failed step rather than a silent 13-minute wait.

Used by mangrove_workflow_cli.py, scripts/prime_cache.py and mangrove_workflow_marimo.py. The CWL
science notebook (mangrove_workflow_for_cwl.ipynb) inlines the same settings because ipython2cwl
converts a single self-contained notebook.
"""
from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from typing import Any, TypeVar

import stackstac
from pystac_client import Client
from pystac_client.stac_api_io import StacApiIO

EARTH_SEARCH = "https://earth-search.aws.element84.com/v1"
HTTP_TIMEOUT_S = 60      # per request: a STAC search page, or one byte-range read of a COG chunk
CONNECT_TIMEOUT_S = 30
HTTP_RETRIES = 3
RETRY_DELAY_S = 5
CANDIDATES = 3           # scenes to try before giving up on a search window
SCENE_DEADLINE_S = 600   # hard ceiling on fetching one scene, whatever is stuck: a download must end, one way or the other

# GDAL/curl settings for stackstac reads: a stalled range request is abandoned after HTTP_TIMEOUT_S
# and retried HTTP_RETRIES times, so the worst case for a dead chunk is a few minutes, not forever.
GDAL_NETWORK = {
    "GDAL_HTTP_TIMEOUT": HTTP_TIMEOUT_S,
    "GDAL_HTTP_CONNECTTIMEOUT": CONNECT_TIMEOUT_S,
    "GDAL_HTTP_MAX_RETRY": HTTP_RETRIES,
    "GDAL_HTTP_RETRY_DELAY": RETRY_DELAY_S,
}
GDAL_ENV = stackstac.DEFAULT_GDAL_ENV.updated(always=GDAL_NETWORK)

T = TypeVar("T")


def open_catalog(url: str = EARTH_SEARCH) -> Client:
    """The Earth Search client with a request timeout and retries on the search itself."""
    return Client.open(url, stac_io=StacApiIO(timeout=HTTP_TIMEOUT_S, max_retries=HTTP_RETRIES))


class SceneDeadline(TimeoutError):
    pass


def with_deadline(fn: Callable[[], T], seconds: float = SCENE_DEADLINE_S) -> T:
    """Run `fn` in a daemon thread and give it `seconds`. The per-request budget catches a slow
    read; this catches everything else (a wedged worker thread, a lock, an emulator), which
    otherwise looks exactly like progress: a process at zero CPU that never returns."""
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = fn()
        except BaseException as e:  # noqa: BLE001 - re-raised in the caller
            box["error"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise SceneDeadline(f"no result after {seconds:.0f}s; abandoning this scene")
    if "error" in box:
        raise box["error"]
    return box["value"]


def fetch_first(items: Iterable[Any], load: Callable[[Any], T], tries: int = CANDIDATES, log: Callable[[str], None] = print,
                deadline: float = SCENE_DEADLINE_S) -> tuple[Any, T]:
    """Call `load(item)` on candidates in order until one succeeds; return (item, result).

    Each attempt runs under `deadline` seconds. A failure (timeout, HTTP error, empty read,
    deadline) is logged and the next candidate is tried. After `tries` failures, or when there
    are no candidates, raise RuntimeError listing every reason."""
    reasons: list[str] = []
    for n, item in enumerate(items):
        if n >= tries:
            break
        try:
            return item, with_deadline(lambda: load(item), deadline)
        except Exception as e:  # noqa: BLE001 - every network failure mode ends the same way: next candidate
            reason = f"{getattr(item, 'id', item)}: {type(e).__name__}: {str(e)[:160]}"
            reasons.append(reason)
            log(f"   scene could not be fetched, trying the next candidate ({reason})")
    if not reasons:
        raise RuntimeError("no candidate scenes to fetch")
    raise RuntimeError(f"Earth Search: none of {len(reasons)} candidate scene(s) could be fetched within the time budget "
                       f"({HTTP_TIMEOUT_S}s per request, {HTTP_RETRIES} retries, {SCENE_DEADLINE_S}s per scene): " + "; ".join(reasons))
