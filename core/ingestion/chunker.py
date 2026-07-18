from __future__ import annotations

import hashlib
from typing import TypedDict

import tree_sitter
import tree_sitter_javascript as ts_javascript
import tree_sitter_typescript as ts_typescript

from core.observability.logging import get_logger

logger = get_logger(__name__)

# Load languages
JS_LANG = tree_sitter.Language(ts_javascript.language())
TS_LANG = tree_sitter.Language(ts_typescript.language_typescript())

class CodeChunk(TypedDict):
    file_path: str
    start_line: int
    end_line: int
    symbol: str | None
    content: str
    content_hash: str

class Chunker:
    """Parses code files using tree-sitter and emits chunks for indexing."""

    def __init__(self) -> None:
        self.js_parser = tree_sitter.Parser(JS_LANG)
        self.ts_parser = tree_sitter.Parser(TS_LANG)

    def chunk_file(self, file_path: str, content: str) -> list[CodeChunk]:
        """Parse a single file and return its function/method chunks."""
        if file_path.endswith(".ts") or file_path.endswith(".tsx"):
            parser = self.ts_parser
        elif file_path.endswith(".js") or file_path.endswith(".jsx"):
            parser = self.js_parser
        else:
            return []

        tree = parser.parse(content.encode("utf-8"))
        root = tree.root_node

        chunks: list[CodeChunk] = []

        # Simple traversal looking for function declarations
        # In a real system, we'd use tree-sitter queries.
        def visit(node: tree_sitter.Node) -> None:
            if node.type in ("function_declaration", "method_definition", "arrow_function"):
                # Extract name if possible
                symbol_name = None
                if node.type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        symbol_name = content[name_node.start_byte:name_node.end_byte]
                elif node.type == "method_definition":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        symbol_name = content[name_node.start_byte:name_node.end_byte]

                chunk_content = content[node.start_byte:node.end_byte]
                
                # Create hash
                hasher = hashlib.sha256()
                hasher.update(chunk_content.encode("utf-8"))
                
                chunks.append({
                    "file_path": file_path,
                    "start_line": node.start_point[0] + 1,  # 1-indexed
                    "end_line": node.end_point[0] + 1,
                    "symbol": symbol_name,
                    "content": chunk_content,
                    "content_hash": hasher.hexdigest()
                })
            
            for child in node.children:
                visit(child)

        visit(root)
        return chunks
