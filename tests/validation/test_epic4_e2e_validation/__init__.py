"""End-to-end validation pipeline for Epic 4 forecasting and insights - facade for backward compatibility.

Story 4.10 AC1-AC4: Comprehensive validation of forecast accuracy, insight quality,
and recommendation alignment against MVP success criteria.

Targets:
- Forecast accuracy: MAPE <=15% (NFR10)
- Insight relevance: >=75%
- Recommendation alignment: >=80%
"""

# Re-export all public API from new modules for backward compatibility
from .models import Epic4ValidationResult
from .orchestrator import Epic4ValidationOrchestrator, create_comprehensive_test_data
from .test_custom_thresholds import TestCustomThresholds
from .test_improvement_recommendations import TestImprovementRecommendations
from .test_orchestrator import TestOrchestrator
from .test_validation_result import TestValidationResult

__all__ = [
    "Epic4ValidationOrchestrator",
    "Epic4ValidationResult",
    "TestOrchestrator",
    "TestValidationResult",
    "TestImprovementRecommendations",
    "TestCustomThresholds",
    "create_comprehensive_test_data",
]
