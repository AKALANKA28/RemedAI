from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import requests
from langsmith import traceable

from backend.app.services.logging_utils import get_app_logger

logger = get_app_logger('tool.tender_fetch')


ALLOWED_SOURCES = {
    # 'ministry_of_health': {
    #     'label': 'Ministry of Health Sri Lanka',
    #     'base_url': 'https://www.health.gov.lk/tenders-procuments/',
    #     'allowed_hosts': {'health.gov.lk', 'www.health.gov.lk'},
    #     'issuer': 'Ministry of Health Sri Lanka',
    # },
    'waterboard': {
        'label': 'National Water Supply and Drainage Board',
        'base_url': 'https://www.waterboard.lk/tenders/',
        'allowed_hosts': {'waterboard.lk', 'www.waterboard.lk'},
        'allowed_document_hosts': {'drive.google.com', 'docs.google.com'},
        'issuer': 'National Water Supply and Drainage Board',
    },
}

DOWNLOAD_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip'}
PARSER_SUPPORTED_EXTENSIONS = {'.md', '.txt', '.json', '.docx', '.pdf'}


@dataclass(slots=True)
class TenderDownload:
    source: str
    source_url: str
    document_url: str
    local_paths: list[str]
    title: str
    issuer: str
    issue_date: str | None
    case_label: str


class TenderHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._active_link: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag.lower() == 'a' and attrs_dict.get('href'):
            self._active_link = {'href': attrs_dict['href'] or '', 'text': ''}

    def handle_data(self, data: str) -> None:
        cleaned = ' '.join(data.split())
        if not cleaned:
            return
        self.text_parts.append(cleaned)
        if self._active_link is not None:
            self._active_link['text'] = f"{self._active_link['text']} {cleaned}".strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == 'a' and self._active_link is not None:
            self.links.append(self._active_link)
            self._active_link = None

    @property
    def text(self) -> str:
        return '\n'.join(self.text_parts)


def _source_config(source: str) -> dict[str, Any]:
    if source not in ALLOWED_SOURCES:
        raise ValueError(f'Unsupported tender source: {source}')
    return ALLOWED_SOURCES[source]


def _validate_url(source: str, url: str, *, allow_document_hosts: bool = False) -> str:
    config = _source_config(source)
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'}:
        raise ValueError('Tender URL must be an HTTP or HTTPS URL.')
    allowed_hosts = set(config['allowed_hosts'])
    if allow_document_hosts:
        allowed_hosts.update(config.get('allowed_document_hosts', set()))
    if parsed.netloc.lower() not in allowed_hosts:
        allowed = ', '.join(sorted(allowed_hosts))
        raise ValueError(f'Tender URL host must be one of: {allowed}')
    return url


def _slug(value: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9_-]+', '_', value.lower()).strip('_')
    return slug[:48] or 'official_tender'


def _extension_from_response(url: str, response: requests.Response) -> str:
    path_suffix = Path(unquote(urlparse(url).path)).suffix.lower()
    if path_suffix:
        return path_suffix
    content_type = response.headers.get('content-type', '').split(';', 1)[0].strip()
    return mimetypes.guess_extension(content_type) or '.bin'


def _filename_from_content_disposition(response: requests.Response) -> str | None:
    header = response.headers.get('content-disposition', '')
    if not header:
        return None
    match = re.search(r"filename\*=(?:utf-8''|UTF-8'')?([^;]+)", header)
    if match:
        return unquote(match.group(1)).strip('"')
    match = re.search(r'filename="?([^";]+)"?', header)
    if match:
        return match.group(1).strip()
    return None


def _sniff_extension(response: requests.Response) -> str | None:
    signature = response.content[:8]
    if signature.startswith(b'%PDF'):
        return '.pdf'
    return None


def _filename_from_url(url: str, response: requests.Response) -> str:
    content_disposition = _filename_from_content_disposition(response)
    if content_disposition:
        return content_disposition
    parsed = urlparse(url)
    candidate = Path(unquote(parsed.path)).name
    if candidate and Path(candidate).suffix:
        return candidate
    extension = _extension_from_response(url, response)
    return f'tender_document{extension}'


def _select_download_link(source_url: str, html: str) -> tuple[str, str]:
    parser = TenderHTMLParser()
    parser.feed(html)
    scored_links: list[tuple[int, str, str]] = []

    for link in parser.links:
        href = link.get('href', '')
        text = link.get('text', '')
        absolute_url = urljoin(source_url, href)
        suffix = Path(unquote(urlparse(absolute_url).path)).suffix.lower()
        score = 0
        if suffix in DOWNLOAD_EXTENSIONS:
            score += 10
        if 'download' in text.lower():
            score += 5
        if score:
            scored_links.append((score, absolute_url, text))

    if not scored_links:
        return source_url, parser.text

    scored_links.sort(key=lambda item: item[0], reverse=True)
    return scored_links[0][1], parser.text


