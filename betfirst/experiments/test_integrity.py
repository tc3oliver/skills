"""Conservative, additive-only integrity policy for agent-authored Python tests.

Existing top-level statements and test methods must remain semantically intact
(AST equality, ignoring comments/whitespace); new test methods/classes/files
are permitted. Non-Python test assets are immutable. This is a grading policy,
NOT a security boundary: independent oracles still decide correctness.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _same(left: ast.AST, right: ast.AST) -> bool:
    return ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)


def _added_statement(node: ast.stmt, *, in_class: bool) -> bool:
    if in_class:
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return True
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name.startswith("test_")
    if isinstance(node, ast.ClassDef):
        # New top-level test case must derive from unittest.TestCase or TestCase.
        return any(
            (isinstance(base, ast.Name) and base.id == "TestCase") or
            (isinstance(base, ast.Attribute) and base.attr == "TestCase")
            for base in node.bases
        )
    return False


def _same_preserved(old: ast.stmt, new: ast.stmt) -> bool:
    if not (isinstance(old, ast.ClassDef) and isinstance(new, ast.ClassDef)):
        return _same(old, new)
    if old.name != new.name:
        return False
    for attr in ("bases", "keywords", "decorator_list", "type_params"):
        if hasattr(old, attr) and not _value_same(getattr(old, attr), getattr(new, attr, None)):
            return False
    return _body_preserved(old.body, new.body, in_class=True)


def _value_same(left: object, right: object) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_value_same(a, b) for a, b in zip(left, right))
    if isinstance(left, ast.AST) and isinstance(right, ast.AST):
        return _same(left, right)
    return left == right


def _body_preserved(old: list[ast.stmt], new: list[ast.stmt], *, in_class: bool) -> bool:
    j = 0
    for expected in old:
        while j < len(new) and not _same_preserved(expected, new[j]):
            if not _added_statement(new[j], in_class=in_class):
                return False
            j += 1
        if j == len(new):
            return False
        j += 1
    return all(_added_statement(extra, in_class=in_class) for extra in new[j:])


def _files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    paths = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"test symlink is not allowed: {path}")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            paths[str(path.relative_to(root))] = path
    return paths


def inspect_tests(original: Path, workspace: Path) -> dict:
    """Check copied workspace/tests against fixture/tests; deterministic and read-only.

    A test-only original fixture missing from the workspace counts as tampering.
    Existing test code may gain standalone test_ methods, unittest.TestCase
    classes and imports, without modifying any existing AST statements.
    """
    before = _files(original / "tests")
    after = _files(workspace / "tests")
    added, extended, tampered, deleted = [], [], [], []
    for rel, source in sorted(before.items()):
        target = after.get(rel)
        if target is None:
            deleted.append(rel)
            continue
        if source.read_bytes() == target.read_bytes():
            continue
        if source.suffix != ".py":
            tampered.append(rel)
            continue
        try:
            src_tree = ast.parse(source.read_text(encoding="utf-8"))
            dst_tree = ast.parse(target.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError, ValueError):
            tampered.append(rel)
            continue
        if _body_preserved(src_tree.body, dst_tree.body, in_class=False):
            extended.append(rel)
        else:
            tampered.append(rel)
    for rel, path in sorted(after.items()):
        if rel in before:
            continue
        # Only new test_*.py source modules are accepted. No conftest.py,
        # .pth, test helper executables, or arbitrary data files.
        if path.suffix != ".py" or not Path(rel).name.startswith("test_"):
            tampered.append(rel)
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError, ValueError):
            tampered.append(rel)
        else:
            added.append(rel)
    return {
        "passed": not (tampered or deleted),
        "added_test_files": added,
        "extended_test_files": extended,
        "tampered_test_files": tampered,
        "deleted_test_files": deleted,
    }
