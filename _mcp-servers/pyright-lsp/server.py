#!/usr/bin/env python3
"""
Pyright LSP MCP Server

A standalone MCP server that wraps pyright-langserver and exposes LSP operations
as Claude Code tools. Replaces OMC's hardcoded pylsp with pyright natively.

Register with: claude mcp add --transport stdio pyright-lsp python3 /path/to/server.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote as url_quote

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# LSP Client — manages pyright-langserver over JSON-RPC / stdio
# ---------------------------------------------------------------------------

WORKSPACE_MARKERS = [
    "pyproject.toml", "setup.py", "setup.cfg", "Pipfile",
    "requirements.txt", "tox.ini", ".git", "package.json",
    "Cargo.toml", "go.mod",
]

LANG_IDS = {
    ".py": "python", ".pyw": "python",
    ".pyi": "python",
}

SYMBOL_KINDS = {
    1: "File", 2: "Module", 3: "Namespace", 4: "Package", 5: "Class",
    6: "Method", 7: "Property", 8: "Field", 9: "Constructor", 10: "Enum",
    11: "Interface", 12: "Function", 13: "Variable", 14: "Constant",
    15: "String", 16: "Number", 17: "Boolean", 18: "Array", 19: "Object",
    20: "Key", 21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event",
    25: "Operator", 26: "TypeParameter",
}

SEVERITY_NAMES = {1: "Error", 2: "Warning", 3: "Information", 4: "Hint"}


def find_workspace_root(file_path: str) -> str:
    d = Path(file_path).resolve().parent
    while d != d.parent:
        if any((d / m).exists() for m in WORKSPACE_MARKERS):
            return str(d)
        d = d.parent
    return str(Path(file_path).resolve().parent)


def file_uri(path: str) -> str:
    p = Path(path).resolve()
    return "file://" + url_quote(str(p), safe="/:")


def uri_to_path(uri: str) -> str:
    if uri.startswith("file://"):
        from urllib.parse import unquote
        return unquote(uri[7:])
    return uri


def fmt_pos(line: int, char: int) -> str:
    return f"{line + 1}:{char + 1}"


def fmt_range(r: dict) -> str:
    s = fmt_pos(r["start"]["line"], r["start"]["character"])
    e = fmt_pos(r["end"]["line"], r["end"]["character"])
    return s if s == e else f"{s}-{e}"


def fmt_location(loc: dict) -> str:
    uri = loc.get("uri") or loc.get("targetUri", "")
    path = uri_to_path(uri)
    r = loc.get("range") or loc.get("targetRange") or loc.get("targetSelectionRange")
    if not r:
        return path
    return f"{path}:{fmt_range(r)}"


class LspClient:
    def __init__(self):
        self._proc: asyncio.subprocess.Process | None = None
        self._req_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._open_docs: set[str] = set()
        self._diagnostics: dict[str, list] = {}
        self._workspace_root: str | None = None
        self._reader_task: asyncio.Task | None = None
        self._initialized = False

    async def ensure_connected(self, file_path: str) -> None:
        ws = find_workspace_root(file_path)
        if self._proc and self._workspace_root == ws and self._initialized:
            return
        if self._proc:
            await self.disconnect()
        self._workspace_root = ws
        await self._connect()

    async def _connect(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            "pyright-langserver", "--stdio",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._workspace_root,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        await self._initialize()
        self._initialized = True

    async def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        buf = b""
        while True:
            chunk = await self._proc.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            while True:
                header_end = buf.find(b"\r\n\r\n")
                if header_end == -1:
                    break
                header = buf[:header_end].decode()
                cl = None
                for line in header.split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        cl = int(line.split(":")[1].strip())
                if cl is None:
                    buf = buf[header_end + 4:]
                    continue
                msg_start = header_end + 4
                msg_end = msg_start + cl
                if len(buf) < msg_end:
                    break
                body = buf[msg_start:msg_end].decode()
                buf = buf[msg_end:]
                try:
                    msg = json.loads(body)
                    self._handle_message(msg)
                except json.JSONDecodeError:
                    pass

    def _handle_message(self, msg: dict) -> None:
        if "id" in msg and msg["id"] is not None:
            fut = self._pending.pop(msg["id"], None)
            if fut and not fut.done():
                if "error" in msg:
                    fut.set_exception(RuntimeError(msg["error"].get("message", "LSP error")))
                else:
                    fut.set_result(msg.get("result"))
        elif msg.get("method") == "textDocument/publishDiagnostics":
            params = msg.get("params", {})
            self._diagnostics[params.get("uri", "")] = params.get("diagnostics", [])

    async def _request(self, method: str, params: Any, timeout: float = 30.0) -> Any:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("LSP server not connected")
        self._req_id += 1
        req_id = self._req_id
        msg = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        content = f"Content-Length: {len(msg.encode())}\r\n\r\n{msg}"
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[req_id] = fut
        self._proc.stdin.write(content.encode())
        await self._proc.stdin.drain()
        return await asyncio.wait_for(fut, timeout=timeout)

    async def _notify(self, method: str, params: Any) -> None:
        if not self._proc or not self._proc.stdin:
            return
        msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
        content = f"Content-Length: {len(msg.encode())}\r\n\r\n{msg}"
        self._proc.stdin.write(content.encode())
        await self._proc.stdin.drain()

    async def _initialize(self) -> None:
        root_uri = file_uri(self._workspace_root)
        await self._request("initialize", {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "rootPath": self._workspace_root,
            "capabilities": {
                "textDocument": {
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "definition": {"linkSupport": True},
                    "references": {},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "codeAction": {"codeActionLiteralSupport": {"codeActionKind": {"valueSet": []}}},
                    "rename": {"prepareSupport": True},
                    "publishDiagnostics": {
                        "relatedInformation": True,
                        "tagSupport": {"valueSet": [1, 2]},
                    },
                },
                "workspace": {"symbol": {}, "workspaceFolders": True},
            },
            "initializationOptions": {},
        }, timeout=60.0)
        await self._notify("initialized", {})

    async def _open_doc(self, file_path: str) -> str:
        p = str(Path(file_path).resolve())
        uri = file_uri(p)
        if uri in self._open_docs:
            return uri
        if not Path(p).exists():
            raise FileNotFoundError(f"File not found: {p}")
        content = Path(p).read_text(errors="replace")
        ext = Path(p).suffix.lower()
        lang_id = LANG_IDS.get(ext, ext.lstrip("."))
        await self._notify("textDocument/didOpen", {
            "textDocument": {"uri": uri, "languageId": lang_id, "version": 1, "text": content},
        })
        self._open_docs.add(uri)
        await asyncio.sleep(0.2)
        return uri

    async def hover(self, file_path: str, line: int, character: int) -> dict | None:
        await self.ensure_connected(file_path)
        uri = await self._open_doc(file_path)
        return await self._request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

    async def definition(self, file_path: str, line: int, character: int) -> Any:
        await self.ensure_connected(file_path)
        uri = await self._open_doc(file_path)
        return await self._request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

    async def references(self, file_path: str, line: int, character: int, include_declaration: bool = True) -> Any:
        await self.ensure_connected(file_path)
        uri = await self._open_doc(file_path)
        return await self._request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": include_declaration},
        })

    async def document_symbols(self, file_path: str) -> Any:
        await self.ensure_connected(file_path)
        uri = await self._open_doc(file_path)
        return await self._request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri},
        })

    async def workspace_symbols(self, file_path: str, query: str) -> Any:
        await self.ensure_connected(file_path)
        return await self._request("workspace/symbol", {"query": query})

    async def diagnostics(self, file_path: str) -> list:
        await self.ensure_connected(file_path)
        uri = await self._open_doc(file_path)
        await asyncio.sleep(1.0)
        return self._diagnostics.get(uri, [])

    async def prepare_rename(self, file_path: str, line: int, character: int) -> Any:
        await self.ensure_connected(file_path)
        uri = await self._open_doc(file_path)
        try:
            return await self._request("textDocument/prepareRename", {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            })
        except RuntimeError:
            return None

    async def rename(self, file_path: str, line: int, character: int, new_name: str) -> Any:
        await self.ensure_connected(file_path)
        uri = await self._open_doc(file_path)
        return await self._request("textDocument/rename", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "newName": new_name,
        })

    async def disconnect(self) -> None:
        if not self._proc:
            return
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        try:
            await asyncio.wait_for(self._request("shutdown", None, timeout=3.0), timeout=3.0)
            await self._notify("exit", None)
        except Exception:
            pass
        if self._proc:
            self._proc.kill()
            await self._proc.wait()
            self._proc = None
        self._initialized = False
        self._open_docs.clear()
        self._diagnostics.clear()
        self._pending.clear()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_hover(hover: dict | None) -> str:
    if not hover:
        return "No hover information available"
    contents = hover.get("contents")
    if isinstance(contents, str):
        text = contents
    elif isinstance(contents, list):
        text = "\n\n".join(c if isinstance(c, str) else c.get("value", "") for c in contents)
    elif isinstance(contents, dict):
        text = contents.get("value", "")
    else:
        text = ""
    r = hover.get("range")
    if r:
        text += f"\n\nRange: {fmt_range(r)}"
    return text or "No hover information available"


def format_locations(locs: Any) -> str:
    if not locs:
        return "No locations found"
    if not isinstance(locs, list):
        locs = [locs]
    if not locs:
        return "No locations found"
    return "\n".join(fmt_location(loc) for loc in locs)


def format_symbols(symbols: list, indent: int = 0) -> str:
    if not symbols:
        return "No symbols found"
    lines = []
    prefix = "  " * indent
    for sym in symbols:
        kind = SYMBOL_KINDS.get(sym.get("kind", 0), "Unknown")
        if "range" in sym:
            r = fmt_range(sym["range"])
            lines.append(f"{prefix}{kind}: {sym['name']} [{r}]")
            children = sym.get("children", [])
            if children:
                lines.append(format_symbols(children, indent + 1))
        else:
            loc = fmt_location(sym.get("location", {}))
            container = f" (in {sym['containerName']})" if sym.get("containerName") else ""
            lines.append(f"{prefix}{kind}: {sym['name']}{container} [{loc}]")
    return "\n".join(lines)


def format_diagnostics(diags: list, file_path: str = "") -> str:
    if not diags:
        return "No diagnostics"
    lines = []
    for d in diags:
        sev = SEVERITY_NAMES.get(d.get("severity", 1), "Unknown")
        r = fmt_range(d["range"])
        source = f"[{d['source']}]" if d.get("source") else ""
        code = f" ({d['code']})" if d.get("code") else ""
        loc = f"{file_path}:{r}" if file_path else r
        lines.append(f"{sev}{code}{source}: {d['message']}\n  at {loc}")
    return "\n\n".join(lines)


def format_workspace_edit(edit: dict | None) -> str:
    if not edit:
        return "No edits"
    lines = []
    for uri, changes in (edit.get("changes") or {}).items():
        path = uri_to_path(uri)
        lines.append(f"File: {path}")
        for ch in changes:
            r = fmt_range(ch["range"])
            preview = ch["newText"][:50] + "..." if len(ch["newText"]) > 50 else ch["newText"]
            lines.append(f'  {r}: "{preview}"')
    for dc in edit.get("documentChanges") or []:
        path = uri_to_path(dc["textDocument"]["uri"])
        lines.append(f"File: {path}")
        for ch in dc.get("edits", []):
            r = fmt_range(ch["range"])
            preview = ch["newText"][:50] + "..." if len(ch["newText"]) > 50 else ch["newText"]
            lines.append(f'  {r}: "{preview}"')
    return "\n".join(lines) if lines else "No edits"


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("pyright-lsp", instructions="Pyright LSP tools for Python code navigation and analysis")
client = LspClient()


@mcp.tool()
async def lsp_hover(file: str, line: int, character: int) -> str:
    """Get type information and documentation for a symbol at a position.

    Args:
        file: Absolute path to the Python file
        line: Line number (1-indexed)
        character: Character position in the line (0-indexed)
    """
    result = await client.hover(file, line - 1, character)
    return format_hover(result)


@mcp.tool()
async def lsp_goto_definition(file: str, line: int, character: int) -> str:
    """Find the definition location of a symbol.

    Args:
        file: Absolute path to the Python file
        line: Line number (1-indexed)
        character: Character position in the line (0-indexed)
    """
    result = await client.definition(file, line - 1, character)
    return format_locations(result)


@mcp.tool()
async def lsp_find_references(file: str, line: int, character: int, include_declaration: bool = True) -> str:
    """Find all references to a symbol across the codebase.

    Args:
        file: Absolute path to the Python file
        line: Line number (1-indexed)
        character: Character position in the line (0-indexed)
        include_declaration: Include the declaration itself in results
    """
    result = await client.references(file, line - 1, character, include_declaration)
    return format_locations(result)


@mcp.tool()
async def lsp_document_symbols(file: str) -> str:
    """Get a hierarchical outline of all symbols in a file (functions, classes, variables).

    Args:
        file: Absolute path to the Python file
    """
    result = await client.document_symbols(file)
    return format_symbols(result or [])


@mcp.tool()
async def lsp_workspace_symbols(file: str, query: str) -> str:
    """Search for symbols across the entire workspace by name.

    Args:
        file: Any Python file in the workspace (used to determine workspace root)
        query: Symbol name or pattern to search for
    """
    result = await client.workspace_symbols(file, query)
    return format_symbols(result or [])


@mcp.tool()
async def lsp_diagnostics(file: str) -> str:
    """Get errors, warnings, and hints for a Python file.

    Args:
        file: Absolute path to the Python file
    """
    result = await client.diagnostics(file)
    return format_diagnostics(result, file)


@mcp.tool()
async def lsp_prepare_rename(file: str, line: int, character: int) -> str:
    """Check if a symbol can be renamed. Returns the symbol range if rename is possible.

    Args:
        file: Absolute path to the Python file
        line: Line number (1-indexed)
        character: Character position in the line (0-indexed)
    """
    result = await client.prepare_rename(file, line - 1, character)
    if not result:
        return "Symbol cannot be renamed at this position"
    if "range" in result:
        return f"Rename possible: {fmt_range(result['range'])}"
    return f"Rename possible: {json.dumps(result)}"


@mcp.tool()
async def lsp_rename(file: str, line: int, character: int, new_name: str) -> str:
    """Rename a symbol across all files in the project. Returns the list of edits (does NOT apply them).

    Args:
        file: Absolute path to the Python file
        line: Line number (1-indexed)
        character: Character position in the line (0-indexed)
        new_name: New name for the symbol
    """
    result = await client.rename(file, line - 1, character, new_name)
    return format_workspace_edit(result)


@mcp.tool()
async def lsp_servers() -> str:
    """List available LSP servers and their installation status."""
    from shutil import which
    servers = [
        ("pyright-langserver", "Pyright (Python)", "pip install pyright"),
    ]
    lines = []
    for cmd, name, hint in servers:
        installed = "installed" if which(cmd) else "not installed"
        lines.append(f"{name}: {installed} ({cmd})\n  Install: {hint}")
    return "\n\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
