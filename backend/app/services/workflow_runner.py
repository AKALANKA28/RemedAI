from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.graph.workflow import build_workflow


@dataclass(slots=True)
class WorkflowRunner:
    runtime_dir: str
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = get_logger(__name__)

    def _invoke(self, *, query: str, input_paths: list[str], case_label: str) -> dict:
        self._logger.info('Invoke workflow: case_label=%s input_paths=%d', case_label, len(input_paths))
        graph = build_workflow()
        initial_state = {
            'user_query': query,
            'input_paths': input_paths,
            'case_label': case_label,
        }
        result = graph.invoke(initial_state, config={'configurable': {'thread_id': case_label}})
        return result.get('final_bundle') or result

    def run_sample(self, sample_id: str, query: str) -> dict:
        sample_dir = Path('data/sample_inputs') / sample_id
        if not sample_dir.exists():
            raise FileNotFoundError(f'Sample not found: {sample_id}')
        input_paths = sorted(str(path) for path in sample_dir.iterdir() if path.is_file())
        self._logger.info('Run sample: sample_id=%s input_paths=%d', sample_id, len(input_paths))
        return self._invoke(query=query, input_paths=input_paths, case_label=sample_id)

    def run_text_case(self, query: str, input_paths: list[str], case_label: str) -> dict:
        self._logger.info('Run text case: case_label=%s input_paths=%d', case_label, len(input_paths))
        return self._invoke(query=query, input_paths=input_paths, case_label=case_label)


_runner = WorkflowRunner(runtime_dir=settings.runtime_dir)


def get_runner() -> WorkflowRunner:
    return _runner
