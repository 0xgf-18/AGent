# `scripts/packers/` — per-packer fast paths

A packer article in `knowledge_base/wiki/packers/` is **knowledge**: prose an
agent has to re-derive commands from, every time. That derivation is the slow
part, and it is why "we already know how to unpack this" did not translate into
"this took five minutes".

A script here is the **speed**: one command that fingerprints, applies the
documented method, verifies, and emits.

```
python scripts/packers/chiko_neoark.py <apk> [--offline|--device] [--rebuild]
```

Keep both. The article stays the knowledge and the record of *why* the method
works; the script is the executable form. Neither is optional, and they must not
drift — if you change the method, change the article in the same commit.

## Contract

Every script in this directory obeys these four rules. They are enforced by
`_base.py`, not by convention.

### 1. Fingerprint gate — never run a method on an APK you did not identify

`require_fingerprint()` exits **20** unless every `strong` indicator hits. A
packer script implements exactly one packer's method; applying it to a
different packer produces plausible-looking garbage, which is worse than
declining to run.

Indicators are split:

- **strong** — all must hit. The packer's own decryptor `.so`, its unique
  strings, its structural tell.
- **weak** — scored, never sufficient. These are the ones that mislead.

That split is not decoration. The original 360-jiagu false positive on
`crackme.apk` came from a **91-byte decoy asset** whose filename said `jiagu`.
A weak indicator that hits must never be able to authorise a run on its own;
`neg_b.apk` in the test matrix is exactly that case (decoy asset + appended
payload, wrong packer) and is refused.

### 2. Verification gate — nothing is a success until `verify_result.py` says so

`Gate` collects category checks and hands them to the KB's own gate. Success
requires `VERIFIED_SUCCESS`: **≥3 distinct categories, zero FAIL.**
`COMMAND_SUCCESS` exits **10** and is explicitly *not learnable* — see
`.kb/core-rules.md`. Do not record it as a success, and do not soften it.

### 3. A recovery is only a recovery if the app's own classes are in it

This is the rule that matters most, and it exists because EXP-0002 got it wrong.

Recovering checksum-valid dex is necessary but **not sufficient**. A packer can
leave the app's real logic in a blob you did not recover, while everything you
*did* recover is AndroidX and Kotlin. That looks like a success and is not one.

So `CONTENT/app-classes-present` counts type descriptors belonging to the app's
own package (`Lcom/mducdz/fakeping/…`) across the recovered dex. Zero matches →
`FAIL`, and the script **refuses to write a deliverable**. It tells you to use
`--device` instead.

A check that prints "PASS — verify this yourself" is a rubber stamp, and a gate
that counts categories will happily count it. Assert something or do not emit it.

### 4. Verbatim, and honest about what was not recovered

Constants carry the observed values from the source experiment. If a value
changes, that is new evidence for a new experiment — not a silent edit here.

And when a method recovers *part* of an APK, say so in the exit code and the
summary. The Chiko offline path is the worked example: it recovers one real
9,303,180-byte framework dex, verifies it perfectly, and **still does not unpack
the app** — so it exits 10, not 0.

## Exit codes

| Code | Meaning | Learnable? |
|---|---|---|
| `0` | `VERIFIED_SUCCESS` — ≥3 categories, zero FAIL, app classes present | yes |
| `10` | `COMMAND_SUCCESS` — ran, insufficient evidence | **no** |
| `20` | `FINGERPRINT_MISMATCH` — not this packer, refused to proceed | no |
| `30` | `ENVIRONMENT` — missing tool, no device, no root, bad input | no |
| `1` | `FAILED` — the method ran and did not work | no |

## Output

The deliverable is written **next to the input APK** as
`<input-stem>-unpacked.apk`, with recovered dex in
`<input-stem>-unpacked-dex/`. The packed input is read-only. Scratch goes to a
temp dir. Full rule in `AGENTS.md`.

## Adding a packer

1. Write or update the article in `knowledge_base/wiki/packers/<packer>.md`
   first. If the knowledge is not written down, do not script it.
2. Copy the structure of `chiko_neoark.py`. Import the machinery from `_base.py`;
   do not re-implement dex validation, the fingerprint gate, or the gate runner.
3. `strong` indicators must be things only this packer has. If you cannot name
   two, you do not have a fingerprint yet.
4. Add a `CONTENT` assertion that the app's own classes were recovered.
5. Add negative tests. A fingerprint gate that has never been shown refusing
   something is an untested gate.
6. Wire the new script into the dispatcher table in `README.md` here.

## Test matrix

Re-run after any change:

```
python scripts/packers/tests/test_chiko_neoark.py --apk <a real chiko apk>
```

The four negative fixtures are **synthesized at run time**, not checked in, so
the repo stays small and no APK can be committed by accident. Without `--apk`
the positive test is skipped and the suite still runs 5/5.

| Input | Expect | Why |
|---|---|---|
| the real Chiko APK, `--offline` | `10` | framework dex only — the app is not in them |
| a clean unpacked APK | `20` | no stub `.so`, no appended payload |
| decoy `jiagu` asset + appended payload + *other* packer's `.so` | `20` | weak indicators must not authorise a run |
| chiko-shaped APK + random payload | `1` | fingerprint passes, comb check refuses to invent a key |
| a file that is not a zip | `20` | clean failure, no traceback |
| a nonexistent path | `30` | clean failure |
| unrooted device, `--device` | `30` | root is checked before anything else |

**Status: 6/6 passing.**

The device path additionally needs a rooted device to exercise; it has not been
re-run since the emulators went offline. Treat `--device` as **unverified**
until it is.

## Current inventory

| Packer | Script | Status |
|---|---|---|
| Chiko / NeoArk (Art-Jiagu) | `chiko_neoark.py` | offline path verified; device path unverified |
| 360 Jiagu | — | article only (see `360-jiagu.md`) |
| ViRex | — | article only |
| XuanDun | — | article only |