def _drive_file_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in {'drive.google.com', 'docs.google.com'}:
        return None
    if parsed.path.startswith('/file/d/'):
        parts = parsed.path.split('/')
        return parts[3] if len(parts) > 3 else None
    if parsed.path.startswith('/uc') or parsed.path.startswith('/open'):
        query = dict(part.split('=', 1) for part in parsed.query.split('&') if '=' in part)
        return query.get('id')
    return None


def _direct_download_url(url: str) -> str:
    file_id = _drive_file_id(url)
    if not file_id:
        return url
    return f'https://drive.google.com/uc?export=download&id={file_id}'


def _infer_listing_title(page_text: str, document_url: str) -> tuple[str, str | None]:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if re.fullmatch(r'\d{2}-\d{2}-\d{4}', line) and index + 1 < len(lines):
            return lines[index + 1], line

    fallback = Path(unquote(urlparse(document_url).path)).stem.replace('-', ' ').replace('_', ' ').strip()
    return fallback or 'Official tender notice', None


def _write_metadata_file(
    folder: Path,
    *,
    title: str,
    issuer: str,
    source_url: str,
    document_url: str,
    issue_date: str | None,
    page_text: str,
) -> Path:
    metadata_path = folder / 'source_notice.md'
    metadata_path.write_text(
        '\n'.join(
            [
                f'Project title: {title}',
                f'Issuer: {issuer}',
                f'Issue date: {issue_date or "Unknown"}',
                f'Source URL: {source_url}',
                f'Document URL: {document_url}',
                '',
                '## Source Page Text',
                page_text[:6000],
            ]
        ),
        encoding='utf-8',
    )
    return metadata_path


@traceable(name='fetch_official_tender', run_type='tool')
def fetch_official_tender(source: str, tender_url: str, runtime_dir: str) -> dict[str, Any]:
    """Fetch one official tender page/document and save local files for the agent workflow."""
    config = _source_config(source)
    source_url = _validate_url(source, tender_url or config['base_url'])
    logger.info('Fetch start source=%s url=%s', source, source_url)
    session = requests.Session()
    headers = {'User-Agent': 'RemedAI tender analysis bot/1.0'}

    page_response = session.get(source_url, headers=headers, timeout=30)
    page_response.raise_for_status()
    content_type = page_response.headers.get('content-type', '')
    logger.info('Fetched source page status=%s content_type=%s', page_response.status_code, content_type)

    page_text = ''
    document_url = source_url
    document_response = page_response
    if 'text/html' in content_type.lower():
        document_url, page_text = _select_download_link(source_url, page_response.text)
        logger.info('Selected document_url=%s', document_url)
        if document_url != source_url:
            download_url = _direct_download_url(document_url)
            _validate_url(source, download_url, allow_document_hosts=True)
            if download_url != document_url:
                logger.info('Resolved document_download_url=%s', download_url)
            document_response = session.get(download_url, headers=headers, timeout=60)
            document_response.raise_for_status()
            logger.info(
                'Fetched document status=%s bytes=%s',
                document_response.status_code,
                len(document_response.content),
            )
    else:
        parser = TenderHTMLParser()
        parser.feed(page_response.text if 'text/' in content_type.lower() else '')
        page_text = parser.text

    title, issue_date = _infer_listing_title(page_text, document_url)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    case_label = f'{source}-{_slug(title)}'
    folder = Path(runtime_dir) / 'fetched_tenders' / f'{_slug(title)}-{timestamp}'
    folder.mkdir(parents=True, exist_ok=True)

    document_name = _filename_from_url(document_url, document_response)
    if Path(document_name).suffix.lower() == '.bin':
        sniffed = _sniff_extension(document_response)
        if sniffed:
            document_name = f'{Path(document_name).stem}{sniffed}'
    document_path = folder / document_name
    document_path.write_bytes(document_response.content)
    metadata_path = _write_metadata_file(
        folder,
        title=title,
        issuer=config['issuer'],
        source_url=source_url,
        document_url=document_url,
        issue_date=issue_date,
        page_text=page_text,
    )
    logger.info('Saved tender files folder=%s document=%s metadata=%s', folder, document_path.name, metadata_path.name)

    input_paths = [str(metadata_path)]
    if document_path.suffix.lower() in PARSER_SUPPORTED_EXTENSIONS:
        input_paths.append(str(document_path))

    download = TenderDownload(
        source=source,
        source_url=source_url,
        document_url=document_url,
        local_paths=input_paths,
        title=title,
        issuer=config['issuer'],
        issue_date=issue_date,
        case_label=case_label,
    )
    return {
        'source': download.source,
        'source_url': download.source_url,
        'document_url': download.document_url,
        'local_paths': download.local_paths,
        'saved_document_path': str(document_path),
        'title': download.title,
        'issuer': download.issuer,
        'issue_date': download.issue_date,
        'case_label': download.case_label,
    }
