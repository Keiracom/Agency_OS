"""
Contract: src/services/domain_name_generator.py
Purpose: Generate customer-agnostic burner domain candidates using approved naming patterns
Layer: services
Imports: stdlib, src.models
Consumers: src.services.domain_pool_manager
"""

import random
from typing import Optional

# Hard rejection rules
MARKETING_VERBS = {"get", "try", "hello", "go", "grab", "join", "use", "meet", "start", "buy", "free"}
BAD_TLDS = {".io", ".co", ".xyz", ".site", ".online", ".click", ".ai", ".dev"}
MAX_NAME_LENGTH = 22


class DomainNameGenerator:
    """
    Generates pronounceable, professional domain name candidates.

    Rules enforced:
    - No marketing verbs (get, try, hello, etc.)
    - No low-trust TLDs (.io, .xyz, etc.)
    - Max 22 chars for the name part
    - Alpha-only (no hyphens, numbers)
    - Pronounceable (no more than 3 consecutive consonants)
    """

    def __init__(self, patterns: list[dict], seed: int | None = None):
        """
        Args:
            patterns: List of pattern dicts with keys: pattern_type, seeds, suffixes
            seed: Optional RNG seed for reproducible output (testing)
        """
        self.patterns = patterns
        self._rng = random.Random(seed)

    def generate_batch(self, count: int = 20, tld: str = ".com.au") -> list[dict]:
        """
        Generate a batch of candidate domain names.

        Returns a list of dicts with keys:
            domain_name, name_part, tld, pattern_type, seed_word, suffix
        """
        candidates: list[dict] = []
        attempts = 0
        max_attempts = count * 5

        while len(candidates) < count and attempts < max_attempts:
            attempts += 1
            pattern = self._rng.choice(self.patterns)
            seeds = pattern.get("seeds", [])
            suffixes = pattern.get("suffixes", [])

            if not seeds or not suffixes:
                continue

            seed_word = self._rng.choice(seeds)
            suffix = self._rng.choice(suffixes)
            name = f"{seed_word}{suffix}"

            if not self._validate(name, tld):
                continue

            domain = f"{name}{tld}"
            if domain not in [c["domain_name"] for c in candidates]:
                candidates.append({
                    "domain_name": domain,
                    "name_part": name,
                    "tld": tld.lstrip("."),
                    "pattern_type": pattern.get("pattern_type", "unknown"),
                    "seed_word": seed_word,
                    "suffix": suffix,
                })

        return candidates[:count]

    def _validate(self, name: str, tld: str) -> bool:
        """Apply all hard rejection rules. Returns True if valid."""
        if len(name) > MAX_NAME_LENGTH:
            return False
        if any(verb in name.lower() for verb in MARKETING_VERBS):
            return False
        # Check TLD with leading dot for consistency
        check_tld = tld if tld.startswith(".") else f".{tld}"
        if check_tld in BAD_TLDS:
            return False
        if not name.isalpha():
            return False
        if not self._is_pronounceable(name):
            return False
        return True

    def _is_pronounceable(self, name: str) -> bool:
        """Reject names with more than 3 consecutive consonants."""
        vowels = set("aeiou")
        consec = 0
        for c in name.lower():
            if c not in vowels:
                consec += 1
                if consec > 3:
                    return False
            else:
                consec = 0
        return True
