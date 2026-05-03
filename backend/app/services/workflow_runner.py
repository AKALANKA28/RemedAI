from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import settings
from backend.app.graph.workflow import build_workflow
from backend.app.services.logging_utils import get_app_logger
from backend.app.tools.tender_fetch import fetch_official_tender

logger = get_app_logger('workflow')


@dataclass(slots=True)
class WorkflowRunner:
    runtime_dir: str

    def _invoke(self, *, query: str, input_paths: list[str], case_label: str) -> dict:
        logger.info('Workflow start case_label=%s input_files=%s', case_label, len(input_paths))
        graph = build_workflow()
        initial_state = {
            'user_query': query,
            'input_paths': input_paths,
            'case_label': case_label,
        }
        result = graph.invoke(initial_state, config={'configurable': {'thread_id': case_label}})
        final = result.get('final_bundle') or result
        logger.info(
            'Workflow complete case_id=%s recommendation=%s',
            final.get('case_id', case_label),
            final.get('recommendation', 'n/a'),
        )
        return final

    def run_sample(self, sample_id: str, query: str) -> dict:
        logger.info('Sample analysis requested sample_id=%s', sample_id)
        sample_dir = Path('data/sample_inputs') / sample_id
        if not sample_dir.exists():
            raise FileNotFoundError(f'Sample not found: {sample_id}')
        input_paths = sorted(str(path) for path in sample_dir.iterdir() if path.is_file())
        return self._invoke(query=query, input_paths=input_paths, case_label=sample_id)

    def run_text_case(self, query: str, input_paths: list[str], case_label: str) -> dict:
        logger.info('Text analysis requested case_label=%s input_files=%s', case_label, len(input_paths))
        return self._invoke(query=query, input_paths=input_paths, case_label=case_label)

    def run_tender_url(self, *, source: str, tender_url: str, query: str) -> dict:
        logger.info('URL analysis requested source=%s url=%s', source, tender_url)
        fetched = fetch_official_tender(source, tender_url, self.runtime_dir)
        logger.info(
            'Tender fetched title=%s document=%s local_files=%s',
            fetched['title'],
            fetched['document_url'],
            len(fetched['local_paths']),
        )
        result = self._invoke(
            query=query,
            input_paths=fetched['local_paths'],
            case_label=fetched['case_label'],
        )
        result['source'] = fetched
        result.setdefault('artifacts', {})['saved_tender_document'] = fetched['saved_document_path']
        result.setdefault('artifacts', {})['source_url'] = fetched['source_url']
        result.setdefault('artifacts', {})['document_url'] = fetched['document_url']
        return result


_runner = WorkflowRunner(runtime_dir=settings.runtime_dir)


def get_runner() -> WorkflowRunner:
    return _runner
