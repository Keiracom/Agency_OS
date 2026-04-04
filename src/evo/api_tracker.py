"""API call tracker for EVO-005 guardrails."""
from collections import defaultdict

DOMAIN_MAP = {
    "api.dataforseo.com": "dfs",
    "api.anthropic.com": "anthropic",
    "api.brightdata.com": "brightdata",
}


class ApiTracker:
    def __init__(self):
        self._counts: dict[str, int] = defaultdict(int)

    def _normalise(self, domain: str) -> str:
        return DOMAIN_MAP.get(domain, "external_http")

    def track_call(self, domain: str) -> None:
        self._counts[self._normalise(domain)] += 1

    def get_counts(self) -> dict:
        return dict(self._counts)

    def check_budget(self, estimated: dict) -> dict:
        overages: dict = {}
        within_budget = True

        for bucket, est in estimated.items():
            actual = self._counts.get(bucket, 0)
            if actual > est * 1.2:
                within_budget = False
                overages[bucket] = {
                    "estimated": est,
                    "actual": actual,
                    "ratio": round(actual / est, 4) if est else float("inf"),
                }

        return {"within_budget": within_budget, "overages": overages}

    def reset(self) -> None:
        self._counts.clear()
