"""
FILE: src/detectors/__init__.py
PURPOSE: Conversion Intelligence Detectors Package
PHASE: 16 (Conversion Intelligence), Phase 24E (Downstream Outcomes)
TASK: 16A-003, 16B, 16C, 16D, OUTCOME-005
DEPENDENCIES:
  - src/models/conversion_patterns.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only
"""

from src.detectors.base import BaseDetector
from src.detectors.funnel_detector import FunnelDetector
from src.detectors.how_detector import HowDetector
from src.detectors.weight_optimizer import WeightOptimizer, optimize_client_weights
from src.detectors.what_detector import WhatDetector
from src.detectors.when_detector import WhenDetector
from src.detectors.who_detector import WhoDetector

__all__ = [
    # Base
    "BaseDetector",
    # Detectors
    "WhoDetector",
    "WhatDetector",
    "WhenDetector",
    "HowDetector",
    "FunnelDetector",
    # Optimizer
    "WeightOptimizer",
    "optimize_client_weights",
]
