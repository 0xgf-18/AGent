---
type: packer
topic: wiki/packers/_index
source: wiki/techniques/apk-unpacking-playbook
tags: ["packer", "srpatch", "mocika-shield", "recursive-nest", "assets-base-apk", "overlapping-entries", "offline-full-recovery"]
complexity: advanced
completeness: complete
last_verified: 2026-10-02
packer_id: srpatch
name: "SRPatch (Mocika Shield)"
aliases: ["SRPatch", "Mocika Shield", "dev.mocika.shield", "msk", "com.srp.patch.Init", "libSRPatch.so", "libmoduleapisupport.so", "SRPatch_config.json", "pathRedirectionEnabled"]
protection_class: packer
first_seen: 2026-10-02
indicators: ["assets/patch/SRPatch_config.json present with keys apkSize/originalApplicationName/packageName/pathRedirectionEnabled/pmsProxyMethod/signature/signatureStrength", "assets/patch/lib/<abi>/libSRPatch.so present (packer-owned loader)", "lib/<abi>/libmoduleapisupport.so added by the packer (outer levels only)", "assets/base.apk present AND itself contains an entry named assets/base.apk — the recursive nest", "application android:name is a packer class (msk.p at the outer levels, com.srp.patch.Init one level deeper) instead of the app's own", "shell dex is 1 dex / 19 class_defs with zero strings from the app package", "config apkSize equals the byte length of the deepest nest level exactly", "config originalApplicationName is android.app.Application, matching the deepest level's <application> which has no android:name"]
unpacking_status: unpacked
confidence: 0.8
evidence: []
technique_ids: ["T-0001", "T-0002", "T-0008", "T-0020"]
tools: ["TR-0001", "TR-0005", "TR-0008"]
documented_in: wiki/techniques/apk-unpacking-playbook
version: 1
created_timestamp: 2026-10-02T00:00:00
updated_timestamp: 2026-10-02T00:00:00
llm_summary: "SRPatch (Mocika Shield) wraps an APK in a RECURSIVE chain of nested zips: every level stores its predecessor's successor at the literal entry name assets/base.apk, so the payload is not appended, not encrypted and not carved — it is simply buried N zips deep. FakePing V3.1 has four levels: 41,143,301 (application=msk.p, 1 dex/19 class_defs) -> 29,340,419 (msk.p, 1/19) -> 17,542,149 (com.srp.patch.Init, 6 dex/7256 class_defs) -> 11,173,014 (application=android.app.Application, 4 dex/7218 class_defs, ZERO packer artifacts). The critical trap is that the level-2 assets/base.apk is built with DELIBERATELY OVERLAPPING entries, so Python zipfile refuses it with BadZipFile 'Overlapped entries ... possible zip bomb'; you must read it from the raw local-file header instead: data_start = header_offset + 30 + filename_len + extra_len, then slice file_size bytes (the entry is STORED). Descend until a level has no assets/base.apk — that level is the original. Three independent proofs pick the right level out of four: (1) assets/patch/SRPatch_config.json apkSize=11173014 equals the deepest level's byte length exactly; (2) the same config's originalApplicationName=android.app.Application equals the deepest level's application, which has no android:name; (3) the signer switches from the packer's re-sign (CN=Android, a40da80a...) to the developer's original (CN=Android Debug, 81209eea...) exactly at that level, and the packer artifacts (config, libSRPatch.so, libmoduleapisupport.so) drop to zero. No rebuild is required — the deepest level is already a complete, signed, installable APK. Fast path: scripts/packers/srpatch.py."
---

# Packer: SRPatch (Mocika Shield)

> ## The payload is not encrypted — it is just nested
>
> SRPatch does not append, encrypt or fragment anything. It re-packs the original
> APK as a STORED entry named `assets/base.apk` inside another APK, and repeats.
> Unpacking is therefore a **peel**, not a decrypt: descend the chain until a level
> has no `assets/base.apk`, and that level is the original.
>
> Two things stop this from being trivial:
>
> 1. **The middle level defeats `zipfile`.** `assets/base.apk` at level 2 is built
>    with deliberately overlapping entries, so Python raises
>    `BadZipFile: Overlapped entries: 'assets/base.apk' (possible zip bomb)`.
>    You must read it from the raw local-file header instead (Step 3).
> 2. **The chain self-decoys.** Every level carries the same
>    `SRPatch_config.json`, including one level that is *still packed*. Presence
>    of the config tells you the packer, never the depth — only the config's own
>    `apkSize` field does (Step 4).
>
> Fast path: `python scripts/packers/srpatch.py <apk>`

