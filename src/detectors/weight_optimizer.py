"""
FILE: src/detectors/weight_optimizer.py
PURPOSE: ALS Weight Optimizer using scipy for optimal weight calculation
PHASE: 16 (Conversion Intelligence)
TASK: 16A-005
DEPENDENCIES:
  - scipy
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument

This module optimizes ALS component weights based on historical conversion data.
Uses scipy.optimize.minimize with constraints to find weights that maximize
correlation between ALS score and conversion probability.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from scipy import optimize
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import LeadStatus
from src.models.lead import Lead

# Default ALS weights (from blueprint)
DEFAULT_WEIGHTS = {
    "data_quality": 0.20,
    "authority": 0.25,
    "company_fit": 0.25,
    "timing": 0.15,
    "risk": 0.15,
}

# Component order for array operations
COMPONENT_ORDER = ["data_quality", "authority", "company_fit", "timing", "risk"]


class WeightOptimizer:
    """
    Optimizes ALS component weights based on conversion outcomes.

    Uses scipy's SLSQP optimizer with constraints:
    - All weights must sum to 1.0
    - Each weight must be between 0.05 and 0.50
    - Minimizes negative correlation (to maximize positive correlation)
    """

    def __init__(
        self,
        min_weight: float = 0.05,
        max_weight: float = 0.50,
        min_samples: int = 50,
    ):
        """
        Initialize optimizer.

        Args:
            min_weight: Minimum weight per component
            max_weight: Maximum weight per component
            min_samples: Minimum conversion samples required
        """
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.min_samples = min_samples

    async def optimize_weights(
        self,
        db: AsyncSession,
        client_id: UUID,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        """
        Optimize ALS weights for a client based on conversion history.

        Args:
            db: Database session
            client_id: Client UUID
            lookback_days: Days of history to analyze

        Returns:
            Dict with optimized weights, confidence, and metadata
        """
        # Get leads with ALS components and outcomes
        leads = await self._get_leads_with_components(
            db, client_id, lookback_days
        )

        if len(leads) < self.min_samples:
            return {
                "weights": DEFAULT_WEIGHTS.copy(),
                "confidence": 0.0,
                "sample_size": len(leads),
                "optimization_status": "insufficient_data",
                "note": f"Need at least {self.min_samples} leads with outcomes",
            }

        # Extract component arrays and conversion labels
        X, y = self._prepare_data(leads)

        if X is None or y is None or len(X) < self.min_samples:
            return {
                "weights": DEFAULT_WEIGHTS.copy(),
                "confidence": 0.0,
                "sample_size": len(leads),
                "optimization_status": "insufficient_component_data",
                "note": "Not enough leads have ALS component scores",
            }

        # Run optimization (X and y guaranteed non-None at this point)
        result = self._optimize(X, y)

        # Convert to dict
        optimized_weights = {
            COMPONENT_ORDER[i]: round(result["weights"][i], 3)
            for i in range(len(COMPONENT_ORDER))
        }

        return {
            "weights": optimized_weights,
            "confidence": result["confidence"],
            "sample_size": len(leads),
            "optimization_status": result["status"],
            "correlation_improvement": result.get("improvement"),
            "iterations": result.get("iterations"),
        }

    async def _get_leads_with_components(
        self,
        db: AsyncSession,
        client_id: UUID,
        lookback_days: int,
    ) -> list[Lead]:
        """Get leads with ALS components and definitive outcomes."""
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        # Use individual ALS component fields instead of als_components JSONB
        stmt = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.als_data_quality.isnot(None),  # Ensure components exist
                Lead.status.in_([
                    LeadStatus.CONVERTED,
                    LeadStatus.BOUNCED,
                    LeadStatus.UNSUBSCRIBED,
                ]),
                Lead.created_at >= cutoff,
                Lead.deleted_at.is_(None),
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    def _prepare_data(
        self,
        leads: list[Lead],
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """
        Prepare component matrix and conversion labels.

        Returns:
            X: Component matrix (n_leads x 5)
            y: Conversion labels (0 or 1)
        """
        X_rows = []
        y_vals = []

        for lead in leads:
            # Build components dict from individual Lead fields
            components = {
                "data_quality": lead.als_data_quality,
                "authority": lead.als_authority,
                "company_fit": lead.als_company_fit,
                "timing": lead.als_timing,
                "risk": lead.als_risk,
            }

            # Build row in component order
            row = []
            for component in COMPONENT_ORDER:
                value = components.get(component)
                if value is None:
                    break
                row.append(float(value))

            if len(row) != len(COMPONENT_ORDER):
                continue  # Skip incomplete records

            X_rows.append(row)
            # Check status as string since it may be stored as string in DB
            lead_status = lead.status.value if hasattr(lead.status, 'value') else lead.status
            y_vals.append(1 if lead_status == LeadStatus.CONVERTED.value else 0)

        if not X_rows:
            return None, None

        return np.array(X_rows), np.array(y_vals)

    def _optimize(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> dict[str, Any]:
        """
        Run scipy optimization to find optimal weights.

        Uses SLSQP with:
        - Equality constraint: weights sum to 1
        - Bounds: each weight in [min_weight, max_weight]
        - Objective: minimize negative correlation
        """
        n_components = X.shape[1]

        # Initial weights (equal)
        x0 = np.ones(n_components) / n_components

        # Bounds for each weight
        bounds = [(self.min_weight, self.max_weight)] * n_components

        # Constraint: weights sum to 1
        constraints = {
            "type": "eq",
            "fun": lambda w: np.sum(w) - 1.0,
        }

        # Calculate baseline correlation with default weights
        default_w = np.array([DEFAULT_WEIGHTS[c] for c in COMPONENT_ORDER])
        baseline_corr = self._calculate_correlation(X, y, default_w)

        # Objective: minimize negative correlation (maximize correlation)
        def objective(weights):
            return -self._calculate_correlation(X, y, weights)

        # Run optimization
        result = optimize.minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 100, "disp": False},
        )

        # Calculate optimized correlation
        optimized_corr = self._calculate_correlation(X, y, result.x)

        # Calculate confidence based on improvement and sample size
        improvement = optimized_corr - baseline_corr
        sample_factor = min(1.0, len(y) / 500)
        confidence = min(0.95, max(0.0, improvement * 2 + sample_factor * 0.3))

        return {
            "weights": result.x.tolist(),
            "status": "success" if result.success else "partial",
            "confidence": round(confidence, 3),
            "baseline_correlation": round(baseline_corr, 4),
            "optimized_correlation": round(optimized_corr, 4),
            "improvement": round(improvement, 4),
            "iterations": result.nit,
        }

    def _calculate_correlation(
        self,
        X: np.ndarray,
        y: np.ndarray,
        weights: np.ndarray,
    ) -> float:
        """Calculate correlation between weighted score and conversion."""
        # Calculate weighted scores
        scores = X @ weights

        # Handle edge cases
        if np.std(scores) == 0 or np.std(y) == 0:
            return 0.0

        # Pearson correlation
        correlation = np.corrcoef(scores, y)[0, 1]

        if np.isnan(correlation):
            return 0.0

        return correlation


async def optimize_client_weights(
    db: AsyncSession,
    client_id: UUID,
) -> dict[str, Any]:
    """
    Convenience function to optimize weights for a client.

    Args:
        db: Database session
        client_id: Client UUID

    Returns:
        Optimized weights result
    """
    optimizer = WeightOptimizer()
    return await optimizer.optimize_weights(db, client_id)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] scipy.optimize.minimize with SLSQP
# [x] Constraint: weights sum to 1.0
# [x] Bounds: each weight in [0.05, 0.50]
# [x] Correlation-based objective function
# [x] DEFAULT_WEIGHTS fallback
# [x] Minimum sample validation
# [x] Confidence calculation
# [x] Correlation improvement tracking
# [x] All functions have type hints
# [x] All functions have docstrings
