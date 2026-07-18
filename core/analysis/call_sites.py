from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict

_SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".next",
    ".cache",
    "coverage",
    "vendor",
}

_CODE_GLOBS = (
    "*.js",
    "*.jsx",
    "*.ts",
    "*.tsx",
    "*.mjs",
    "*.cjs",
    "*.py",
)


class CallSite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str
    line: int
    end_line: int
    symbol: str
    snippet: str
    kind: str  # import | call | require
    context_before: str = ""
    context_after: str = ""


@dataclass
class CallSiteFinder:
    """Locate imports and syntactic call sites for a package / symbols."""

    skip_dirs: set[str] = field(default_factory=lambda: set(_SKIP_DIRS))

    def find(
        self,
        repo: Path,
        package_name: str,
        symbols: list[str] | None = None,
        max_sites: int = 40,
    ) -> list[CallSite]:
        symbols = symbols or []
        bare = package_name.split("/")[-1]
        py_mod = bare.replace("-", "_")
        sites: list[CallSite] = []

        import_patterns = self._import_patterns(package_name, bare, py_mod)
        call_patterns = self._call_patterns(bare, py_mod, symbols, package_name)

        for path in self._iter_files(repo):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(path.relative_to(repo)).replace("\\", "/")
            lines = text.splitlines()
            # Collect local aliases from import/require lines in this file
            aliases = self._aliases_in_file(text, package_name, bare)

            for i, line in enumerate(lines):
                for kind, pat in import_patterns:
                    if pat.search(line):
                        sites.append(
                            self._site(rel, i + 1, i + 1, package_name, line, kind, lines, i)
                        )
                        break
                for sym, pat in call_patterns:
                    if pat.search(line):
                        sites.append(
                            self._site(rel, i + 1, i + 1, sym, line, "call", lines, i)
                        )
                for alias in aliases:
                    # default-export call: minimist(, express(, _
                    if re.search(rf"(?:^|[^\w.]){re.escape(alias)}\s*\(", line):
                        if "require" in line or "import " in line or "from " in line:
                            continue
                        sites.append(
                            self._site(rel, i + 1, i + 1, alias, line, "call", lines, i)
                        )

                if len(sites) >= max_sites:
                    return sites

        return sites

    def find_imports_only(self, repo: Path, package_name: str) -> list[str]:
        sites = self.find(repo, package_name, symbols=[], max_sites=50)
        files: list[str] = []
        seen: set[str] = set()
        for s in sites:
            if s.kind in ("import", "require") and s.file_path not in seen:
                seen.add(s.file_path)
                files.append(s.file_path)
        return files

    def _iter_files(self, repo: Path) -> list[Path]:
        out: list[Path] = []
        for pattern in _CODE_GLOBS:
            for f in repo.rglob(pattern):
                if any(part in self.skip_dirs for part in f.parts):
                    continue
                out.append(f)
        return out

    def _site(
        self,
        rel: str,
        start: int,
        end: int,
        symbol: str,
        line: str,
        kind: str,
        lines: list[str],
        idx: int,
    ) -> CallSite:
        before = "\n".join(lines[max(0, idx - 3) : idx])
        after = "\n".join(lines[idx + 1 : min(len(lines), idx + 4)])
        return CallSite(
            file_path=rel,
            line=start,
            end_line=end,
            symbol=symbol,
            snippet=line.strip(),
            kind=kind,
            context_before=before,
            context_after=after,
        )

    @staticmethod
    def _import_patterns(package_name: str, bare: str, py_mod: str) -> list[tuple[str, re.Pattern[str]]]:
        esc = re.escape(package_name)
        bare_esc = re.escape(bare)
        py_esc = re.escape(py_mod)
        sep = re.escape(bare).replace(r"\-", r"[_\-]")
        return [
            ("require", re.compile(rf"""require\s*\(\s*['"]{esc}(?:/[^'"]*)?['"]""")),
            ("import", re.compile(rf"""from\s+['"]{esc}(?:/[^'"]*)?['"]""")),
            ("import", re.compile(rf"""import\s+['"]{esc}(?:/[^'"]*)?['"]""")),
            ("import", re.compile(rf"""from\s+['"]@?{bare_esc}(?:/[^'"]*)?['"]""")),
            ("import", re.compile(rf"""^from\s+{sep}\b""", re.MULTILINE)),
            ("import", re.compile(rf"""^import\s+{py_esc}\b""", re.MULTILINE)),
            ("import", re.compile(rf"""import\s+\w+\s+from\s+['"]{esc}['"]""")),
        ]

    @staticmethod
    def _call_patterns(
        bare: str, py_mod: str, symbols: list[str], package_name: str
    ) -> list[tuple[str, re.Pattern[str]]]:
        patterns: list[tuple[str, re.Pattern[str]]] = []
        aliases = {bare, py_mod, f"_{bare}", f"_{py_mod}", "lodash", "_", package_name}
        for sym in symbols:
            if not sym or not re.match(r"^[A-Za-z_][\w.]*$", sym):
                continue
            leaf = sym.split(".")[-1]
            patterns.append(
                (sym, re.compile(rf"""(?:^|[^\w])(?:{re.escape(leaf)})\s*\(""")),
            )
            for alias in aliases:
                patterns.append(
                    (
                        f"{alias}.{leaf}",
                        re.compile(
                            rf"""(?:^|[^\w]){re.escape(alias)}\s*\.\s*{re.escape(leaf)}\s*\("""
                        ),
                    )
                )
        # Common express / framework member usage
        if bare in {"express"} or package_name == "express":
            for method in ("redirect", "send", "json", "render", "use", "get", "post"):
                patterns.append(
                    (
                        f"res.{method}",
                        re.compile(rf"""(?:^|[^\w])res\s*\.\s*{method}\s*\("""),
                    )
                )
        return patterns

    @staticmethod
    def _aliases_in_file(text: str, package_name: str, bare: str) -> set[str]:
        aliases: set[str] = set()
        # const x = require('pkg') / import x from 'pkg'
        for m in re.finditer(
            rf"""(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*['"]{re.escape(package_name)}['"]\s*\)""",
            text,
        ):
            aliases.add(m.group(1))
        for m in re.finditer(
            rf"""import\s+(\w+)\s+from\s+['"]{re.escape(package_name)}['"]""",
            text,
        ):
            aliases.add(m.group(1))
        for m in re.finditer(
            rf"""(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*['"]{re.escape(bare)}['"]\s*\)""",
            text,
        ):
            aliases.add(m.group(1))
        if bare == "lodash":
            aliases.add("_")
        return aliases
