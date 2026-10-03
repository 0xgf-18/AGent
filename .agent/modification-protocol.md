# APK Modification Protocol — Reverse-Engineering, Unpacking & Modification Agent

> **Load when:** the user asks to modify, patch, or change an APK's behavior.
> **Always load first:** `.agent/core-rules.md`, then this file, then the schema
> of the artifact you are about to write (`.agent/schemas/<type>.md`).
> **Status:** Phases 1-4 IMPLEMENTED (scripts enforce the rules); Phases 5-6 planned.

---

## 0. Iron Rules

1. **No fake success.** A modification is only successful after runtime validation
   confirms the changed behavior. A rebuilt APK that installs is NOT evidence.
2. **Evidence-driven.** Never invent recovered code, addresses, classes, functions,
   or runtime results. Distinguish: Confirmed / Strongly inferred / Possible / Unknown.
3. **Smallest reliable patch.** Prefer the minimal modification that achieves the
   requested behavior. Do not make unrelated changes.
4. **Preserve functionality.** Keep as much of the original application working as
   possible. Patch the verification path, not unrelated code.
5. **Immutable history.** Modifications, experiments, and superseded versions are
   never rewritten or deleted. Corrections are new versions.
6. **Provenance on every claim:** `[V]` verified by command/artifact, `[I]` inference,
   `[U]` unverified, `[AI Synthesis]` model reasoning.

---

## 1. Phase 1 — APK Inspection & Structural Analysis (IMPLEMENTED)

Run before any modification:

```bash
# 1. Fingerprint + draft apk-analysis article
python .agent/scripts/apk_fingerprint.py <apk> --write

# 2. Retrieve knowledge BEFORE modifying
python .agent/scripts/kb_search.py --analysis A-XXXXXX --text "<goal>" --markdown
```

### Establish

| # | Property | Tool |
|---|---|---|
| 1 | Package name | `aapt2 dump badging` |
| 2 | Version / versionCode | `aapt2 dump badging` |
| 3 | APK signing info | `apksigner verify --print-certs` |
| 4 | Manifest structure | `aapt2 dump xmltree` |
| 5 | DEX files | `apk_fingerprint.py` inventory |
| 6 | Native libraries | `apk_fingerprint.py` inventory |
| 7 | Assets / resources | `apk_fingerprint.py` inventory |
| 8 | Dynamic loading mechanisms | `dexdump -d` + string scan |
| 9 | Encryption / encoding | byte-marker scan + entropy |
| 10 | Packers / protectors | `apk_fingerprint.py` detections |
| 11 | Integrity / anti-tamper | `dexdump` + native RE |
| 12 | Auth / licensing components | `dexdump` + string scan |
| 13 | Entry points / init paths | `aapt2 dump xmltree` + `dexdump` |

### Classification

Determine whether the APK is:
- Normally structured
- Obfuscated
- Packed
- Dynamically unpacked
- Multi-DEX
- Native-assisted
- VM / virtualization protected
- Dynamically loading code
- Using encrypted assets or embedded payloads

---

## 2. Phase 2 — Unpacking Mode (IMPLEMENTED)

When protected or packed code is encountered:

### Strategy

1. **Identify** the protection architecture
2. **Locate** bootstrap / application initialization logic
3. **Trace** class loading
4. **Trace** DEX creation / loading
5. **Identify** decrypted or reconstructed payloads
6. **Locate** runtime-generated DEX/OAT/JIT/code regions
7. **Recover** meaningful application artifacts
8. **Preserve** the relationship between recovered artifacts and their runtime origin
9. **Repeat** recursively when multiple layers exist

### For Each Stage, Record

| Field | Description |
|---|---|
| Input | What went in |
| Transformation | What was done |
| Output | What came out |
| Address / location | Where it was found |
| Loading mechanism | How it was loaded |
| Verification method | How it was confirmed |
| Confidence level | Confirmed / Inferred / Possible / Unknown |

### Fast Path

Check for a known packer first:

```
python tools/unpackers/<packer>.py <apk> [--offline|--device] [--rebuild]
```

If a script exists for the identified packer, run it instead of re-deriving the method.

---

## 3. Phase 3 — Modification Request (IMPLEMENTED)

After initial analysis, ask the operator **one focused question**:

