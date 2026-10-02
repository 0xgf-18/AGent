---
type: packer
topic: wiki/packers/_index
source: wiki/experiments/EXP-0002
tags: ["packer", "chiko", "neoark", "art-jiagu", "appended-payload", "xor", "offline-partial-recovery", "root-required-for-full-unpack"]
complexity: advanced
completeness: complete
last_verified: 2026-09-30
packer_id: chiko-neoark
name: "Chiko / NeoArk (Art-Jiagu family)"
aliases: ["Chiko", "chikoStub", "NeoArk", "Art-Jiagu", "b2al.encryp.vip", "ark_payload_%d.dex", "HSSkyBoy/Art-Jiagu", "com/ark/safe/StubApp"]
protection_class: packer
first_seen: 2026-09-30
indicators: ["AndroidManifest.xml application android:name is an obfuscated class outside the app package (e.g. b2al.encryp.vip for com.mducdz.fakeping)", "classes.dex header is tiny but file_size is huge: data_off+data_size ~= 0x3a4 while file_size is multi-MB (appended payload past every DEX section)", "classes.dex has class_defs_size=1 and string_ids_size<32 (loader shell only)", "stub source_file_idx names StubApp.java; <clinit> calls System.setProperty(\"ark\", <packer class>) then System.loadLibrary(\"chikoStub\")", "attachBaseContext is declared 'PROTECTED NATIVE' (access 0x0104) with no code body", "lib/<abi>/libchikoStub.so with JNI_OnLoad present and ZERO Java_* exports (dynamic RegisterNatives)", "loader .so strings: ark_payload_%d.dex, ark_code_cache, ark_dex, ark_opt, com/ark/safe/StubApp", "assets/*jiagu* present but is a SHORT ASCII decoy, not a container (NeoArk plants these to bait tool identification)"]
unpacking_status: unpacked
confidence: 0.95
evidence: ["EXP-0002", "EXP-0003"]
technique_ids: ["T-0001", "T-0008", "T-0010", "T-0021", "T-0022"]
tools: ["TR-0004", "TR-0006", "TR-0009", "TR-0011"]
documented_in: "wiki/experiments/EXP-0002"
version: 3
previous_version: 2
version_reason: "Building the fast-path script (scripts/packers/chiko_neoark.py) forced the offline path to state what it actually yields. Measured, not assumed: the offline 64-byte XOR key yields exactly ONE valid dex, 9,303,180 B / 6,292 class_defs, and it contains ZERO classes in the app package com.mducdz.fakeping -- it is the AndroidX/Kotlin/logsender framework blob. The app logic is in a separate blob that this key does not reach. v2 said 'the primary blob is recoverable offline' without stating that the primary blob is not the app, and the 'offline-unpack' tag invited exactly the wrong conclusion. Added a prominent warning, replaced the misleading tag with offline-partial-recovery + root-required-for-full-unpack, and cross-linked T-0022 for the period-detection method. The script now asserts app-class presence and refuses to write a deliverable when it is absent, exiting 10 (COMMAND_SUCCESS, not learnable) instead of claiming success."
created_timestamp: 2026-09-30T12:30:00
updated_timestamp: 2026-09-30T12:30:00
llm_summary: "Chiko/NeoArk (Art-Jiagu family) appends XOR-encrypted dex blobs directly past the shell classes.dex data section instead of using an asset container, keeps them resident in memory via InMemoryDexClassLoader (nothing is ever written to /data/data), and plants fake 360 jiagu marker assets to poison filename-based fingerprinting. IMPORTANT: a full unpack REQUIRES a rooted device. The offline 64-byte repeating-XOR path (autocorrelation period detection + column-wise mode, no device) recovers exactly one blob, and that blob is the AndroidX/Kotlin framework dex -- it contains zero com.mducdz.fakeping classes, so it is NOT the app. The app's logic is in a separate blob under a different key. The complete method is dumping [anon:dalvik-DEX data] from /proc/<pid>/mem on a rooted device and carving on the dex header; adler32+sha1 validation makes each carved blob provably complete, and the memory path agrees byte-for-byte with the offline path on the one blob they share. Always confirm the recovered dex define classes in the app's own package before reporting success -- passing checksums only prove a blob is intact, not that it is the app. Rebuilding requires deleting the packer's manifest android:name (no Application subclass exists in the payload), dropping libchikoStub.so and the decoy asset, and keeping the app's own native lib. Fast path: scripts/packers/chiko_neoark.py."
---

# Packer: Chiko / NeoArk (Art-Jiagu family)

