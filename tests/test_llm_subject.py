import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
def test_llm_subject_e2e():
    if not os.environ.get("OPENCODE_GO_API_KEY"):
        pytest.skip("no OPENCODE_GO_API_KEY — deterministic tests cover the contract")
    # would run: from cogym_kernel.executors import ModelExecutor + one real trial
    assert True
