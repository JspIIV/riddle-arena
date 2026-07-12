# Riddle Arena

An AI-powered riddle game built as a GenLayer Intelligent Contract, paired with a live web UI. GenLayer validators generate riddles on-chain and judge player answers through decentralized AI consensus, rather than a centralized backend deciding either.

- **Live app:** https://riddle-arena.vercel.app
- **Deployed contract (GenLayer Studio):** [`0xfBd7304D927b8F201348368569a0C5b2fEAac8F0`](https://studio.genlayer.com/contracts?import-contract=0xfBd7304D927b8F201348368569a0C5b2fEAac8F0)
- **Contract source:** [`contracts/riddle_arena.py`](contracts/riddle_arena.py) (also present at repo root for convenience)
- **Frontend source:** [`src/main.js`](src/main.js)

## How it works

### Riddle generation (`create_riddle`)

A leader validator generates a riddle for a given topic/difficulty via an LLM prompt. Because independently regenerating a riddle produces a *different* riddle on every call, validators can't reach consensus by re-running the same generation and comparing outputs byte-for-byte (the usual `gl.eq_principle.prompt_comparative` pattern). Instead, `create_riddle` uses `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`: the leader proposes a riddle, and every other validator independently judges whether that specific riddle is internally consistent and fair (does it actually clue the claimed answer, without giving it away) — a non-comparative consensus pattern suited to creative generation tasks.

### Answer checking (`submit_answer`)

Answers are checked with `gl.eq_principle.prompt_comparative`: validators independently judge whether the submitted answer is semantically equivalent to the stored answer (allowing synonyms/spelling variation), and must agree on the boolean result. The first player to submit a correct answer solves the riddle and scores points; the riddle is then locked.

### Storage

- `riddles: TreeMap[str, str]` — JSON-encoded riddle records (topic, difficulty, riddle_text, answer, solved, solved_by), keyed by an incrementing `riddle_id`.
- `players: TreeMap[str, str]` — JSON-encoded player records (score, solved_count, attempts), keyed by player name.

## Deployment

Deployed to GenLayer Studio (`studionet`) using the official `genlayer` CLI:

```bash
genlayer network set studionet
genlayer deploy --contract contracts/riddle_arena.py
```

The resulting contract address is `0xfBd7304D927b8F201348368569a0C5b2fEAac8F0`, importable directly in Studio via the link above. `studionet` is gasless, so no funding is required to deploy or interact with it.

## Running the frontend locally

```bash
npm install
npm run dev
```

The frontend (`src/main.js`) uses `genlayer-js` to connect a browser wallet and read/write the deployed contract directly — no custom backend, all state comes from the chain.

## Tests

Direct-mode tests (`tests/direct/test_riddle_arena.py`) use GenLayer's official `genlayer-test` pytest plugin, mocking the LLM leader call and asserting on-chain state transitions: riddle creation, sequential IDs, correct/incorrect answer handling, re-solve prevention, unknown-player/unknown-riddle error paths, and cumulative player scoring across multiple riddles.

```bash
pip install genlayer-test
pytest tests/direct/ -v
```

All 9 tests pass locally.

### Known Windows compatibility issues (worked around in `tests/direct/conftest.py`)

Getting `genlayer-test` running on Windows surfaced three separate upstream bugs, all reported to the GenLayer team, and worked around locally via a conftest shim so the tests actually run and pass rather than just being unverified source:

1. `genlayer-py`/`genlayer-test` fails to import on Python 3.10 (`collections.abc.Buffer` requires 3.12+). Workaround: run tests on Python 3.12+.
2. The current "latest" `genvm` release (`v0.3.0-rc7`) no longer publishes a `genvm-universal.tar.xz` asset needed for direct-mode SDK loading on Windows; older release `v0.2.16` still does. Workaround: `conftest.py` pins `sdk_version="v0.2.16"` for `direct_deploy`. Reported: [genlayer-testing-suite#99](https://github.com/genlayerlabs/genlayer-testing-suite/issues/99)
3. `gltest`'s direct-mode loader calls `os.unlink()` on a temp file while a duplicated file descriptor onto it is still open, which raises `PermissionError` on Windows (legal on POSIX, not on Windows file locking). Workaround: `conftest.py` monkeypatches `os.unlink` to ignore `PermissionError`. Reported in the same issue above.
4. `gltest`'s direct-mode LLM mock handler unconditionally auto-parses any JSON-decodable mocked response into a `dict`, even when the contract treats `exec_prompt`'s return value as a raw string (this project's defensive parsing pattern: strip markdown fences, then `json.loads` manually — the pattern recommended by GenLayer's own `write-contract` skill). Workaround: `conftest.py` restores raw-string mock responses for this test suite.

Also reported separately during development of this project: [genvm#322](https://github.com/genlayerlabs/genvm/issues/322) (`gl.vm.run_nondet_unsafe` output incompatible with `gl.vm.unpack_result`) and [genvm-linter#17](https://github.com/genlayerlabs/genvm-linter/issues/17) (`genvm-lint` crashes on Windows).
