---
type: packer
topic: wiki/packers/_index
source: wiki/techniques/apk-unpacking-playbook
tags: [packer, 360-jiagu, qihoo, pokeguard, vmp, container]
complexity: advanced
completeness: complete
last_verified: 2026-09-29
packer_id: 360-jiagu
name: 360 jiagu (PokeGuard-style variant)
aliases: ["360加固", "360 jiagu", "jiagu", "qihoo", "PokeGuard", "VenKiT Guard", "libjiagu", "libSecShell", "com.qihoo", "com.stub.StubApp"]
protection_class: packer
indicators: ["com.qihoo.util.* stub classes", "com.stub.StubApp application", "assets/libjiagu.so (custom container, not ELF)", "assets/ProtectV1|V2|V3.zip", "lib/<abi>/libSecShell.so exports vmInterpret/gVm", "small shell classes.dex (~44 KB, ~15 classes)"]
unpacking_status: unpacked
confidence: 0.9
evidence: [EXP-0001]
technique_ids: [T-0001, T-0002, T-0003, T-0008, T-0013, T-0014, T-0016, T-0017, T-0018, T-0019]
tools: [TR-0001, TR-0002, TR-0003, TR-0005, TR-0007, TR-0008, TR-0009]
documented_in: wiki/techniques/apk-unpacking-playbook
version: 1
created_timestamp: 2026-09-29T00:00:00
updated_timestamp: 2026-09-29T00:00:00
llm_summary: "360 jiagu / PokeGuard packer: recognized by com.qihoo.* + com.stub.StubApp stub, non-ELF assets/libjiagu.so container (74 encrypted dex), ProtectV*.zip, libSecShell VMP exports (vmInterpret/gVm). Verified unpack = T-0016 native char-table decode -> T-0017 container walk -> T-0018 VMP detect (go dynamic) -> T-0019 harvest plaintext dex from no_backup/dex_unpack on rooted device -> validate all dex -> clean rebuild (drop packer assets, keep lib/, fix Application in manifest, rezip/align/sign). Proven on pokemon.dex.guard (74 dex, 11378 classes, runs after rebuild); baseline verified via EXP-0001."
---

# Packer: 360 jiagu (PokeGuard-style variant)

## This Article Answers
- "How do I recognize 360 jiagu on an APK?"
- "How do I unpack 360 jiagu / PokeGuard?"
- "What is the verified unpacking workflow and its failure modes?"

## Key Takeaways
- [RECOGNIZE] stub `classes.dex` ~44 KB with `com.qihoo.util.*` + `com.stub.StubApp`; non-ELF `assets/libjiagu.so` container; `ProtectV*.zip`; `libSecShell.so` with `vmInterpret`/`gVm` exports
- [METHOD] char-table decode (T-0016) -> container walk (T-0017) -> VMP detection -> **dynamic harvest** of plaintext dex written to `no_backup/dex_unpack` (T-0019) -> validate (T-0008) -> clean rebuild (T-0013/T-0014)
- [STATUS] `unpacked` — 74 dex harvested and validated (11,378 classes); clean rebuild ran with stable pid + working UI [V]
- [EVIDENCE] playbook Case 3 [V] + baseline `[[wiki/experiments/EXP-0001]]` (VERIFIED_SUCCESS)
- [CAUTION] offline decrypt of the AES-GCM blob failed (key derived at runtime) — when you see VMP exports, stop static RE and go dynamic

## Identification

| Indicator | Where | How to detect |
|---|---|---|
| `com.qihoo.util.*` + `com.stub.StubApp` | classes.dex | `dexdump -d` / `verify_result.py content --class com.qihoo.util.VM` |
| Shell dex ≈ 44 KB, ~15 classes | classes.dex | entry inventory (apk_fingerprint.py) |
| `assets/libjiagu.so` is NOT an ELF (magic `PokeGuard`) | assets/ | magic-byte check: first 9 B = ASCII, not `\x7fELF` |
| `assets/ProtectV1.zip`…`ProtectV3.zip` | assets/ | zip magic `PK` |
| `vmInterpret`, `gVm`, `cacheInitial` exports, 0 `Java_*` | libSecShell.so | `readelf --dyn-syms` / capstone scan |
| Sorted native-name table in .rodata without xrefs | libSecShell.so | capstone ADRP scan |
| 74 plaintext entry names, encrypted bodies | libjiagu.so container | T-0017 walker |

## Unpacking Method (verified workflow)

> Every step below is `[V]` — proven end-to-end on `pokemon.dex.guard` (see Evidence).
> Full verbatim commands: [[wiki/techniques/apk-unpacking-playbook]] Case 3.