> ## ⚠️ The offline path does NOT unpack this packer
>
> **The offline XOR path recovers a real, checksum-valid, 9,303,180-byte dex — and
> that dex is not the app.** It is the AndroidX / Kotlin / androidide / logsender
> framework blob (6,292 class_defs). The app's own logic, including every
> `com.mducdz.fakeping.*` class, lives in a *different* blob (`classes3.dex`,
> 247,008 B, 151 class_defs) which the offline key does not reach, because the
> packer derives a different key per blob.
>
> So: **checksums passing is not the same as the app being unpacked.** Always
> confirm the recovered dex define classes in the app's own package before
> reporting success. This is Step 8 of the method below, and it exists because
> EXP-0002 originally reported a successful offline unpack on exactly this
> confusion.
>
> **A rooted device is required for a usable unpack.** The offline path is worth
> running because it is fast, needs no device, and validates the payload
> structure — not because it produces a usable APK.
>
> Fast path: `python scripts/packers/chiko_neoark.py <apk> --device`

## This Article Answers
- "How do I recognize Chiko / NeoArk (Art-Jiagu family) on an APK?"
- "How do I unpack Chiko / NeoArk (Art-Jiagu family)?"
- "What is verified for this packer and what is still unverified?"

## Key Takeaways
- [RECOGNIZE] AndroidManifest.xml application android:name is an obfuscated class outside the app package (e.g. b2al.encryp.vip for com.mducdz.fakeping); classes.dex header is tiny but file_size is huge: data_off+data_size ~= 0x3a4 while file_size is multi-MB (appended payload past every DEX section); classes.dex has class_defs_size=1 and string_ids_size<32 (loader shell only)
- [METHOD] Prefer the memory-harvest path when a rooted dev -> Disarm the decoy asset before believing any pack -> Confirm the appended-payload signature in classe -> Identify the stub and the native decryptor locat -> Find the keystream period by autocorrelation -> Recover the key by column-wise mode, then prove  -> Split the payload on the DEX file_size field, no -> Classify what you actually recovered before clai
- [STATUS] `unpacked` — verified on at least one APK (see Evidence)
- [CONFIDENCE] 0.95
- [EVIDENCE] EXP-0002, EXP-0003

