import pytest

from semabi.llm import ask


def test_cache_only_mode_refuses_external_invocation_on_miss(tmp_path, monkeypatch):
    monkeypatch.setenv("SEMABI_LLM_CACHE_ONLY", "1")

    with pytest.raises(RuntimeError, match="cache miss"):
        ask("a prompt not present in this isolated cache", model="opus", cache_dir=tmp_path)
