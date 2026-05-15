"""Unit tests for tool_executor."""

import os
import tempfile
import pytest
from runner.tool_executor import execute_tool, _truncate, _resolve_path


@pytest.fixture
def tmp_dirs():
    with tempfile.TemporaryDirectory() as workspace:
        with tempfile.TemporaryDirectory() as skill_path:
            yield workspace, skill_path


def test_write_and_read_file(tmp_dirs):
    workspace, skill_path = tmp_dirs
    path = os.path.join(workspace, "hello.txt")

    result = execute_tool(
        "write_file", {"path": path, "content": "Hello World"}, workspace, skill_path
    )
    assert "written" in result

    result = execute_tool("read_file", {"path": path}, workspace, skill_path)
    assert result == "Hello World"


def test_read_file_in_skill_folder(tmp_dirs):
    workspace, skill_path = tmp_dirs
    skill_file = os.path.join(skill_path, "FORMS.md")
    with open(skill_file, "w") as f:
        f.write("# Forms Guide")

    result = execute_tool("read_file", {"path": skill_file}, workspace, skill_path)
    assert result == "# Forms Guide"


def test_read_file_outside_workspace_denied(tmp_dirs):
    workspace, skill_path = tmp_dirs
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("secret")
        outside_path = f.name

    try:
        result = execute_tool(
            "read_file", {"path": outside_path}, workspace, skill_path
        )
        assert "Access denied" in result or "ERROR" in result
    finally:
        os.unlink(outside_path)


def test_write_file_outside_workspace_denied(tmp_dirs):
    workspace, skill_path = tmp_dirs
    outside_path = os.path.join(skill_path, "malicious.txt")

    result = execute_tool(
        "write_file", {"path": outside_path, "content": "bad"}, workspace, skill_path
    )
    assert "ERROR" in result


def test_bash_execution(tmp_dirs):
    workspace, skill_path = tmp_dirs
    result = execute_tool("bash", {"command": "echo hello"}, workspace, skill_path)
    assert "hello" in result


def test_bash_timeout(tmp_dirs):
    workspace, skill_path = tmp_dirs
    result = execute_tool(
        "bash", {"command": "sleep 10"}, workspace, skill_path, timeout=1
    )
    assert "timed out" in result.lower()


def test_list_directory(tmp_dirs):
    workspace, skill_path = tmp_dirs
    path = os.path.join(workspace, "test.txt")
    with open(path, "w") as f:
        f.write("x")

    result = execute_tool("list_directory", {"path": workspace}, workspace, skill_path)
    assert "test.txt" in result


def test_str_replace(tmp_dirs):
    workspace, skill_path = tmp_dirs
    path = os.path.join(workspace, "code.py")
    with open(path, "w") as f:
        f.write("def hello(): pass")

    result = execute_tool(
        "str_replace",
        {"path": path, "old_str": "hello", "new_str": "world"},
        workspace,
        skill_path,
    )
    assert "Replaced" in result

    content = open(path).read()
    assert "world" in content
    assert "hello" not in content


def test_str_replace_not_unique(tmp_dirs):
    workspace, skill_path = tmp_dirs
    path = os.path.join(workspace, "dup.txt")
    with open(path, "w") as f:
        f.write("foo foo foo")

    result = execute_tool(
        "str_replace",
        {"path": path, "old_str": "foo", "new_str": "bar"},
        workspace,
        skill_path,
    )
    assert "3 times" in result


def test_end_turn(tmp_dirs):
    workspace, skill_path = tmp_dirs
    result = execute_tool("end_turn", {"summary": "Done!"}, workspace, skill_path)
    assert "Done!" in result


def test_unknown_tool(tmp_dirs):
    workspace, skill_path = tmp_dirs
    result = execute_tool("nonexistent", {}, workspace, skill_path)
    assert "Unknown tool" in result


def test_truncate():
    long_text = "a" * 5000
    result = _truncate(long_text, max_chars=4000)
    assert len(result) > 4000  # includes truncation marker
    assert "TRUNCATED" in result


def test_resolve_path_absolute(tmp_dirs):
    workspace, _ = tmp_dirs
    abs_path = "/tmp/foo.txt"
    assert _resolve_path(abs_path, workspace) == abs_path


def test_resolve_path_relative(tmp_dirs):
    workspace, _ = tmp_dirs
    result = _resolve_path("foo.txt", workspace)
    assert result == os.path.join(workspace, "foo.txt")
