# Experiment Protocol — Adaptive APK RE Research Loop

> **Load when:** the user asks to `analyze <apk>`, `run experiment`, `unpack`,
> `learn from success/failure`, or any task that runs the research loop
> (fingerprint -> analyze -> knowledge search -> experiment -> verify -> learn).
> **Always load first:** `.kb/core-rules.md`, then this file, then the schema
> of the artifact you are about to write (`.kb/schemas/<type>.md`).
> **Status:** Phases 1-4 IMPLEMENTED (scripts enforce the rules); Phases 5-6 planned.

---

## 0. Iron Rules

1. **No fake success.** A technique enters the KB only after the verification
   gate returns `VERIFIED_SUCCESS`. `COMMAND_SUCCESS` (exit code 0 / file
   produced) is NOT evidence.
2. **Failures are classified, never guessed:**

   | Class | Meaning | Example |
   |---|---|---|
   | `ENVIRONMENT_ISSUE` | probe/health check failed BEFORE the experiment | adb disconnected, no root, disk full |
   | `TOOL_FAILURE` | tool crashed/misbehaved on valid input | apktool OOM, jadx exception |
   | `TECHNIQUE_INAPPLICABLE` | technique's prerequisites are not met for this APK | needs root, APK is not packed that way |
   | `APK_FAILURE` | APK defeats the technique | anti-tamper kills patched build |

   An `ENVIRONMENT_ISSUE` must be fixed and the experiment re-run; it is
   **never** recorded as an APK failure and never learned from.

3. **Immutable history.** Experiments, success traces, and superseded technique
   versions are never rewritten or deleted. Corrections are new versions
   (`technique_version`, `supersedes`, `superseded_by`).
4. **Provenance on every claim:** `[V]` verified by command/artifact, `[I]`
   inference, `[U]` unverified, `[AI Synthesis]` model reasoning. Causality
   factors from experiments are `[V]`; speculative ones stay `INFERENCE` until
   an experiment supports them.
5. **Environment before APK.** If `.kb` health gate is not `READY`, stop and
   fix the environment first (rule: never blame the APK for a broken setup).
6. **No volatile state in the KB.** Device/host state (serials, models,
   endpoints, absolute host paths, on-device tool presence) is probed at
   runtime (`env_probe.py --health`, `tool_discover.py`) and recorded in
   artifacts as `environment_id: host-runtime` — never as wiki articles.
   What the KB stores instead: **packer -> unpacking-method knowledge**
   (the only part that can be reused on the next APK).

---

## 1. Phase 1 — Environment & Tool Initialization (IMPLEMENTED)

Run before touching any APK, and again whenever a device/tool changes.

```bash
# 1. Probe environment + health verdict (READY | DEGRADED | UNAVAILABLE)
#    Runtime-only: device state is NEVER written into the KB (Iron Rule 6)
python .kb/scripts/env_probe.py --health

# 2. Discover/refresh tool registry (host + device tools)
python .kb/scripts/tool_discover.py --serial <adb-serial> --write

# 3. Rebuild indexes + graph after any wiki write
python .kb/scripts/index_builder.py
python .kb/scripts/graph_generator.py
```

- Missing tools -> install per the registry article (`install_command`), then
  re-probe. `DEGRADED` (e.g. root missing) = proceed only with techniques whose
  prerequisites do not require root — the planner checks this in Phase 2.
- New tool IDs are allocated by `python .kb/scripts/kb_ids.py --next TR`
  (scripts do this internally; IDs are never reused).

## 2. Phase 2 — APK Fingerprint & Strategy Planning (IMPLEMENTED)

```bash
# 1. Fingerprint + draft apk-analysis article (allocates A-XXXXXX, reuses id on same sha256)
python .kb/scripts/apk_fingerprint.py <apk> --write

# 2. Retrieve knowledge BEFORE experimenting (prereqs gated vs environment)
python .kb/scripts/kb_search.py --analysis A-XXXXXX --text "<goal>" --markdown
```

1. Fingerprint: sha256, package, versionCode, SDKs, ABIs, signature schemes/cert,
   DEX/native inventory, protection indicators (entry-name heuristics + native
   byte markers) -> `.kb/schemas/apk-analysis.md`. Detections are `[AI Synthesis]`
   heuristics until an experiment confirms them `[V]`.
2. Search knowledge BEFORE experimenting — **packer articles first**
   (`kind: packer`: packer name -> verified unpacking method), then
   techniques, patterns, success traces, prior analyses matched by indicators.
   An `unpacking_status: unpacked` packer match means: follow its method
   directly and record every step as an experiment.
3. For each candidate evaluate prerequisites (`MET | NOT_MET(+missing) | UNKNOWN`):
   stored environment profile if present, else the runtime fallback (tools
   gated against the tool registry; device-bound requirements -> run
   `env_probe.py --health`). `PREREQUISITES_NOT_MET` -> skip with reason;
   never brute-force.
4. Produce an ordered plan (technique chain) -> each attempt becomes `EXP-XXXX`.

## 3. Phase 3 — Experiments & Verification Gate (IMPLEMENTED)

```bash
# per-check verification (each prints one JSON result line)
python .kb/scripts/verify_result.py structural --file <apk> --kind zip
python .kb/scripts/verify_result.py parser --dex <dex>            # real DEX header/adler32/sha1
python .kb/scripts/verify_result.py content --file <apk> --class com.foo.Bar
python .kb/scripts/verify_result.py downstream --tool apktool|jadx|apksigner|zipalign --file <x>
python .kb/scripts/verify_result.py reproducibility --file <x> --expected-sha <hex>
python .kb/scripts/verify_result.py gate r1.json r2.json ...       # 0=VERIFIED, 10=COMMAND, 1=FAILED

# record the experiment (allocates EXP-XXXX, validates schema rules)
python .kb/scripts/record_experiment.py --payload exp.json
```

