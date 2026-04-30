"""
Chunker - Document chunking strategies

Splits knowledge-type documents into chunks for vector storage.
Each chunk is independently embedded and stored in ChromaDB.

Strategies:
- Recursive: Split by heading → paragraph → sentence (for PRD)
- Endpoint: Split OpenAPI spec by path+method (for API_DOC)
- NoSplit: Keep short documents intact (for BEST_PRACTICE, CODE_EXAMPLE, TEST_PATTERN)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ChunkResult:
    content: str
    chunk_index: int


class BaseChunkStrategy:
    """Base class for chunk strategies"""

    def chunk(self, content: str) -> List[ChunkResult]:
        raise NotImplementedError


class RecursiveStrategy(BaseChunkStrategy):
    """
    Recursive character splitting by natural boundaries.

    Priority: headings → paragraphs → sentences → lines
    """

    SEPARATORS: List[str] = ['\n## ', '\n### ', '\n#### ', '\n\n', '。', '；', '\n']

    def __init__(self, chunk_size: int = 512, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, content: str) -> List[ChunkResult]:
        content = content.strip()
        if not content:
            return []

        return self._split(content, self.SEPARATORS, 0)

    def _split(
        self,
        text: str,
        separators: List[str],
        depth: int,
    ) -> List[ChunkResult]:
        if len(text) <= self.chunk_size or depth >= len(separators):
            return [ChunkResult(content=text, chunk_index=0)]

        sep = separators[depth]
        parts = self._split_by_separator(text, sep)

        if len(parts) <= 1:
            return self._split(text, separators, depth + 1)

        results: List[ChunkResult] = []
        for part in parts:
            if len(part) > self.chunk_size:
                sub_results = self._split(part, separators, depth + 1)
                results.extend(sub_results)
            else:
                results.append(ChunkResult(content=part, chunk_index=0))

        # Renumber chunk_index
        for i, r in enumerate(results):
            r.chunk_index = i

        return results

    @staticmethod
    def _split_by_separator(text: str, separator: str) -> List[str]:
        """
        Split text by separator, keeping the separator with the following content.

        Example with separator='\\n## ':
          Input:  'intro\\n## Section 1\\ncontent\\n## Section 2'
          Output: ['intro', '## Section 1\\ncontent', '## Section 2']
        """
        if not separator:
            return [text] if text else []

        parts = text.split(separator)
        if len(parts) <= 1:
            return parts

        result: List[str] = []
        result.append(parts[0])

        sep_clean = separator.strip()
        for part in parts[1:]:
            if part.strip():
                result.append(f'{sep_clean}\n{part}')
            else:
                result[-1] = result[-1] + separator + part

        return [r for r in result if r.strip()]


class EndpointStrategy(BaseChunkStrategy):
    """
    Split OpenAPI spec by endpoint (path + method).

    Each path+method becomes one chunk, preserving the full endpoint definition.
    """

    def chunk(self, content: str) -> List[ChunkResult]:
        spec = self._parse_spec(content)
        if not spec:
            return [ChunkResult(content=content, chunk_index=0)]

        paths = spec.get('paths', {})
        if not paths:
            return [ChunkResult(content=content, chunk_index=0)]

        base_url = self._extract_base_url(spec)
        info = spec.get('info', {})
        doc_title = info.get('title', 'API Document')

        chunks: List[ChunkResult] = []
        index = 0

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() not in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH'):
                    continue

                chunk_text = self._build_endpoint_chunk(
                    doc_title, base_url, path, method, details
                )
                chunks.append(ChunkResult(content=chunk_text, chunk_index=index))
                index += 1

        return chunks if chunks else [ChunkResult(content=content, chunk_index=0)]

    @staticmethod
    def _parse_spec(content: str) -> Dict | None:
        try:
            if content.strip().startswith('{') or content.strip().startswith('['):
                return json.loads(content)
            import yaml
            result = yaml.safe_load(content)
            return result if isinstance(result, dict) else None
        except Exception:
            return None

    @staticmethod
    def _extract_base_url(spec: Dict) -> str:
        if 'servers' in spec:
            servers = spec['servers']
            if servers:
                return str(servers[0].get('url', ''))
        elif 'host' in spec:
            host = spec['host']
            base_path = spec.get('basePath', '')
            schemes = spec.get('schemes', ['https'])
            scheme = schemes[0] if schemes else 'https'
            return f'{scheme}://{host}{base_path}'
        return ''

    @staticmethod
    def _build_endpoint_chunk(
        doc_title: str,
        base_url: str,
        path: str,
        method: str,
        details: Dict,
    ) -> str:
        lines = [
            f'# {doc_title}',
            f'## {method.upper()} {path}',
            '',
        ]

        summary = details.get('summary', details.get('description', ''))
        if summary:
            lines.append(summary)
            lines.append('')

        if base_url:
            lines.append(f'**Base URL**: {base_url}')
            lines.append(f'**Full URL**: {base_url}{path}')
            lines.append('')

        parameters = details.get('parameters', [])
        if parameters:
            lines.append('### Parameters')
            for param in parameters:
                name = param.get('name', '')
                param_in = param.get('in', '')
                required = 'required' if param.get('required') else 'optional'
                desc = param.get('description', '')
                lines.append(f'- `{name}` ({param_in}, {required}): {desc}')
            lines.append('')

        request_body = details.get('requestBody', {})
        if request_body:
            lines.append('### Request Body')
            rb_desc = request_body.get('description', '')
            if rb_desc:
                lines.append(rb_desc)
            content = request_body.get('content', {})
            for content_type in content:
                lines.append(f'- Content-Type: {content_type}')
            lines.append('')

        responses = details.get('responses', {})
        if responses:
            lines.append('### Responses')
            for status_code, response in responses.items():
                resp_desc = response.get('description', '')
                lines.append(f'- `{status_code}`: {resp_desc}')
            lines.append('')

        return '\n'.join(lines)


class NoSplitStrategy(BaseChunkStrategy):
    """
    Keep short documents as a single chunk.

    Falls back to RecursiveStrategy if content exceeds max_tokens.
    """

    def __init__(self, max_tokens: int = 512) -> None:
        self.max_tokens = max_tokens

    def chunk(self, content: str) -> List[ChunkResult]:
        content = content.strip()
        if not content:
            return []

        if len(content) <= self.max_tokens:
            return [ChunkResult(content=content, chunk_index=0)]

        recursive = RecursiveStrategy(chunk_size=self.max_tokens, overlap=50)
        return recursive.chunk(content)


class Chunker:
    """
    Document chunker - selects strategy by document type.
    """

    STRATEGIES: Dict[str, BaseChunkStrategy] = {
        'prd': RecursiveStrategy(chunk_size=512, overlap=50),
        'api_doc': EndpointStrategy(),
        'best_practice': NoSplitStrategy(max_tokens=512),
        'code_example': NoSplitStrategy(max_tokens=512),
        'test_pattern': NoSplitStrategy(max_tokens=512),
    }

    DEFAULT_STRATEGY = RecursiveStrategy(chunk_size=512, overlap=50)

    def chunk(self, doc_type: str, content: str) -> List[ChunkResult]:
        strategy = self.STRATEGIES.get(doc_type, self.DEFAULT_STRATEGY)
        return strategy.chunk(content)