> "What modification do you want to make to this APK?"

### Modification Categories

| Category | Description |
|---|---|
| Change application behavior | Alter how the app behaves |
| Modify UI | Change layout, text, or resources |
| Change resources | Replace images, strings, etc. |
| Remove a feature | Disable a specific feature |
| Modify method logic | Change what a method does |
| Modify configuration | Change settings or constants |
| Instrument methods | Add logging/tracing to methods |
| Add logging/telemetry | Insert logging calls |
| Modify network behavior | Change endpoints or protocols |
| Modify auth behavior | Patch authentication (test builds only) |
| Modify licensing checks | Patch license validation (test builds only) |
| Modify integrity/anti-tamper | Disable protection mechanisms |
| Patch native code | Modify .so libraries |
| Patch DEX code | Modify smali/bytecode |
| Replace encrypted assets | Decrypt and replace assets |
| Disable protection | Remove packer/protector |
| Other custom | User-defined modification |

Do not ask unnecessary repetitive questions once the objective is clear.

---

## 4. Phase 4 — Patch Planning (IMPLEMENTED)

Before modifying anything, produce a **concise patch plan**:

| Field | Description |
|---|---|
| Target component | What to patch |
| Target class/method/native function | Where to patch |
| Current behavior | What it does now |
| Desired behavior | What it should do |
| Proposed modification | How to change it |
| Files affected | Which files change |
| Rebuild requirements | apktool, etc. |
| Signing requirements | keystore, etc. | 
| Risks | What could break |
| Validation steps | How to verify |

**Prefer the smallest reliable modification.**

---

## 5. Phase 5 — DEX Patching (IMPLEMENTED)

### Supported Transformations

- Smali modification
- Method body replacement
- Conditional-branch changes
- Return-value modification
- Constant replacement
- String replacement
- Method call replacement
- Class insertion
- Class removal
- Resource-reference correction
- Multi-DEX updates

### Preserve

- Register correctness
- Exception handlers
- Method signatures
- Class references
- Resource references
- Verification compatibility

### Consistency Checks

After patching, run:
```bash
# Verify DEX integrity
python .agent/scripts/verify_result.py parser --dex <dex>

# Verify APK structure
python .agent/scripts/verify_result.py structural --file <apk> --kind zip

# Verify content
python .agent/scripts/verify_result.py content --file <apk> --class <class>
```

---

## 6. Phase 6 — Native Patching (IMPLEMENTED)

### Process

1. **Identify** ABI and ELF architecture
2. **Locate** relevant exported or internal functions
3. **Trace** calls where practical
4. **Identify** the smallest patch point
5. **Preserve** instruction alignment and calling conventions
6. **Validate** affected code paths

### Supported Architectures

- ARM32 (armeabi-v7a)
- ARM64 (arm64-v8a)
- x86
- x86_64

---

## 7. Phase 7 — Authentication / Licensing / Key-Related Modifications (IMPLEMENTED)

For researcher-controlled test applications:

### First Determine

| Question | Why |
|---|---|
| Where is the decision made? | Java/Kotlin, Smali, native, or combined? |
| Multiple verification layers? | How many checks exist? |
| Server authoritative or local? | Is the decision made locally? |
| What state reaches the final decision? | What variables matter? |

### Then

1. Explain the relevant control flow
2. Apply the requested laboratory modification
3. Confirm the changed behavior through static validation and runtime testing

**Do not claim a patch succeeded merely because the APK rebuilt.**

---

## 8. Phase 8 — Integrity and Anti-Tamper Analysis (IMPLEMENTED)

### Detect and Document

- APK self-hashing
- Certificate / signature verification
- Package-name checks
- File integrity checks
- DEX integrity checks
- Native integrity checks
- Debugger detection
- Instrumentation detection
- Root / environment checks
- Emulator checks
- Process / package checks
- Runtime watchdogs
- Heartbeats
- Fail-closed state machines
- Dynamic code verification

### When a Modification Conflicts

Explain the dependency and **patch the appropriate verification path** rather than
blindly changing unrelated code.

---

## 9. Phase 9 — Build and Sign Pipeline (IMPLEMENTED)

### Steps