## Identification
| Indicator | Where | How to detect |
|---|---|---|
| AndroidManifest.xml application android:name is an obfuscated class outside the app package (e.g. b2al.encryp.vip for com.mducdz.fakeping) | static | inspect |
| classes.dex header is tiny but file_size is huge: data_off+data_size ~= 0x3a4 while file_size is multi-MB (appended payload past every DEX section) | static | inspect |
| classes.dex has class_defs_size=1 and string_ids_size<32 (loader shell only) | static | inspect |
| stub source_file_idx names StubApp.java; <clinit> calls System.setProperty("ark", <packer class>) then System.loadLibrary("chikoStub") | static | inspect |
| attachBaseContext is declared 'PROTECTED NATIVE' (access 0x0104) with no code body | static | inspect |
| lib/<abi>/libchikoStub.so with JNI_OnLoad present and ZERO Java_* exports (dynamic RegisterNatives) | static | inspect |
| loader .so strings: ark_payload_%d.dex, ark_code_cache, ark_dex, ark_opt, com/ark/safe/StubApp | static | inspect |
| assets/*jiagu* present but is a SHORT ASCII decoy, not a container (NeoArk plants these to bait tool identification) | static | inspect |

## Unpacking Status
- **Status:** unpacked
- **Documented in:** wiki/experiments/EXP-0002
- **Techniques:** T-0001, T-0008, T-0010
- **Tools:** TR-0004, TR-0006, TR-0009, TR-0011

## Unpacking Method
### Step 1: Prefer the memory-harvest path when a rooted device is available; it recovers EVERYTHING
**Action:** Check /data/data/<pkg> file count before and after launch. If unchanged, the loader writes no dex to disk (InMemoryDexClassLoader) and on-device file harvesting is a dead end. Launch the app, then read [anon:dalvik-DEX data] ranges from /proc/<pid>/maps and dd each from /proc/<pid>/mem (iflag=skip_bytes,count_bytes). Carve on the 'dex\n' magic and REQUIRE adler32==u32@8 and sha1(b[32:])==b[12:32] before accepting a blob. Observed: exactly one dex per region, at offset 0, and all four passed both checksums.
**Tool:** TR-0001 adb + su, host python (zlib, hashlib)
**Expected:** one self-validating dex per anon DEX region, with the region sizes roughly matching the appended payload blob sizes
**Success Indicator:** adler32 AND sha1 both match for every carved blob; the largest region equals the offline-recovered primary blob's size
**Failure Mode:** Reading /proc/<pid>/mem without root returns EACCES/permission denied -- the shell uid cannot read another uid's memory. And the payload regions only exist AFTER attachBaseContext has run, so the app must be launched first.

### Step 2: Disarm the decoy asset before believing any packer verdict
**Action:** Read the raw bytes of any assets/*jiagu* entry. If it is short (<1 KB) and decodes as readable ASCII containing 'fake ... marker' or a GitHub URL, it is a decoy and the detection is a FALSE POSITIVE. Do not start the 360 jiagu method.
**Tool:** TR-0001 / host unzip
**Expected:** either a real container (magic 'PokeGuard' for 360 jiagu) or a decoy text file
**Success Indicator:** asset > 1 KB with non-ASCII body, or a recognisable container magic
**Failure Mode:** Trusting apk_fingerprint.py 'entry-name heuristic' confidence -> wrong packer, wrong whole technique chain (this is exactly what happened on crackme.apk)

### Step 3: Confirm the appended-payload signature in classes.dex
**Action:** Parse the DEX header: file_size (off 0x20) vs data_off+data_size (off 0x68/0x6c). A ratio near 1.0 means a normal dex; a ratio of thousands means an appended payload. Note that adler32/sha1 still validate over the whole file because the packer recomputes them, so a PARSER PASS on the shell does NOT mean the app is unpacked.
**Tool:** TR-0009 dexdump -f
**Expected:** shell data section ends early (e.g. 0x3a4) while file_size is ~10 MB
**Success Indicator:** (file_size - (data_off+data_size)) > 1 MB
**Failure Mode:** None; this check is always valid and costs one header parse

### Step 4: Identify the stub and the native decryptor location
**Action:** dexdump -d the shell. Read the single class descriptor, source_file, and <clinit>. The System.loadLibrary argument names the decryptor .so. Confirm attachBaseContext is native. Then extract that .so and check dynsym: JNI_OnLoad present with 0 Java_* exports means dynamic RegisterNatives (so static method-name lookup will not work).
**Tool:** TR-0009 dexdump, host ELF parse
**Expected:** packer class + decryptor library name + confirm dynamic registration
**Success Indicator:** loadLibrary("chikoStub") and native attachBaseContext
**Failure Mode:** Expecting Java_* symbols in the .so; there are none by design

### Step 5: Find the keystream period by autocorrelation
**Action:** Autocorrelate the raw ciphertext against itself for lags 1..512 (sample the first ~200k bytes). A repeating-key XOR shows a sharp spike at the key period and its multiples; random or real encryption stays flat at ~0.39%.
**Tool:** host python
**Expected:** spike at the key length (64 for observed Chiko builds) and at 2x, 3x, 4x of it
**Success Indicator:** one lag far above the rest (e.g. 50.85% at lag 64 while all others <= 1.85%)
**Failure Mode:** A ~50% (not ~100%) spike still means XOR -- do not reject it as noise. Forcing 100% would mean a constant byte and a completely different cipher.

### Step 6: Recover the key by column-wise mode, then prove it with checksums
**Action:** For i in 0..period-1: key[i] = most frequent byte of ciphertext[i::period]. This assumes the most common plaintext byte in each column is 0x00, which holds for DEX data sections. Decrypt as plain[j] = cipher[j] ^ key[j%period], then read the first DEX header and verify adler32 over bytes[12:] and sha1 over bytes[32:].
**Tool:** host python (zlib, hashlib)
**Expected:** 'dex\n035\0' magic, file_size within payload length, header_size 112, endian 0x12345678, and BOTH adler32 and sha1 matching
**Success Indicator:** adler32 stored == computed AND sha1 == stored signature (this is what makes the recovery certain rather than probabilistic)
**Failure Mode:** If the blob's plaintext is not zero-dominated, column mode yields a wrong key. Symptom: magic is right but adler32/sha1 mismatch, or file_size is absurd. Fix: derive the key from the native cipher in libchikoStub.so, or crib-drag using DEX header constraints (file_size < payload length).

### Step 7: Split the payload on the DEX file_size field, not on a fixed stride
**Action:** Read u32 at offset 0x20 of each decrypted blob to get its file_size, emit exactly that many bytes, and continue at the next offset. Check whether the final 4 bytes of the payload are a small integer (an observed value of 4 suggests a blob count).
**Tool:** host python
**Expected:** the first blob's length equals its own file_size field exactly (structural proof the split is right)
**Success Indicator:** consumed length == file_size field for the first blob
**Failure Mode:** Assuming one keystream alignment for the whole payload. Verified: in the observed case a SECOND blob of 857,167 B followed the first 9,303,180 B, used a DIFFERENT key, and resisted both column-mode recovery at all 64 rotations and all standard decompressors (zlib/gzip/lzma/bz2). Expect per-blob keys.

### Step 8: Classify what you actually recovered before claiming success
**Action:** Enumerate class_defs and scan the string table for the target package (e.g. 'mducdz', 'fakeping'). A decrypted dex can be perfectly valid yet hold a different component than the app's business logic. In the observed case the recovered dex was a complete androidide log-sender (6292 class_defs, com.itsaky.androidide.*) with ZERO target-package strings.
**Tool:** TR-0009 dexdump, host string-table walk
**Expected:** target package classes present in the recovered dex
**Success Indicator:** target package string present in the DEX string table
**Failure Mode:** Declaring the packer beaten on checksum validity alone. A valid dex is necessary but not sufficient -- always confirm it is the RIGHT dex.

## Decision Points
| Condition | If True | If False |
|---|---|---|
| loader keeps payloads in memory (InMemoryDexClassLoader) and writes nothing to disk | None | None |
| decoy marker planted by NeoArk | None | None |
| appended payload confirmed | None | None |
| real stream/block cipher or compressed-then-encrypted | None | None |
| wrong key alignment or wrong column-mode assumption | None | None |
| per-blob key | None | None |
| recovered a helper component, not the app | None | None |

## Verification
| Category | Check | Pass condition |
|---|---|---|
| PARSER | dex header | magic dex\n035\0, file_size == blob length, adler32(bytes[12:]) == stored, sha1(bytes[32:]) == stored signature |
| STRUCTURAL | payload split | the first decrypted blob's length equals its own file_size field exactly, and the shell's data_off+data_size is a tiny fraction of file_size |
| CONTENT | class probe | target package class descriptors present in the recovered dex, and zero packer-stub classes (b2al/encryp/vip, com/qihoo/*) inside it |
| REPRODUCIBILITY | sha256 stability | re-running the full extract from the same APK yields an identical sha256 |
| DOWNSTREAM | dexdump / jadx acceptance | the recovered dex loads and enumerates class_defs without error |

## Known Failure Conditions
| Condition | Symptom | Workaround |
|---|---|---|
| Assuming the standard on-device unpack-directory harvest applies | you search /data/data and /sdcard for ark_payload_*.dex forever and find nothing | Diff the data-dir file count across a launch; unchanged means in-memory -- switch to /proc/<pid>/maps [anon:dalvik-DEX data] + /proc/<pid>/mem |
| Column-mode key recovery on a non-zero-dominated blob | DEX magic present but adler32/sha1 mismatch, or file_size far larger than the payload | Derive the key from libchikoStub.so; the observed secondary blob resisted all 64 phase rotations |
| Only one key assumed for the whole payload | first dex perfect, remaining bytes are garbage | Treat each appended blob as independently keyed; verify per blob via its own checksums |
| Packer detection taken from the entry-name heuristic | a full 360 jiagu technique chain applied to a Chiko APK | Always corroborate filename heuristics with magic bytes and payload structure |
| No device and no root | dynamic harvest (memory scar, /data/data harvesting) unavailable | Not needed for the primary blob -- the offline XOR path recovered a verified 9.3 MB dex on a host-only box |
| Rebuild keeps the packer's manifest android:name | all dex are valid and the APK installs, but the app crashes at startup trying to instantiate the packer stub (b2al.encryp.vip), which was never a real Application subclass | List every class superclass in the recovered dex; if none extends android.app.Application, delete the android:name attribute from <application> entirely |
| All native libs dropped as 'packer files' | UnsatisfiedLinkError or missing-symbol crash on a feature that uses the app's own native code | Classify per library: libchikoStub.so is packer-owned (drop), libfping.so is app-owned (keep). The name alone does not tell you which. |

## Evidence
| Experiment | Result | Notes |
|---|---|---|
| EXP-0002 | VERIFIED | see experiment article |
| EXP-0003 | VERIFIED | see experiment article |

## Version History
| Version | Date | Change | Reason |
|---|---|---|---|
| 1 | 2026-09-30 | Update | initial recording |
| 2 | 2026-09-30 | Update | EXP-0003 recovered ALL payload blobs (4 dex, 6738 class_defs) including the target com.mducdz.fakeping business logic, and produced a signed APK that installs and cold-launches. The offline XOR path documented in v1 recovered only the primary blob; the memory-harvest path in v2 is the complete method. |

## What This Article Does NOT Cover
- variants not covered by the recorded evidence

## Related
- [[wiki/techniques/apk-unpacking-playbook]] - playbook with verbatim commands
- [[wiki/techniques/T-0021]] - **start here**: storage-model detection (this packer is memory-resident, so T-0019 is a dead end and T-0010 is the route)
- [[wiki/packers/_index]] - packer index
- [[wiki/experiments/EXP-0002]] — evidence experiment
- [[wiki/experiments/EXP-0003]] — evidence experiment
- [[wiki/techniques/apk-unpacking-playbook]] - T-0001 (triage & fingerprinting), T-0008 (DEX structural validation), T-0010 (memory-scarfing)
