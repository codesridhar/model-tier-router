"""Optional classifier implementations.

Classifier modules are not imported by :mod:`model_router`, so the core package keeps only its
Pydantic dependency. Import an implementation explicitly after installing its corresponding
extra.
"""

from .sklearn import TfidfClassifier, TrainingExample

__all__ = ["TfidfClassifier", "TrainingExample"]