### Step 1: Triage & fingerprint (T-0001)
**Observation:** unknown APK, need packer id in < 5 min
**Action:** entry inventory + `aapt dump xmltree AndroidManifest.xml` + dexdump of stub
**Tool:** TR-0001/TR-0005/TR-0009 (or `.kb/scripts/apk_fingerprint.py`)
**Expected:** packer class in manifest (`com.stub.StubApp`), tiny shell dex, packer assets
**Success Indicator:** indicators table above all hit
**Failure Mode:** none — if no packer indicators, this packer does not apply

### Step 2: Stub / decoder mapping (T-0002, T-0003)
**Observation:** shell dex is the loader
**Action:** `apktool d <apk>` -> read StubApp smali; find `const-string` calls backed by `native decoder(short[], int, int, int)`
**Tool:** TR-0002
**Expected:** every protected string is a native char-table decode call
**Success Indicator:** `fill-array-data v0, :array_0` table (5032 shorts) found in smali
**Failure Mode:** no native decoder -> container holds the payload directly, go to Step 4

### Step 3: Char-table recovery (T-0016) [V]
**Observation:** strings hidden behind native XOR table
**Action:** regex `:array_0\s*\.array-data 2\s*(.*?)\.end array-data` from smali; XOR candidate `(start,len,key)` args read from the `invoke-static/range` (e.g. `v42=0x7c1`, `v40=0x10`, v41=key)
**Tool:** TR-0002 + python helper
**Code:** `plain = ''.join(chr(table[start + i] ^ key) for i in range(length))` — a hit is all-ASCII
**Success Indicator:** constants recovered: `AES_GCM_KEY="PokGuard1029Key!"`, `XOR_KEY="PoZeHello1#$03992030#1"`, `BLOB_MAGIC="PokeGuard"`, `ASSET_ENCRYPTED_BLOB="libjiagu.so"`
**Failure Mode:** non-ASCII output -> wrong (start,len,key) triple, re-read invoke args

### Step 4: Container walk (T-0017) [V]
**Observation:** `assets/libjiagu.so` = custom container
**Action:** parse `magic "PokeGuard"(9B) + 00 00 00 + u8 dexCount(0x4A=74)`, then `u16be nameLen | name | u32be cipherSize | cipher` × 74
**Tool:** python helper (walk must consume exactly file size)
**Expected:** walker EOF == file size (0x110025B) — structural proof
**Success Indicator:** 74 entries `classes.dex`…`classes74.dex`, plaintext names, encrypted bodies
**Failure Mode:** Repeating-XOR / single-byte-XOR / AES-ECB / AES-GCM-with-obvious-nonce **all failed** [V] — do not burn time here; go dynamic

### Step 5: VMP detection -> dynamic pivot (T-0018) [V]
**Observation:** native decryptor unreachable statically
**Action:** check `.dynsym` of `libSecShell.so`: `vmInterpret`, `gVm`, `cacheInitial`, `getCacheClass`, **0 `Java_*` symbols** + sorted 78-name table in .rodata with no ADRP xrefs
**Tool:** TR-0004 (capstone) / readelf
**Success Indicator:** VMP confirmed -> **abandon static RE of the decryptor**
**Failure Mode:** continuing static RE wastes hours (ViRex lesson)

### Step 6: On-device unpack-dir harvest (T-0019) [V]
**Observation:** protector writes plaintext dex to disk on first launch
**Action:**
```bash
adb install -r <apk>
adb shell am start -n <pkg>/.MainActivity
adb shell "su -c 'cp -r /data/data/<pkg>/no_backup/dex_unpack /sdcard/dex_unpack; chmod -R 777 /sdcard/dex_unpack'"
adb pull /sdcard/dex_unpack
```
**Tool:** TR-0001 (adb) + rooted device/emulator
**Expected:** 74 files, 17,822,544 B
**Success Indicator:** `su -c 'find /data/data/<pkg> -type f'` right after first launch shows the dex files
**Failure Mode:** no `dex_unpack` dir -> look for other written paths (`find ... -name '*.dex'`); no root -> memory scarfing fallback (T-0010)

### Step 7: Validate every dex (T-0008) [V]
**Action:** `dex\n035` magic + `file_size` vs real length + adler32(`d[12:]`) + sha1(`d[32:]`) — use `.kb/scripts/verify_result.py parser --dex <f>`
**Success Indicator:** all 74 valid; 11,378 class defs; real app = `<pkg>.SketchApplication` / `.MainActivity` (renamed set) + original package set
**Failure Mode:** checksum mismatch -> re-harvest (partial copy)

