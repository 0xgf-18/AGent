---
type: packer
topic: wiki/packers/_index
source: wiki/techniques/apk-unpacking-playbook
tags: [packer, xuandun, xuan-shield, aead, memory-unpack]
complexity: advanced
completeness: complete
last_verified: 2026-09-29
packer_id: xuandun
name: XuanDun (玄盾) v3.3
aliases: ["xuanDun", "玄盾", "XuanDun", "xuan.factory", "XuanDunApp", "libXuanVM", "libvms.so"]
protection_class: packer
indicators: ["application=com.xuan.XuanDunApp", "appComponentFactory=com.xuan.factory.AndroidComponet", "stub classes.dex ~49 KB / 11 classes / ~500 native methods", "assets/xuanDun_wifi (AES-256-GCM container)", "libvms.so + libXuanVM.so + libHardening.so", "payload never written to disk (RAM-only dex map)"]
unpacking_status: unpacked
confidence: 0.85
evidence: []
technique_ids: [T-0001, T-0002, T-0004, T-0005, T-0008, T-0010, T-0013, T-0014]
tools: [TR-0001, TR-0002, TR-0003, TR-0005, TR-0007, TR-0008, TR-0009, TR-0011]
documented_in: wiki/techniques/apk-unpacking-playbook
version: 1
created_timestamp: 2026-09-29T00:00:00
updated_timestamp: 2026-09-29T00:00:00
llm_summary: "XuanDun v3.3 packer: recognized by com.xuan.XuanDunApp/AndroidComponet manifest entries, 49KB stub with ~500 native methods, assets/xuanDun_wifi AES-256-GCM container keyed from the runtime signing cert (offline decrypt fails: UNLOCK_FAIL). Verified unpack = triage -> apktool smali stub mapping (real Application name never in Java) -> capstone native RE for constants -> container format proof -> memory scarfing T-0010 (carve anonymous rw mappings, search dex magic, validate) -> 54 dex / 4240 classes recovered -> rebuild+sign+verify on x86_64 and arm64."
---

# Packer: XuanDun (玄盾) v3.3

## This Article Answers
- "How do I recognize XuanDun on an APK?"
- "How do I unpack XuanDun?"
- "Why does offline decryption fail and what is the fallback?"

## Key Takeaways
- [RECOGNIZE] manifest `application=com.xuan.XuanDunApp` + `appComponentFactory=com.xuan.factory.AndroidComponet`; 49 KB stub, ~500 native methods; `assets/xuanDun_wifi` container; `libvms.so`/`libXuanVM.so`/`libHardening.so`
- [METHOD] offline decrypt **fails** (AEAD key re-derived from the installed signing cert at runtime) -> **memory scarfing (T-0010)** carves the dex from anonymous `rw` mappings -> validate (T-0008) -> rebuild (T-0013/T-0014)
- [STATUS] `unpacked` — 54 dex / 7,865,640 B / 4,240 classes recovered; unpacked APK built, signed, verified on MuMu x86_64 and phone arm64 [V]
- [EVIDENCE] playbook Evidence row [V] (`Test DumpV2.apk`, `com.my.newproject`)

## Identification

| Indicator | Where | How to detect |
|---|---|---|
| `com.xuan.XuanDunApp` / `com.xuan.factory.AndroidComponet` | AndroidManifest.xml | `aapt dump xmltree` |
| Stub 49,392 B, 11 classes, ~500 methods all `native` | classes.dex | `dexdump -d` |
| `assets/xuanDun_wifi` ≈ 7.9 MB | assets/ | entry inventory |
| `[u8 ivLen][iv][u16be digLen][digest][u32be ctLen][ct]` | asset blob | magic/layout parse |
| `instantiateApplication` / `attachBaseContext` declared native | smali | `apktool d` |
| `XuanDunApp.smali:138-154` AES keys | smali | `xuanDun1029Key!2`, fallback `PokGuard1029Key!!` |

## Unpacking Method (verified workflow)

> Full verbatim scripts: [[wiki/techniques/apk-unpacking-playbook]] Phases 1-9.

### Step 1: Triage (T-0001) [V]
**Action:** entry inventory + manifest dump + `dexdump -d classes.dex`
**Expected:** the identification table above; payload found as asset blob -> **prefer offline decryption attempt over dynamic dumping** (decision point)
**Failure Mode:** none

