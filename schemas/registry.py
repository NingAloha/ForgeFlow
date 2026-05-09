from __future__ import annotations

from pydantic import BaseModel

from .design import SystemDesignState
from .implementation import ImplementationStatusState
from .question_state import QuestionStateModel
from .solution import SolutionState
from .spec import SpecState
from .testing import TestReportState


STATE_MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    "spec": SpecState,
    "solution": SolutionState,
    "system_design": SystemDesignState,
    "implementation_status": ImplementationStatusState,
    "test_report": TestReportState,
    "question_state": QuestionStateModel,
}