### Step 8: Clean rebuild (T-0013) [V]
**Action:**
1. synthetic zip = original APK **minus** `assets/libjiagu.so`, `assets/ProtectV*.zip`, packer dex, `META-INF/**` **plus** the 74 harvested dex; **keep `lib/`** (the real app needs `libIts_PokemonZ.so`)
2. `apktool d -f -s` -> edit `AndroidManifest.xml` `android:name` from `com.stub.StubApp` to the real application -> `apktool b`
3. `zipalign -f -p 4` -> `apksigner sign` -> `apksigner verify` -> `zipalign -c -p 4`
**Success Indicator:** signed APK installs (uninstall first — signer changed), stable pid, UI renders
**Failure Mode:** `UnsatisfiedLinkError in <clinit>` -> you stripped a native lib the real app loads; keep `lib/` and only drop packer *assets*

## Decision Points

| Situation | Condition | Action |
|---|---|---|
| Offline decrypt of blob fails | AES-GCM with runtime key | go dynamic (Step 6), do not retry constants |
| `vmInterpret` + name table w/o xrefs | VMP | abandon static decryptor RE |
| No `dex_unpack` after launch | dir absent | `find /data/data/<pkg> -type f` for any written `*.dex`, else T-0010 memory scarfing |
| Rebuild crashes `UnsatisfiedLinkError` | native lib stripped | keep original `lib/`, drop only packer assets |
| App class absent from plaintext dex | probe FAIL | packed state confirmed (see `[[wiki/techniques/T-0020]]` baseline gate) |

## Verification

| Category | Check | Pass condition |
|---|---|---|
| PARSER | every harvested dex via `verify_result.py parser` | magic/size/adler32/sha1 all valid |
| STRUCTURAL | rebuilt zip CRC + `zipalign -c -p 4` | exit 0 |
| CONTENT | real application class present in harvested dex | probe PASS |
| DOWNSTREAM | `apksigner verify --print-certs` | signer printed, no warnings |
| REPRODUCIBILITY | apk sha256 stable across re-runs | matches fingerprint |
| RUNTIME | install + launch + UI tap | stable pid, no `has died` loop |

Only `VERIFIED_SUCCESS` (>= 3 distinct categories, zero FAIL) is recorded as learning.

## Known Failure Conditions

| Condition | Symptom | Workaround |
|---|---|---|
| No root on device | cannot read `/data/data/<pkg>/...` | memory scarfing (T-0010) or run on rooted emulator |
| VMP static RE attempted | hours no progress | pivot to dynamic harvest at Step 5 |
| Stripped `lib/` in rebuild | `UnsatisfiedLinkError` at `<clinit>` | keep original libs |
| Signature changed, anti-tamper | `TAMPER DETECTED` crash loop | patch expected cert hash (T-0012 recipe) + `pm clear` |

## Evidence

| Source | APK / Target | Result |
|---|---|---|
| playbook Case 3 [V] | `myprotectorproject.apk` (`pokemon.dex.guard`, 21.78 MB) | 74 dex harvested + validated; clean rebuild runs (pid stable, UI + navigation) |
| `[[wiki/experiments/EXP-0001]]` [V] | same APK, baseline | VERIFIED_SUCCESS (5 gate categories): shell dex integrity, qihoo loader present, app classes absent |
| `[[wiki/apks/A-000001-pokemon.dex.guard]]` | fingerprint | protections detected: 360 jiagu + libSecShell + VMP markers + custom containers |

**Unpacked output:** `myprotectorproject-unpacked.apk` — 9.58 MB / 74 dex / 16 libs.

## What This Article Does NOT Cover
- Variants where the decryptor key is purely offline (older 360 jiagu builds) — not exercised here
- Frida-based hooks; only adb + rooted harvesting was used
- Patching anti-debug flags generally (only cert anti-tamper T-0012)

## Related
- [[wiki/techniques/apk-unpacking-playbook]] — verbatim commands (Case 3)
- [[wiki/apks/A-000001-pokemon.dex.guard]] — APK fingerprint
- [[wiki/experiments/EXP-0001]] — baseline verification experiment
- [[wiki/success-traces/ST-0001]] — verified baseline trace
- [[wiki/techniques/T-0020]] - packed-APK baseline gate
- [[wiki/techniques/T-0021]] - storage-model detection: PokeGuard writes dex to disk (T-0019 applies), but run this first — Chiko/NeoArk also looks 360-ish and is memory-resident instead
- [[wiki/packers/_index]] - packer index
