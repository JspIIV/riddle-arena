import os
import pytest

# Windows compatibility shim: gltest's direct-mode loader calls os.unlink() on a
# temp file while a duplicated file descriptor pointing at it is still open
# (dup'd onto stdin for a subprocess to read). This is legal on POSIX but raises
# PermissionError on Windows, which enforces file locking on open handles.
# Reported upstream: https://github.com/genlayerlabs/genlayer-testing-suite/issues/99
_original_unlink = os.unlink


def _safe_unlink(path, *args, **kwargs):
    try:
        _original_unlink(path, *args, **kwargs)
    except PermissionError:
        pass


os.unlink = _safe_unlink

# Compatibility shim: gltest's direct-mode LLM mock handler unconditionally
# auto-parses any JSON-decodable mocked response into a dict, regardless of
# whether the contract called exec_prompt(response_format="json") or the
# plain default. riddle_arena.py (like most contracts in this project) treats
# exec_prompt's return value as a raw string and does its own markdown-fence
# stripping + json.loads, per GenLayer's documented defensive-parsing pattern.
# This shim restores that raw-string behavior for direct-mode tests.
# Reported upstream: https://github.com/genlayerlabs/genlayer-testing-suite/issues/99
import gltest.direct.wasi_mock as _wasi_mock


def _handle_llm_request_raw_string(vm, data):
    prompt = data.get("prompt", "")
    response = vm._match_llm_mock(prompt)
    if response is not None:
        return {"ok": response}

    strict = getattr(vm, "_strict_mock_mode", False)
    if strict:
        registered = [p.pattern for p, _ in vm._llm_mocks]
        raise _wasi_mock.MockNotFoundError(
            f"[strict] No LLM mock for prompt: {prompt[:100]}...\n"
            f"  Registered: {registered or '(none)'}"
        )

    live_handler = getattr(vm, "_live_llm_handler", None)
    if live_handler is not None:
        return live_handler(data)

    registered = [p.pattern for p, _ in vm._llm_mocks]
    raise _wasi_mock.MockNotFoundError(
        f"No LLM mock for prompt: {prompt[:100]}...\n"
        f"  Registered: {registered or '(none)'}"
    )


_wasi_mock._handle_llm_request = _handle_llm_request_raw_string


@pytest.fixture
def direct_deploy(direct_vm):
    def _deploy(contract_path, *args, sdk_version="v0.2.16", **kwargs):
        # Windows compatibility shim: the current "latest" genvm release
        # (v0.3.0-rc7) no longer publishes a genvm-universal.tar.xz asset,
        # which direct-mode SDK loading needs on Windows. v0.2.16 is the most
        # recent release that still publishes it.
        # Reported upstream: https://github.com/genlayerlabs/genlayer-testing-suite/issues/99
        from gltest.direct.loader import deploy_contract
        return deploy_contract(contract_path, direct_vm, *args, sdk_version=sdk_version, **kwargs)
    return _deploy
