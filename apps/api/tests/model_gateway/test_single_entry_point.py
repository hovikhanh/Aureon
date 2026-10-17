"""TC-IDP-036 (a): every LLM call goes through ModelGateway (07 §5.2, CLAUDE.md "IDP Worker").

Static AST scan of apps/api/src/app: no module outside `app/core/model_gateway/` may import an
LLM provider SDK or reference OmniRoute's chat-completions endpoint.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import app

APP_ROOT = Path(app.__file__).resolve().parent
GATEWAY_PKG = APP_ROOT / "core" / "model_gateway"

LLM_SDK_MODULES = (
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "google.ai.generativelanguage",
    "vertexai",
    "litellm",
    "mistralai",
    "cohere",
    "groq",
    "together",
    "ollama",
    "replicate",
    "huggingface_hub",
    "langchain",
    "langchain_core",
    "langchain_openai",
    "langchain_anthropic",
    "llama_index.llms",
    "dashscope",
    "zhipuai",
    "deepseek",
)
ENDPOINT_MARKERS = ("chat/completions", "/v1/completions", "/v1/messages")


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    what: str


def _is_llm_module(name: str) -> bool:
    return any(name == m or name.startswith(m + ".") for m in LLM_SDK_MODULES)


def scan_file(path: Path, rel: str) -> list[Violation]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[Violation] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name | ast.Attribute)
            and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
            in ("import_module", "__import__")
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names = [node.args[0].value]
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(marker in node.value for marker in ENDPOINT_MARKERS):
                found.append(Violation(rel, node.lineno, f"endpoint {node.value!r}"))
        for name in names:
            if _is_llm_module(name):
                found.append(Violation(rel, node.lineno, f"import {name}"))
                break
    return found


def scan_tree(root: Path, allowed: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        if path.is_relative_to(allowed):
            continue
        violations += scan_file(path, path.relative_to(root).as_posix())
    return violations


def test_no_module_outside_gateway_calls_llm() -> None:
    # Zero exceptions: the gateway package is the only allowed caller (no allowlist).
    violations = scan_tree(APP_ROOT, GATEWAY_PKG)
    assert violations == [], f"LLM access outside ModelGateway: {violations}"


def test_gateway_package_itself_uses_no_provider_sdk() -> None:
    # The gateway talks to OmniRoute over plain httpx (no new dependency, CLAUDE.md).
    imports = [
        v
        for p in sorted(GATEWAY_PKG.rglob("*.py"))
        for v in scan_file(p, p.name)
        if v.what.startswith("import")
    ]
    assert imports == []


def test_scanner_catches_violations(tmp_path: Path) -> None:
    root = tmp_path / "app"
    (root / "core" / "model_gateway").mkdir(parents=True)
    (root / "core" / "model_gateway" / "gateway.py").write_text("import openai\n")
    (root / "modules").mkdir()
    (root / "modules" / "clean.py").write_text("import httpx\nfrom app.core import config\n")
    (root / "modules" / "bad_import.py").write_text("import openai\n")
    (root / "modules" / "bad_from.py").write_text("from anthropic import Anthropic\n")
    (root / "modules" / "bad_sub.py").write_text("from google import genai\n")
    (root / "modules" / "bad_dyn.py").write_text(
        "import importlib\nm = importlib.import_module('litellm')\n"
    )
    (root / "modules" / "bad_http.py").write_text(
        "import httpx\nhttpx.post(f'{base}/chat/completions', json={})\n"
    )

    found = {
        (v.path, v.what.split(" ")[0]) for v in scan_tree(root, root / "core" / "model_gateway")
    }

    assert found == {
        ("modules/bad_import.py", "import"),
        ("modules/bad_from.py", "import"),
        ("modules/bad_sub.py", "import"),
        ("modules/bad_dyn.py", "import"),
        ("modules/bad_http.py", "endpoint"),
    }
