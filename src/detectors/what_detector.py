"""
FILE: src/detectors/what_detector.py
PURPOSE: WHAT Detector - Analyzes content patterns that correlate with conversions
PHASE: 16 (Conversion Intelligence), modified Phase 24B
TASK: 16B, CONTENT-006
DEPENDENCIES:
  - src/detectors/base.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only

WHAT Pattern Outputs:
  - subject_patterns: Which subject line patterns convert
  - pain_points: Which pain points are effective
  - ctas: Which CTAs convert best
  - angles: Which message angles work
  - optimal_length: Optimal message length by channel
  - personalization_lift: Lift from personalization elements

Phase 24B Additions:
  - template_performance: Which templates convert best
  - ab_test_insights: Insights from A/B test results
  - link_effectiveness: Whether including links helps/hurts
  - ai_model_performance: Which AI models generate better content
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.detectors.base import BaseDetector
from src.models.activity import Activity
from src.models.conversion_patterns import ConversionPattern

# Angle detection patterns
ANGLE_PATTERNS = {
    "roi_focused": ["roi", "return", "revenue", "profit", "save", "increase", "boost"],
    "social_proof": ["clients like", "companies like", "case study", "helped", "worked with"],
    "curiosity": ["noticed", "wondering", "quick question", "curious", "saw that"],
    "fear_based": ["missing out", "losing", "behind", "risk", "problem", "struggle"],
    "value_add": ["free", "complimentary", "audit", "analysis", "no cost"],
    "authority": ["expert", "specialist", "experience", "trusted", "leading"],
}

# Subject pattern templates
SUBJECT_PATTERNS = [
    (r"question.*(about|for|regarding)", "question_about"),
    (r"^quick\s+question", "quick_question"),
    (r"^re:", "reply_style"),
    (r"idea\s+for", "idea_for"),
    (r"thought\s+(about|for)", "thought_about"),
    (r"\{company\}|\{first_name\}", "personalized"),
]


class WhatDetector(BaseDetector):
    """
    WHAT Detector - Analyzes which content patterns predict conversions.

    Analyzes:
    - Subject line patterns (which subject types convert?)
    - Pain point effectiveness (which pain points resonate?)
    - CTA effectiveness (which calls-to-action work?)
    - Message angles (which angles convert?)
    - Optimal message length by channel
    - Personalization lift
    """

    pattern_type = "what"

    async def detect(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> ConversionPattern:
        """
        Run WHAT pattern detection for a client.

        Analyzes activities with content_snapshot to find content patterns.
        """
        # Get activities with content snapshots
        activities = await self._get_activities_with_content(db, client_id)

        if len(activities) < self.min_sample_size:
            return await self.save_pattern(
                db=db,
                client_id=client_id,
                patterns=self._default_patterns(),
                sample_size=len(activities),
                confidence=self.calculate_confidence(len(activities)),
            )

        # Calculate baseline
        converting = [a for a in activities if a.led_to_booking]
        baseline_rate = len(converting) / len(activities) if activities else 0

        # Analyze each dimension
        subject_patterns = self._analyze_subjects(activities, baseline_rate)
        pain_points = self._analyze_pain_points(activities, baseline_rate)
        ctas = self._analyze_ctas(activities, baseline_rate)
        angles = self._analyze_angles(activities, baseline_rate)
        optimal_length = self._analyze_length(activities, baseline_rate)
        personalization_lift = self._analyze_personalization(activities, baseline_rate)

        # Phase 24B: New analyses
        template_performance = self._analyze_templates(activities, baseline_rate)
        ab_test_insights = self._analyze_ab_tests(activities, baseline_rate)
        link_effectiveness = self._analyze_links(activities, baseline_rate)
        ai_model_performance = self._analyze_ai_models(activities, baseline_rate)

        patterns = {
            "type": "what",
            "version": "2.0",  # Updated for Phase 24B
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": len(activities),
            "baseline_conversion_rate": round(baseline_rate, 4),
            "subject_patterns": subject_patterns,
            "pain_points": pain_points,
            "ctas": ctas,
            "angles": angles,
            "optimal_length": optimal_length,
            "personalization_lift": personalization_lift,
            # Phase 24B additions
            "template_performance": template_performance,
            "ab_test_insights": ab_test_insights,
            "link_effectiveness": link_effectiveness,
            "ai_model_performance": ai_model_performance,
        }

        return await self.save_pattern(
            db=db,
            client_id=client_id,
            patterns=patterns,
            sample_size=len(activities),
            confidence=self.calculate_confidence(len(activities)),
        )

    async def _get_activities_with_content(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> list[Activity]:
        """Get outbound activities with content snapshots."""
        cutoff = datetime.utcnow() - timedelta(days=90)

        stmt = select(Activity).where(
            and_(
                Activity.client_id == client_id,
                Activity.content_snapshot.isnot(None),
                Activity.action.in_(["sent", "email_sent", "sms_sent", "linkedin_sent"]),
                Activity.created_at >= cutoff,
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    def _analyze_subjects(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze subject line patterns."""
        pattern_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "converted": 0})

        for activity in activities:
            snapshot = activity.content_snapshot or {}
            subject = snapshot.get("subject", "")
            if not subject:
                continue

            # Match against patterns
            subject_lower = subject.lower()
            for pattern, name in SUBJECT_PATTERNS:
                if re.search(pattern, subject_lower):
                    pattern_stats[name]["total"] += 1
                    if activity.led_to_booking:
                        pattern_stats[name]["converted"] += 1

        winning = []
        for pattern, stats in pattern_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            if rate > baseline_rate:
                winning.append(
                    {
                        "pattern": pattern,
                        "conversion_rate": round(rate, 4),
                        "sample": stats["total"],
                    }
                )

        winning.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return {"winning": winning[:5]}

    def _analyze_pain_points(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze pain point effectiveness."""
        pain_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "converted": 0})

        for activity in activities:
            snapshot = activity.content_snapshot or {}
            pain_points = snapshot.get("pain_points_used", [])

            for pain in pain_points:
                pain_stats[pain]["total"] += 1
                if activity.led_to_booking:
                    pain_stats[pain]["converted"] += 1

        effective = []
        ineffective = []

        for pain, stats in pain_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            lift = self.calculate_lift(rate, baseline_rate)

            entry = {
                "pain_point": pain,
                "frequency": round(stats["total"] / len(activities), 2),
                "lift": round(lift, 2),
            }

            if lift >= 1.1:
                effective.append(entry)
            elif lift < 0.9:
                ineffective.append(entry)

        effective.sort(key=lambda x: x["lift"], reverse=True)
        ineffective.sort(key=lambda x: x["lift"])

        return {
            "effective": effective[:5],
            "ineffective": ineffective[:3],
        }

    def _analyze_ctas(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze CTA effectiveness."""
        cta_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "converted": 0})

        for activity in activities:
            snapshot = activity.content_snapshot or {}
            cta = snapshot.get("cta_used")
            if not cta:
                continue

            cta_stats[cta]["total"] += 1
            if activity.led_to_booking:
                cta_stats[cta]["converted"] += 1

        effective = []
        for cta, stats in cta_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            effective.append(
                {
                    "cta": cta,
                    "conversion_rate": round(rate, 4),
                    "sample": stats["total"],
                }
            )

        effective.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return {"effective": effective[:5]}

    def _analyze_angles(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze message angle effectiveness."""
        angle_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "converted": 0})

        for activity in activities:
            snapshot = activity.content_snapshot or {}
            body = snapshot.get("body", "").lower()

            for angle, keywords in ANGLE_PATTERNS.items():
                if any(kw in body for kw in keywords):
                    angle_stats[angle]["total"] += 1
                    if activity.led_to_booking:
                        angle_stats[angle]["converted"] += 1

        rankings = []
        for angle, stats in angle_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            rankings.append(
                {
                    "angle": angle,
                    "conversion_rate": round(rate, 4),
                    "sample": stats["total"],
                }
            )

        rankings.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return {"rankings": rankings}

    def _analyze_length(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze optimal message length by channel."""
        channel_lengths: dict[str, list[tuple[int, bool]]] = defaultdict(list)

        for activity in activities:
            snapshot = activity.content_snapshot or {}
            channel = snapshot.get("channel", "email")
            word_count = snapshot.get("word_count", 0)

            if word_count > 0:
                channel_lengths[channel].append((word_count, activity.led_to_booking))

        result = {}
        for channel, lengths in channel_lengths.items():
            if len(lengths) < 10:
                continue

            # Find optimal by binning
            converting = [l[0] for l in lengths if l[1]]
            if not converting:
                continue

            optimal = int(sum(converting) / len(converting))
            result[channel] = {
                "optimal_words": optimal,
                "range_min": max(10, optimal - 25),
                "range_max": optimal + 25,
            }

        return result

    def _analyze_personalization(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, float]:
        """Analyze lift from personalization elements."""
        elements = [
            "has_company_mention",
            "has_first_name",
            "has_recent_news",
            "has_mutual_connection",
            "has_industry_specific",
        ]

        result = {}
        for element in elements:
            with_element = [a for a in activities if (a.content_snapshot or {}).get(element)]
            if len(with_element) < 5:
                result[element.replace("has_", "")] = 1.0
                continue

            rate = sum(1 for a in with_element if a.led_to_booking) / len(with_element)
            result[element.replace("has_", "")] = round(self.calculate_lift(rate, baseline_rate), 2)

        return result

    # ========================================
    # Phase 24B: New Analysis Methods
    # ========================================

    def _analyze_templates(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """
        Analyze template performance.

        Phase 24B: Uses template_id field to track which templates convert best.
        """
        template_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "converted": 0}
        )

        for activity in activities:
            template_id = getattr(activity, "template_id", None)
            if not template_id:
                continue

            template_key = str(template_id)
            template_stats[template_key]["total"] += 1
            if activity.led_to_booking:
                template_stats[template_key]["converted"] += 1

        rankings = []
        for template_id, stats in template_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            rankings.append(
                {
                    "template_id": template_id,
                    "conversion_rate": round(rate, 4),
                    "sample": stats["total"],
                    "lift": round(self.calculate_lift(rate, baseline_rate), 2),
                }
            )

        rankings.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return {
            "top_templates": rankings[:5],
            "bottom_templates": rankings[-3:] if len(rankings) > 3 else [],
            "total_templates_analyzed": len(template_stats),
        }

    def _analyze_ab_tests(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """
        Analyze A/B test results.

        Phase 24B: Uses ab_test_id and ab_variant to aggregate test insights.
        """
        test_results: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"total": 0, "converted": 0})
        )

        for activity in activities:
            ab_test_id = getattr(activity, "ab_test_id", None)
            ab_variant = getattr(activity, "ab_variant", None)
            if not ab_test_id or not ab_variant:
                continue

            test_key = str(ab_test_id)
            test_results[test_key][ab_variant]["total"] += 1
            if activity.led_to_booking:
                test_results[test_key][ab_variant]["converted"] += 1

        insights = []
        for test_id, variants in test_results.items():
            if len(variants) < 2:
                continue

            variant_rates = {}
            for variant, stats in variants.items():
                if stats["total"] >= 5:
                    variant_rates[variant] = stats["converted"] / stats["total"]

            if len(variant_rates) >= 2:
                best_variant = max(variant_rates, key=variant_rates.get)
                worst_variant = min(variant_rates, key=variant_rates.get)
                insights.append(
                    {
                        "test_id": test_id,
                        "best_variant": best_variant,
                        "best_rate": round(variant_rates[best_variant], 4),
                        "worst_variant": worst_variant,
                        "worst_rate": round(variant_rates[worst_variant], 4),
                        "lift_difference": round(
                            variant_rates[best_variant] - variant_rates[worst_variant], 4
                        ),
                    }
                )

        return {
            "test_insights": insights,
            "total_tests_analyzed": len(test_results),
        }

    def _analyze_links(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """
        Analyze whether including links helps or hurts conversion.

        Phase 24B: Uses links_included field.
        """
        with_links = {"total": 0, "converted": 0}
        without_links = {"total": 0, "converted": 0}
        link_count_stats: dict[int, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "converted": 0}
        )

        for activity in activities:
            links = getattr(activity, "links_included", None) or []

            if links:
                with_links["total"] += 1
                if activity.led_to_booking:
                    with_links["converted"] += 1

                # Track by link count
                count = min(len(links), 5)  # Cap at 5 for stats
                link_count_stats[count]["total"] += 1
                if activity.led_to_booking:
                    link_count_stats[count]["converted"] += 1
            else:
                without_links["total"] += 1
                if activity.led_to_booking:
                    without_links["converted"] += 1

        # Calculate rates
        with_rate = (
            with_links["converted"] / with_links["total"] if with_links["total"] >= 5 else None
        )
        without_rate = (
            without_links["converted"] / without_links["total"]
            if without_links["total"] >= 5
            else None
        )

        # Find optimal link count
        optimal_count = None
        best_rate = 0
        for count, stats in link_count_stats.items():
            if stats["total"] >= 5:
                rate = stats["converted"] / stats["total"]
                if rate > best_rate:
                    best_rate = rate
                    optimal_count = count

        return {
            "with_links_rate": round(with_rate, 4) if with_rate else None,
            "without_links_rate": round(without_rate, 4) if without_rate else None,
            "links_lift": round(self.calculate_lift(with_rate, without_rate), 2)
            if with_rate and without_rate
            else None,
            "optimal_link_count": optimal_count,
            "recommendation": "include_links"
            if (with_rate and without_rate and with_rate > without_rate)
            else "no_links",
        }

    def _analyze_ai_models(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """
        Analyze which AI models generate better-converting content.

        Phase 24B: Uses ai_model_used and prompt_version fields.
        """
        model_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "converted": 0})
        prompt_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "converted": 0})

        for activity in activities:
            ai_model = getattr(activity, "ai_model_used", None)
            prompt_version = getattr(activity, "prompt_version", None)

            if ai_model:
                model_stats[ai_model]["total"] += 1
                if activity.led_to_booking:
                    model_stats[ai_model]["converted"] += 1

            if prompt_version:
                prompt_stats[prompt_version]["total"] += 1
                if activity.led_to_booking:
                    prompt_stats[prompt_version]["converted"] += 1

        # Rank models
        model_rankings = []
        for model, stats in model_stats.items():
            if stats["total"] >= 5:
                rate = stats["converted"] / stats["total"]
                model_rankings.append(
                    {
                        "model": model,
                        "conversion_rate": round(rate, 4),
                        "sample": stats["total"],
                        "lift": round(self.calculate_lift(rate, baseline_rate), 2),
                    }
                )
        model_rankings.sort(key=lambda x: x["conversion_rate"], reverse=True)

        # Rank prompts
        prompt_rankings = []
        for prompt, stats in prompt_stats.items():
            if stats["total"] >= 5:
                rate = stats["converted"] / stats["total"]
                prompt_rankings.append(
                    {
                        "prompt_version": prompt,
                        "conversion_rate": round(rate, 4),
                        "sample": stats["total"],
                        "lift": round(self.calculate_lift(rate, baseline_rate), 2),
                    }
                )
        prompt_rankings.sort(key=lambda x: x["conversion_rate"], reverse=True)

        return {
            "best_model": model_rankings[0] if model_rankings else None,
            "model_rankings": model_rankings[:3],
            "best_prompt": prompt_rankings[0] if prompt_rankings else None,
            "prompt_rankings": prompt_rankings[:3],
        }

    def _default_patterns(self) -> dict[str, Any]:
        """Return default patterns when insufficient data."""
        return {
            "type": "what",
            "version": "2.0",
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": 0,
            "subject_patterns": {"winning": []},
            "pain_points": {"effective": [], "ineffective": []},
            "ctas": {"effective": []},
            "angles": {"rankings": []},
            "optimal_length": {},
            "personalization_lift": {},
            # Phase 24B additions
            "template_performance": {
                "top_templates": [],
                "bottom_templates": [],
                "total_templates_analyzed": 0,
            },
            "ab_test_insights": {"test_insights": [], "total_tests_analyzed": 0},
            "link_effectiveness": {
                "with_links_rate": None,
                "without_links_rate": None,
                "recommendation": "unknown",
            },
            "ai_model_performance": {
                "best_model": None,
                "model_rankings": [],
                "best_prompt": None,
                "prompt_rankings": [],
            },
            "note": "Insufficient data for pattern detection.",
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Extends BaseDetector
# [x] pattern_type = "what"
# [x] detect() method implemented
# [x] Subject line pattern analysis
# [x] Pain point effectiveness analysis
# [x] CTA effectiveness analysis
# [x] Message angle analysis
# [x] Optimal length by channel
# [x] Personalization lift calculation
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Phase 24B: Template performance analysis
# [x] Phase 24B: A/B test insights aggregation
# [x] Phase 24B: Link effectiveness analysis
# [x] Phase 24B: AI model performance analysis