## This Article Answers
- "How do I recognize SRPatch (Mocika Shield) on an APK?"
- "How do I unpack SRPatch (Mocika Shield)?"
- "What is verified for this packer and what is still unverified?"

## Key Takeaways
- [RECOGNIZE] `assets/patch/SRPatch_config.json` + `assets/patch/lib/<abi>/libSRPatch.so` + an `assets/base.apk` entry that itself contains an `assets/base.apk` entry; application is a packer class (`msk.p`, then `com.srp.patch.Init`), shell dex is 1 dex / 19 class_defs with no app-package strings
- [METHOD] Fingerprint -> descend the `assets/base.apk` chain using raw local-file-header slices (zipfile refuses the overlapping level) -> stop at the first level with no `assets/base.apk` -> prove it with `apkSize`, `originalApplicationName` and the signer switch -> validate dex and gate
- [STATUS] `unpacked` — verified on exactly one APK (FakePing V3.1); see Evidence
- [CONFIDENCE] 0.8
- [EVIDENCE] none recorded yet — single-APK verification, inline only

## Identification
| Indicator | Where | How to detect |
|---|---|---|
| `assets/patch/SRPatch_config.json` present, keys `apkSize` `originalApplicationName` `packageName` `pathRedirectionEnabled` `pmsProxyMethod` `signature` `signatureStrength` | assets | inspect |
| `assets/patch/lib/<abi>/libSRPatch.so` present | assets | inspect |
| `lib/<abi>/libmoduleapisupport.so` present (outer levels) | lib | inspect |
| `assets/base.apk` present AND that entry itself contains an entry named `assets/base.apk` | assets | inspect |
| application `android:name` is `msk.p` (outer) or `com.srp.patch.Init` (deeper), both outside the app package | manifest | inspect |
| shell dex: 1 dex, `class_defs_size=19`, zero strings from the app package | dex | inspect |
| `config apkSize` == byte length of the deepest level | assets | compare |
| `config originalApplicationName` == `android.app.Application` and the deepest level's `<application>` has no `android:name` | assets + manifest | compare |
| deepest level carries the *original* signer while every level above carries the packer's re-sign | signature | `apksigner verify --print-certs` |

## Unpacking Status
- **Status:** unpacked
- **Documented in:** wiki/techniques/apk-unpacking-playbook
- **Techniques:** T-0001, T-0002, T-0008, T-0020
- **Tools:** TR-0001, TR-0005, TR-0008

## Unpacking Method

### Step 1: Fingerprint on all three strong indicators before descending
**Action:** Require, all at once: `assets/patch/SRPatch_config.json` parses as JSON with an `apkSize` key; `assets/patch/lib/<abi>/libSRPatch.so` exists; and `assets/base.apk` exists *and* the bytes you read from it contain an entry also named `assets/base.apk`. Any one alone is weak — `libmoduleapisupport.so` in particular is dropped by the deeper level and must never be required.
**Tool:** host python (`zipfile`, `json`)
**Expected:** all three hit on the packed input
**Success Indicator:** three green; a single red means exit 20, do not descend
**Failure Mode:** keying on `libmoduleapisupport.so` — level 2 does not have it, so a fingerprint that requires it rejects a real SRPack APK one level down.

### Step 2: Establish the shell baseline so you can recognise the original later
**Action:** For the input level, record `class_defs_size` of every dex (dex header offset 0x60), the application `android:name`, and the signer DN. FakePing's two outer levels are 1 dex / 19 class_defs with application `msk.p` and DN `CN=Android`. This is the number you are trying to get *away* from: the original must be dramatically different, not marginally.
**Tool:** TR-0005 aapt2 `dump xmltree --file AndroidManifest.xml`, host python
**Expected:** tiny `class_defs`, app-package string count 0
**Success Indicator:** shell `class_defs` is tens, not thousands, and no `L<package>/` descriptor resolves
**Failure Mode:** reading the application block by scanning forward for `android:name` without stopping at the first nested `E:` element — aapt2 indents child elements (`E: activity`) inside `<application>`, so an over-run returns the *launcher activity* and makes a clean original look packed. Stop at the first `E:` line whose indent exceeds the `E: application` line's indent.

### Step 3: Descend using the raw local-file header, not `zipfile.read`
**Action:** At each level, locate the `assets/base.apk` local file header at `header_offset`, then read `namelen = u16 @ h+26`, `extralen = u16 @ h+28`, and set `data_start = h + 30 + namelen + extralen`. The entry is always STORED (`compress_type == 0`), so the next level is simply `cur[data_start : data_start + file_size]`. Do **not** call `zipfile`'s `read()` — level 2 overlaps its neighbours and raises.
**Tool:** host python (`struct`, `zipfile` for the header only)
**Expected:** observed local-file headers on FakePing V3.1 —