### Step 2: Stub mapping (T-0002/T-0003) [V]
**Action:** `apktool d <apk>` -> read `<clinit>` chain: `AndroidComponet.<clinit>` -> `VMP.classesInit0(4)`; `instantiateApplication` native; real Application name **never appears in Java code**
**Rule [I]:** if `application` is a packer class and the real app class is a string constant inside the stub, that string is your first recovery target

### Step 3: Native RE for constants (T-0004/T-0005) [V]
**Action:** capstone scripts (vrx_dis/xref/range pattern) over `libvms.so`/`libXuanVM.so` — `raw.find(bytes.fromhex(...))`, `raw.find(b"ascii")`, regex `\b[0-9a-f]{64}\b`, then ADRP xref to see if the hit is compared/logged/dead
**Expected:** AES key material, S-box/Rcon tables, expected cert SHA-256 constants
**Failure Mode:** `md.disasm()` stops at first undecodable byte -> use `skipdata=True` and start at a known-good boundary

### Step 4: Offline decrypt attempt (T-0006b) — expected to FAIL [V]
**Layout:** `[u8 ivLen=0x0C][iv ×12][u16be digLen=0x0020][digest ×32][u32be ctLen][ct]`
**Key:** re-derived from the **installed signing certificate at runtime** (`blobKeyFromRuntimeCert`) -> constant-key attacks return `UNLOCK_FAIL (tamper/resign?)`
**Failure Mode:** this is the designed dead end — do not retry constants; proceed to Step 5

### Step 5: Memory scarfing (T-0010) [V] — the working path
**Action:** launch the app, carve **anonymous `rw` mappings** (+ heap) from `/proc/self/maps`, search `dex\n035` magic, apply T-0008 validators
**Tool:** rooted device + python (or Frida-style dump); ~66 non-empty regions / ~275 MB scanned
**Expected:** 54 unique dex, 0 duplicate classes
**Success Indicator:** every carved dex passes file_size + adler32 + sha1
**Failure Mode:** if packer uses `InMemoryDexClassLoader` and nothing is file/mapping-backed, this path yields nothing (ViRex negative control) — see packer family row in triage table

### Step 6: Validate + list (T-0008) [V]
**Action:** `verify_result.py parser` on each dex; `dexdump -d` for class listing
**Expected:** 54 dex, 7,865,640 B, 4,240 classes
**Failure Mode:** wrong-offset parser -> check map_list strides (string_ids stride 4, class_def stride 32)

### Step 7: Rebuild + verify (T-0013/T-0014) [V]
**Action:** rezip (drop packer assets, add recovered dex as classesN.dex), `zipalign -f -p 4`, `apksigner sign`, `zipalign -c -p 4`, install on **both** ABIs (x86_64 emulator + arm64 device), tap-through test
**Success Indicator:** stable pid, UI renders, no FATAL — executed on MuMu x86_64/Android 15 and physical arm64/Android 14

## Decision Points

| Situation | Condition | Action |
|---|---|---|
| `UNLOCK_FAIL (tamper/resign?)` | cert-derived key | skip offline decrypt, go memory scarfing |
| Payload in asset blob, never on disk | RAM-only dex map | T-0010 carve mappings, not files |
| jadx `corrupt zip` | any | fall back to `dexdump`/apktool — never block on jadx |
| ABI mismatch on verify | emulator != device | patch/verify all four ABIs |

## Verification

| Category | Check | Pass condition |
|---|---|---|
| PARSER | all carved dex | magic/size/adler32/sha1 valid |
| STRUCTURAL | rebuilt zip + `zipalign -c -p 4` | exit 0 |
| DOWNSTREAM | `apksigner verify` | signer printed |
| RUNTIME | install + launch + tap on 2 ABIs | stable pid, UI verified |

## Evidence

| Source | APK / Target | Result |
|---|---|---|
| playbook Evidence row [V] | `Test DumpV2.apk` (10,558,831 B), `com.my.newproject` | 54 dex recovered + validated; unpacked APK built/signed/verified on MuMu and phone; report `PROTECTION.md` |

## What This Article Does NOT Cover
- Decompiling the 59 VM bytecode methods back to Dalvik (bodies live in the native interpreter)
- Frida-based hooking — not used
- iOS / non-DEX payloads

## Related
- [[wiki/techniques/apk-unpacking-playbook]] — verbatim scripts (Phases 1-9)
- [[wiki/packers/_index]] — packer index
- [[wiki/packers/virex]] — sibling packer solved with offline decrypt + cert patch
- [[wiki/packers/360-jiagu]] — sibling packer solved with on-device harvest
