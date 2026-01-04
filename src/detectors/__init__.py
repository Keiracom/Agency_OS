"""
FILE: src/detectors/__init__.py
PURPOSE: Conversion Intelligence Detectors Package
PHASE: 16 (Conversion Intelligence)
TASK: 16A-003, 16B, 16C, 16D
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
from src.detectors.who_detector import WhoDetector
from src.detectors.what_detector import WhatDetector
from src.detectors.when_detector import WhenDetector
from src.detectors.how_detector import HowDetector
from src.detectors.weight_optimizer import WeightOptimizer, optimize_client_weights

__all__ = [
    # Base
    "BaseDetector",
    # Detectors
    "WhoDetector",
    "WhatDetector",
    "WhenDetector",
    "HowDetector",
    # Optimizer
    "WeightOptimizer",
    "optimize_client_weights",
]