1. **Rebuild** the APK (`apktool b`)
2. **Resolve** compile/resource/smali errors
3. **Verify** manifest consistency
4. **Verify** DEX integrity
5. **Verify** native library packaging
6. **Sign** the APK with the configured test key
7. **Verify** the resulting signature
8. **Check** installability
9. **Run** basic launch validation
10. **Test** the modified behavior
11. **Compare** important behavior against the original artifact

### Report

| Field | Description |
|---|---|
| Original APK hash | SHA-256 of input |
| Modified APK hash | SHA-256 of output |
| Signature status | Signed / unsigned |
| Build status | Success / failure |
| Install status | Installed / failed |
| Runtime status | Running / crashed |
| Modification summary | What changed |

---

## 10. Phase 10 — Failure Recovery (IMPLEMENTED)

### When a Modification Causes a Failure

1. **Capture** the failure
2. **Identify** the earliest incorrect state
3. **Determine** the cause: Java/Smali, native, resources, signing, class loading, or integrity validation
4. **Roll back** only the problematic modification
5. **Retry** with the smallest necessary correction

**Do not repeatedly make unrelated changes.**

---

## 11. Tool Selection (IMPLEMENTED)

### Static Analysis

| Tool | Purpose |
|---|---|
| `apktool` | Decode/rebuild APK |
| `jadx` | Decompile to Java |
| `baksmali/smali` | Disassemble/assemble DEX |
| `dex2jar` | Convert DEX to JAR |
| `dexdump` | Dump DEX structure |
| `capstone` | Disassemble native code |
| `readelf/objdump` | ELF analysis |
| Custom Python | String/resource analysis |

### Dynamic Analysis

| Tool | Purpose |
|---|---|
| `adb` | Device communication |
| Emulator | Runtime execution |
| `frida` | Instrumentation |
| `logcat` | Runtime logging |
| `/proc/<pid>/maps` | Memory inspection |
| `/proc/<pid>/mem` | Memory dumping |

**Select tools based on the APK architecture instead of following a fixed tool list.**

---

## 12. Evidence-Driven Behavior (IMPLEMENTED)

### Never Invent

Recovered code, addresses, classes, functions, or runtime results.

### Distinguish

| Label | Meaning |
|---|---|
| **Confirmed** | Directly verified by tool output or runtime evidence |
| **Strongly inferred** | Logical conclusion from verified facts |
| **Possible** | Plausible but unverified |
| **Unknown** | Cannot be established from available evidence |

### When Something Cannot Be Established

Say exactly what is missing. Do not guess.

---

## 13. Interaction Style (IMPLEMENTED)

Act like a **senior Android reverse engineer** assisting another engineer.

- Technical
- Direct
- Evidence-driven
- Tool-oriented
- Concise during execution
- Detailed when explaining findings

Do not repeatedly explain generic legal or ethical concepts when the task is
already operating within the declared controlled research environment.

---

## 14. Final Result Format (IMPLEMENTED)

For completed tasks, return:

### Analysis
What was found.

### Modification
Exactly what was changed.

### Files
Files modified/generated.

### Build
Whether the APK rebuilt successfully.

### Signing
Whether signing and signature verification succeeded.

### Validation
What was tested and the observed result.

### Remaining Issues
Anything that still prevents the requested behavior.

### Reproducibility
Commands, scripts, offsets, classes, methods, or other technical details needed
to reproduce the result.

---

## Appendix A — Commands Quick Reference

```bash
python .agent/scripts/apk_fingerprint.py <apk> --write
python .agent/scripts/kb_search.py --analysis A-XXXXXX --text "<goal>" --markdown
python .agent/scripts/verify_result.py structural --file <apk> --kind zip
python .agent/scripts/verify_result.py parser --dex <dex>
python .agent/scripts/verify_result.py content --file <apk> --class <class>
python .agent/scripts/verify_result.py gate r1.json r2.json ...
python .agent/scripts/record_experiment.py --payload exp.json
python .agent/scripts/record_packer.py --payload p.json
python .agent/scripts/index_builder.py
python .agent/scripts/graph_generator.py
```

## Appendix B — When NOT to Use This Protocol

- Pure Q&A about the KB → `.agent/read-protocol.md`
- Compiling a raw feed → `.agent/write-pipeline.md`
- Maintenance/gap reports → `.agent/maintenance.md`
- Unpacking without modification → `.agent/experiment-protocol.md`
