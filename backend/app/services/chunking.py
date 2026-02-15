"""Intelligent code chunking: AST-based for Python, regex-based for JS/TS."""

import ast
import logging
import re
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("codecontext.chunking")


@dataclass
class CodeChunk:
    """A logical chunk of source code."""
    file_path: str
    symbol: str
    code: str
    language: str
    start_line: int
    end_line: int


def chunk_file(file_path: str, content: str, language: str) -> list[CodeChunk]:
    """
    Chunk a file into logical code blocks.
    Uses AST parsing for Python, regex heuristics for JS/TS,
    and falls back to line-window chunking for other languages.
    """
    if language == "python":
        chunks = _chunk_python(file_path, content)
        if chunks:
            logger.debug("AST-chunked %s → %d chunks", file_path, len(chunks))
            return chunks

    if language in ("javascript", "typescript"):
        chunks = _chunk_javascript(file_path, content, language)
        if chunks:
            logger.debug("Regex-chunked %s → %d chunks", file_path, len(chunks))
            return chunks

    # Fallback: line-window chunking for any language
    chunks = _chunk_by_lines(file_path, content, language)
    logger.debug("Line-chunked %s → %d chunks (fallback)", file_path, len(chunks))
    return chunks


def _chunk_python(file_path: str, content: str) -> list[CodeChunk]:
    """Parse Python using the AST module to extract classes and functions."""
    chunks: list[CodeChunk] = []
    lines = content.splitlines()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.debug("Python AST parse failed for %s: %s", file_path, e)
        return []

    # Collect module-level docstring / imports as a preamble chunk
    first_node_line = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first_node_line = node.lineno
            break

    if first_node_line and first_node_line > 1:
        preamble = "\n".join(lines[: first_node_line - 1]).strip()
        if preamble and len(preamble.splitlines()) >= 3:
            chunks.append(CodeChunk(
                file_path=file_path,
                symbol="<module>",
                code=preamble,
                language="python",
                start_line=1,
                end_line=first_node_line - 1,
            ))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno or start
            code = "\n".join(lines[start - 1 : end])
            chunks.append(CodeChunk(
                file_path=file_path,
                symbol=node.name,
                code=code,
                language="python",
                start_line=start,
                end_line=end,
            ))

        elif isinstance(node, ast.ClassDef):
            start = node.lineno
            end = node.end_lineno or start
            code = "\n".join(lines[start - 1 : end])

            # If the class is small enough, keep it whole
            if (end - start) <= settings.MAX_CHUNK_LINES:
                chunks.append(CodeChunk(
                    file_path=file_path,
                    symbol=node.name,
                    code=code,
                    language="python",
                    start_line=start,
                    end_line=end,
                ))
            else:
                # Split class into its methods
                class_header_end = start
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_header_end = child.lineno - 1
                        break

                header = "\n".join(lines[start - 1 : class_header_end])
                if header.strip():
                    chunks.append(CodeChunk(
                        file_path=file_path,
                        symbol=f"{node.name}.<header>",
                        code=header,
                        language="python",
                        start_line=start,
                        end_line=class_header_end,
                    ))

                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        c_start = child.lineno
                        c_end = child.end_lineno or c_start
                        c_code = "\n".join(lines[c_start - 1 : c_end])
                        chunks.append(CodeChunk(
                            file_path=file_path,
                            symbol=f"{node.name}.{child.name}",
                            code=c_code,
                            language="python",
                            start_line=c_start,
                            end_line=c_end,
                        ))

    return chunks


# Regex patterns for JS/TS splitting
_JS_PATTERNS = [
    # export default function / export function
    re.compile(r"^(export\s+(?:default\s+)?(?:async\s+)?function\s+\w+)", re.MULTILINE),
    # function declarations
    re.compile(r"^((?:async\s+)?function\s+\w+)", re.MULTILINE),
    # const/let/var arrow functions or class expressions
    re.compile(r"^((?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>)", re.MULTILINE),
    # class declarations
    re.compile(r"^((?:export\s+(?:default\s+)?)?class\s+\w+)", re.MULTILINE),
]


def _chunk_javascript(file_path: str, content: str, language: str) -> list[CodeChunk]:
    """Split JS/TS files by function/class/export boundaries."""
    lines = content.splitlines()
    if not lines:
        return []

    # Find all boundary lines
    boundaries: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        for pattern in _JS_PATTERNS:
            match = pattern.match(line)
            if match:
                # Try to extract a symbol name
                symbol = _extract_js_symbol(line)
                boundaries.append((i, symbol))
                break

    if not boundaries:
        return []

    chunks: list[CodeChunk] = []

    # Preamble (imports, etc.) before first boundary
    if boundaries[0][0] > 0:
        preamble = "\n".join(lines[: boundaries[0][0]]).strip()
        if preamble and len(preamble.splitlines()) >= 2:
            chunks.append(CodeChunk(
                file_path=file_path,
                symbol="<imports>",
                code=preamble,
                language=language,
                start_line=1,
                end_line=boundaries[0][0],
            ))

    # Create chunks between boundaries
    for i, (line_idx, symbol) in enumerate(boundaries):
        start = line_idx
        end = boundaries[i + 1][0] - 1 if i + 1 < len(boundaries) else len(lines) - 1
        code = "\n".join(lines[start : end + 1]).rstrip()

        if code.strip():
            chunks.append(CodeChunk(
                file_path=file_path,
                symbol=symbol,
                code=code,
                language=language,
                start_line=start + 1,
                end_line=end + 1,
            ))

    return chunks


def _extract_js_symbol(line: str) -> str:
    """Try to extract a symbol name from a JS/TS declaration line."""
    patterns = [
        r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(\w+)",
        r"(?:export\s+)?(?:const|let|var)\s+(\w+)",
        r"(?:export\s+(?:default\s+)?)?class\s+(\w+)",
    ]
    for p in patterns:
        m = re.search(p, line)
        if m:
            return m.group(1)
    return "<anonymous>"


def _chunk_by_lines(
    file_path: str, content: str, language: str
) -> list[CodeChunk]:
    """Fallback: split file into fixed-size line windows with overlap."""
    lines = content.splitlines()
    if not lines:
        return []

    # Small files → single chunk
    if len(lines) <= settings.MAX_CHUNK_LINES:
        return [CodeChunk(
            file_path=file_path,
            symbol="<file>",
            code=content,
            language=language,
            start_line=1,
            end_line=len(lines),
        )]

    window = settings.FALLBACK_CHUNK_LINES
    overlap = 20
    chunks: list[CodeChunk] = []
    i = 0
    idx = 0

    while i < len(lines):
        end = min(i + window, len(lines))
        code = "\n".join(lines[i:end])
        chunks.append(CodeChunk(
            file_path=file_path,
            symbol=f"<block_{idx}>",
            code=code,
            language=language,
            start_line=i + 1,
            end_line=end,
        ))
        i += window - overlap
        idx += 1

    return chunks
