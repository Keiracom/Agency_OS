"""Thin httpx transport wrapper that records API calls via ApiTracker."""
import httpx
from src.evo.api_tracker import ApiTracker


class TrackedTransport(httpx.BaseTransport):
    def __init__(self, tracker: ApiTracker, wrapped: httpx.BaseTransport = None):
        self._tracker = tracker
        self._wrapped = wrapped or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._tracker.track_call(request.url.host)
        return self._wrapped.handle_request(request)

    def close(self) -> None:
        self._wrapped.close()


def make_tracked_client(tracker: ApiTracker) -> httpx.Client:
    """Return an httpx.Client instrumented with ApiTracker — the enforcement point."""
    return httpx.Client(transport=TrackedTransport(tracker))