Every attempt = one `Experiment` (`.kb/schemas/experiment.md`):

- Record: exact commands (verbatim), inputs (APK/tool versions),
  `environment_id: host-runtime` (device state probed live, never stored),
  hypothesis, result (`SUCCESS | PARTIAL | FAILURE`), verification verdict.
- **Gate (3+ distinct categories required, zero FAIL):**

  | Category | Example check |
  |---|---|
  | `STRUCTURAL` | output exists, zip parses, entry counts sane |
  | `PARSER` | DEX magic/size/adler32/sha1, XML parses, ELF header |
  | `CONTENT` | expected classes/strings/signatures present |
  | `DOWNSTREAM` | apktool/jadx/apksigner/zipalign accept the output |
  | `REPRODUCIBILITY` | repeat run produces identical hash |

- All required categories pass -> `VERIFIED_SUCCESS` (learnable).
  Any category fail (or <3 categories) -> `COMMAND_SUCCESS` at best (not learnable).
- `record_experiment.py` ENFORCES the rules: refuses VERIFIED_SUCCESS with <3
  categories, refuses SUCCESS/PARTIAL with `UNVERIFIED`, refuses FAILURE
  without a `failure_category`.

## 4. Phase 4 — Success Traces & Technique Extraction (IMPLEMENTED)

- `VERIFIED_SUCCESS` -> `SuccessTrace` (ST-XXXX): sequence of experiments,
  `ESSENTIAL` vs `LIKELY_RELEVANT` vs `OPTIONAL` vs `IRRELEVANT` factors,
  causality table (each factor `[V]` or `INFERENCE`).
  **Script:** `.kb/scripts/record_success_trace.py --payload st.json`
  (refuses traces not backed by a VERIFIED_SUCCESS experiment; requires >=3
  PASS gate rows, mandatory before/after + reproducibility; `causality_analysis`
  only `SUPPORTED` when every ESSENTIAL factor is `[V]` with evidence,
  otherwise `INFERENCE`).
- Extract at most ONE `Technique` per extraction pass from a trace
  (`.kb/schemas/technique.md`), with `confidence 0.0-1.0`,
  `promotion_state: OBSERVED -> CANDIDATE -> VALIDATED -> TRUSTED`.
  **Script:** `.kb/scripts/record_technique.py --payload t.json`
  (enforces promotion evidence: CANDIDATE >=1 VERIFIED experiment,
  VALIDATED >=2 independent verified analyses, TRUSTED >=3; every workflow
  step needs Observation/Action/Tool/Expected/Success Indicator; versioning
  immutable — updates must bump `version`, carry `version_reason` +
  `previous_version`, old Version History rows appended, never rewritten).
- **Packer storage (primary reuse artifact):** when an unpack beats a packer
  that has no article yet (or adds a new variant), store it:
  `.kb/scripts/record_packer.py --payload packer.json` (`.kb/schemas/packer.md`).
  New packer -> slug-named article `wiki/packers/<packer_id>.md` with its full
  unpacking method; `unpacking_status: unpacked` requires >=1 VERIFIED_SUCCESS
  experiment in evidence OR a documented source; updates bump `version`
  immutably. Retrieval: `kb_search` returns `kind: packer` results.
- Failures -> `failure_db` notes on the experiment (never promoted, never
  silently deleted).

Implemented artifacts: `wiki/success-traces/ST-0001.md` (first trace, causality
INFERENCE), `wiki/techniques/T-0020.md` (first structured technique, CANDIDATE
0.7). Tests: `.kb/scripts/tests/test_phase4.py`.

## 5. Phase 5 — Knowledge Graph, Reuse & Confidence (PLANNED)

- Link everything with `[[wiki/...]]`; regenerate
  `index_builder.py` + `graph_generator.py` after each write.
- Retrieval planner for future APKs: similarity + prerequisite gate; unmet
  prerequisites return `PREREQUISITES_NOT_MET`, not a silent drop.
- Confidence promotion rules: +evidence per independent VERIFIED_SUCCESS on a
  new APK; decay/flag on contradicted result (`[X]` marker + version bump).
- Self-improvement applies ONLY to knowledge files (wiki, indexes, protocol
  amendments); core scripts change only via explicit user request.

## 6. Phase 6 — Acceptance (PLANNED)

End-to-end demo on an authorized APK: BEFORE (technique absent, retrieval
miss) -> run loop -> AFTER (SuccessTrace + Technique stored) -> re-run
retrieval on a second APK (or second entry) -> technique returned with
prerequisites satisfied. Report: files created/modified, tests run, build
command, result, open issues.

---

## Appendix A — Commands Quick Reference

```bash
python .kb/scripts/kb_ids.py --list                 # next free IDs
python .kb/scripts/env_probe.py --health            # environment gate (runtime-only)
python .kb/scripts/kb_search.py --text "<goal>"     # includes kind: packer results
python .kb/scripts/record_packer.py --payload p.json  # store packer -> unpacking method
python .kb/scripts/tool_discover.py --markdown      # tool availability table
python .kb/scripts/index_builder.py                 # rebuild generated indexes
python .kb/scripts/graph_generator.py               # regenerate graph_data.js
```

## Appendix B — When NOT to Use This Protocol

- Pure Q&A about the KB -> `.kb/read-protocol.md`
- Compiling a raw feed -> `.kb/write-pipeline.md`
- Maintenance/gap reports -> `.kb/maintenance.md`