| level | bytes | header_offset | namelen | extralen | data_start | file_size |
|---|---|---|---|---|---|---|
| 0 | 41,143,301 | 0 | 15 | 3 | 48 | 29,340,419 |
| 1 | 29,340,419 | 0 | 15 | 3 | 48 | 17,542,149 |
| 2 | 17,542,149 | 4,193,833 | 15 | 426 | 4,194,304 | 11,173,014 |

**Success Indicator:** the slice's own EOCD (`rfind PK\x05\x06`) sits at `len - 22 - cdsize`, i.e. zero trailing bytes, and `zipfile` opens it
**Failure Mode:** `zipfile.BadZipFile: Overlapped entries: 'assets/base.apk' (possible zip bomb)` — this is expected at the middle level, not a corrupt input. Falling back to a hardcoded offset works on one APK and silently returns garbage on the next.

### Step 4: Stop at the first level with no `assets/base.apk`, then prove it three ways
**Action:** The loop terminates when a level has no `assets/base.apk`. Do not take "no more nesting" as proof — prove the winner independently with all three: (a) `config apkSize` equals this level's byte length exactly; (b) `config originalApplicationName` equals this level's application (`android.app.Application` == a `<application>` with no `android:name`); (c) packer artifacts drop to zero (`assets/base.apk`, `assets/patch/*`, `libmoduleapisupport.so` all absent) while the signer switches from the packer's `CN=Android` to the original `CN=Android Debug`.
**Tool:** TR-0005 aapt2, TR-0008 apksigner, host python
**Expected:** FakePing V3.1: `apkSize=11173014` == 11,173,014 bytes; `originalApplicationName="android.app.Application"` == application (default); artifacts NONE; signer `81209eeaa0b20b9cb614231ab50cd095e3c1ba5e85c04fd160aff6c9008c24f8` vs outer `a40da80a59d170caa950cf15c18c454d47a39b26989d8b640ecd745ba71bf5dc`
**Success Indicator:** all three agree
**Failure Mode:** trusting any single signal. `apkSize` alone is strong but could collide with an intermediate; artifacts alone fail because level 2 already dropped `libmoduleapisupport.so`. Only the three together distinguish level 3 from level 2.

### Step 5: Validate the recovered dex and gate it before claiming anything
**Action:** For every dex in the winner, require magic `dex\n035\0`, `file_size == len(blob)`, `adler32(blob[12:]) == u32@8`, `sha1(blob[32:]) == blob[12:32]`. Then count `L<package>/` descriptors across all recovered dex and require a non-zero count in the app's own package, plus zero descriptors for the packer's shell (`Ldev/mocika/shield/`, `Lmsk/`, `Lcom/srp/`). Write the deliverable as `<input-stem>-unpacked.apk` next to the input and the dex to `<input-stem>-unpacked-dex/`. Run `verify_result.py gate` and require VERIFIED_SUCCESS with at least three categories and zero FAIL.
**Tool:** TR-0009 dexdump / host python, `.kb/scripts/verify_result.py`
**Expected:** FakePing V3.1 — 4 dex, all checksums valid, 7,218 class_defs, 163 `Lcom/mducdz/fakeping/` types, zero packer descriptors
**Success Indicator:** `gate` exit 0, verdict `VERIFIED_SUCCESS`
**Failure Mode:** stopping at "dex checksums pass". Checksums prove a blob is *intact*, not that it is *the app* — this exact confusion produced a wrong deliverable once during FakePing analysis (Zip B, an intermediate that is still packed, was shipped before the three-way proof in Step 4 caught it).

### Step 6: Cold-launch the deliverable — no rebuild is needed
**Action:** Install the recovered APK as-is and launch its declared activity. SRPatch's deepest level is already a complete, signed APK, so there is no apktool round-trip, no manifest patching and no re-sign.
**Tool:** TR-0001 adb
**Expected:** install `Success`; `pidof <package>` returns a PID; zero `FATAL EXCEPTION` / `ClassNotFoundException` / `has died` lines in logcat
**Success Indicator:** process alive after a cold start
**Failure Mode:** re-signing the deliverable "to be safe" — that destroys the original certificate, which is one of the three proofs from Step 4 and the only thing tying the output back to the developer rather than to the packer.

## Decision Points
| Condition | If True | If False |
|---|---|---|
| `assets/base.apk` present at this level | read it (raw LFH) and descend | this level is the original — stop |
| `zipfile.read("assets/base.apk")` raises `Overlapped entries` | fall back to the raw local-file-header slice (Step 3) | use either; the raw path works at every level |
| level still contains `assets/patch/*` or `libmoduleapisupport.so` | keep descending | candidate original — go to Step 4's three-way proof |
| `apkSize` == level byte length AND `originalApplicationName` == level application AND signer switched | accept and emit | keep descending or fail honestly |
| recovered dex contain `L<package>/` descriptors | proceed to gate | exit 10 (COMMAND_SUCCESS, not learnable) |

## Verification
| Category | Check | Pass condition |
|---|---|---|
| STRUCTURAL | nest + output zip | every level's EOCD has zero trailing bytes; the emitted APK opens as a zip with zero `assets/base.apk` / `assets/patch/*` / `libmoduleapisupport.so` |
| PARSER | dex header | magic `dex\n035\0`, `file_size == len`, `adler32(bytes[12:])` matches, `sha1(bytes[32:])` matches, for **every** recovered dex |
| CONTENT | class probe | ≥1 descriptor from `L<package>/` present; zero `Ldev/mocika/shield/`, `Lmsk/`, `Lcom/srp/` descriptors |
| DOWNSTREAM | apksigner + install | `apksigner verify` passes; adb install succeeds; cold launch leaves a live PID with no crash lines |
| REPRODUCIBILITY | re-peel from the original | re-running the full peel from the packed input yields an identical sha256 of the recovered dex |

## Known Failure Conditions
| Condition | Symptom | Workaround |
|---|---|---|
| `zipfile.read("assets/base.apk")` at the middle level | `BadZipFile: Overlapped entries: 'assets/base.apk' (possible zip bomb)` | expected — slice from `header_offset + 30 + namelen + extralen` (Step 3) |
| Fingerprint requiring `libmoduleapisupport.so` | a genuine SRPack APK rejected with exit 20 | that file exists only on the outer levels; require config + `libSRPatch.so` + the nest instead |
| Scanning the manifest for the first `android:name` after `E: application` | clean original reported as packed because the launcher activity's name is read as the application | stop attribute scanning at the first nested `E:` line (Step 2) |
| Taking the first level that "looks unpacked" | a level with 6 dex / 7,256 class_defs and application `com.srp.patch.Init` accepted as the original | that is an intermediate — it still carries the config and `libSRPatch.so`; run all three proofs (Step 4) |
| Stopping at "checksums pass" | a checksum-valid APK that is not the app | count `L<package>/` descriptors and require zero packer descriptors (Step 5) |
| Hardcoding the observed offsets (48 / 4,194,304) | works on FakePing, returns garbage on any other SRPack APK | always parse the local-file header; the table in Step 3 is evidence, not an input |
| Re-signing the deliverable | installs fine, but the original `CN=Android Debug` certificate is lost | the deepest level is already signed — emit it unchanged |

## Evidence
| Experiment | Result | Notes |
|---|---|---|
| inline (no EXP record yet) | VERIFIED | FakePing V3.1 — 4-level nest peeled to 11,173,014 B; `verify_result.py gate` exit 0, `VERIFIED_SUCCESS`, 5/5 categories (STRUCTURAL, PARSER, CONTENT, DOWNSTREAM, REPRODUCIBILITY); reproducibility by re-peeling from the packed input; adb cold launch live PID, zero crash lines |

## Version History
| Version | Date | Change | Reason |
|---|---|---|---|
| 1 | 2026-10-02 | Create | initial recording from FakePing V3.1 |

## What This Article Does NOT Cover
- variants with a different nesting depth or a non-`assets/base.apk` entry name
- variants whose `assets/base.apk` is DEFLATE-compressed rather than STORED (the method in Step 3 assumes `compress_type == 0` and must be extended if that fails)
- whether the `signature` / `pathRedirectionEnabled` / `pmsProxyMethod` config fields are honoured at runtime, and what they do to a repacked APK
- the behaviour of `libSRPatch.so` itself — it was not disassembled; the method here needs only the container structure

## Related
- [[wiki/techniques/apk-unpacking-playbook]] - playbook with verbatim commands
- [[wiki/techniques/T-0001]] - APK triage & packer fingerprinting
- [[wiki/techniques/T-0002]] - Stub / Application / ClassLoader mapping
- [[wiki/techniques/T-0020]] - Packed-APK baseline verification gate (shell-dex triage)
- [[wiki/packers/_index]] - packer index
