---
type: packer
topic: wiki/packers/_index
source: wiki/techniques/apk-unpacking-playbook
tags: [packer, virex, vmp, aes-ecb, cert-tamper]
complexity: advanced
completeness: complete
last_verified: 2026-09-29
packer_id: virex
name: ViRex (VM + BXDV/DVMP containers)
aliases: ["ViRex", "ViRexVM", "libViRex", "BXDV", "DVMP", "virex.dexb", "ViRexData.bin"]
protection_class: packer
indicators: ["application=ViRexVM.Bridge", "stub classes.dex 11,632 B / single class LViRexVM/Bridge;", "assets/virex.dexb (magic BXDV)", "assets/ViRexData.bin (magic DVMP)", "libViRex.so x4 ABIs", "InMemoryDexClassLoader + nativeInvoke VM stubs", "expected cert SHA-256 hardcoded in libViRex.so per ABI"]
unpacking_status: unpacked
confidence: 0.9
evidence: []
technique_ids: [T-0001, T-0002, T-0004, T-0005, T-0006, T-0007, T-0008, T-0009, T-0011, T-0012, T-0013, T-0014]
tools: [TR-0001, TR-0002, TR-0003, TR-0005, TR-0007, TR-0008, TR-0009, TR-0011]
documented_in: wiki/techniques/apk-unpacking-playbook
version: 1
created_timestamp: 2026-09-29T00:00:00
updated_timestamp: 2026-09-29T00:00:00
llm_summary: "ViRex packer: recognized by ViRexVM.Bridge application, 11KB single-class stub, assets/virex.dexb (BXDV) + ViRexData.bin (DVMP), libViRex.so with hardcoded expected cert SHA-256 per ABI. Verified unpack = stub API mapping (dexdump) -> capstone native RE for AES-128 key @0x5CEE9 -> offline decrypt BXDV (AES-ECB keystream over nonce||ctr blocks) + LCG XOR decode DVMP -> cert anti-tamper patch (raw 32B + vectorized pool, pm clear) -> rezip/align/sign -> verify strong_signature PASS. classes2/3.dex validated byte-exact; per-method VM protection (nativeInvoke) means pure strip build is not viable."
---

# Packer: ViRex (VM + BXDV/DVMP containers)

## This Article Answers
- "How do I recognize ViRex on an APK?"
- "How do I unpack ViRex (offline decrypt + cert bypass)?"
- "Why does re-signing crash the app and how do I fix it?"

## Key Takeaways
- [RECOGNIZE] `application=ViRexVM.Bridge`; 11,632 B single-class stub; `assets/virex.dexb` (`BXDV`) + `assets/ViRexData.bin` (`DVMP`); `libViRex.so` ×4 ABIs with hardcoded expected cert hash
- [METHOD] dexdump stub mapping -> capstone RE (AES-128 key in lib) -> **offline decrypt both containers** -> **patch cert anti-tamper in every ABI** (+ vectorized compare pool) -> rezip/align/sign -> verify
- [STATUS] `unpacked` — `classes2.dex` 227,684 B + `classes3.dex` 21,392 B decrypted, byte-exact valid; rebuilt APK verified on MuMu x86_64 AND physical arm64 [V]
- [CAUTION] protection is **per-method** (`nativeInvoke` stubs): a pure-strip build crashes at launch — keep the packer loader and add decrypted dex, or decompile VM bytecode first
- [EVIDENCE] playbook Evidence row [V] (`o_sign (1).apk`, `com.signature`)

## Identification

| Indicator | Where | How to detect |
|---|---|---|
| `application=ViRexVM.Bridge` | AndroidManifest.xml | `aapt dump xmltree` |
| Stub = single class `LViRexVM/Bridge;`, 11,632 B | classes.dex | `dexdump -d` |
| `REAL_APP_CLASS = "com.signature.SketchApplication"` | const-string in `<clinit>` | dexdump strings |
| `assets/virex.dexb` magic `BXDV` | assets/ | magic bytes |
| `assets/ViRexData.bin` magic `DVMP` | assets/ | magic bytes |
| `libViRex.so` (444,696/272,028/484,980/493,856 B) | lib/<abi>/ | entry inventory |
| `Java_ViRexVM_Bridge_nativeLoadDexes` export | libViRex.so | dynsym |

## Unpacking Method (verified workflow)

> Full verbatim scripts: [[wiki/techniques/apk-unpacking-playbook]] Phases 1-9.

### Step 1: Triage + stub API mapping (T-0001/T-0002) [V]
**Action:** `dexdump -d classes.dex` — read the full stub surface: `REAL_APP_CLASS`, `createDexClassLoader()` (`InMemoryDexClassLoader` API>=26), `nativeLoadDexes(...)` NATIVE, `bypassHiddenApi()`, lib-path patching
**Expected:** real Application name recovered as a string constant (first recovery target)
**Failure Mode:** none

### Step 2: Native RE — find the key (T-0004/T-0005) [V]
**Action:** capstone over `libViRex.so` (arm64 first): dynsym xref of `nativeLoadDexes` -> AES key-expand/enc/dec call sites -> constants
**Key found [V]:** AES-128 key `7a3f9e1cd46288512b4af105c3196e7d` @ VA `0x5CEE9`; expected cert SHA-256 @ arm64 `0x5D99A`, arm32 `0x38D67`, x86 `0x6792A`, x86_64 `0x68860`
**Failure Mode:** wrong ABI layout -> also do the x86_64 variant (RIP-relative, `skipdata=True`)

### Step 3: Offline decrypt `virex.dexb` (T-0006a) [V]
**Header:** `+00 'BXDV' | +04 ver=1 | +08 dexCount=2 | +0C totalSize | +10..1F 16B block key | +20 entries[dexCount]×16B {u32 offset, u32 size, 8B pad}` — payload at `0x20 + dexCount*16`
**Keystream:** AES-128-**ECB encrypt** of `header[0x10:0x18] ‖ BE_u64(header[0x18:0x20] + blockIndex)`, XOR per 16-byte block:
```python
key = bytes.fromhex("7a3f9e1cd46288512b4af105c3196e7d")
nonce, ctr0 = blk[0x10:0x18], int.from_bytes(blk[0x18:0x20], "big")
for i in range(0, len(payload), 16):
    ks = AES.new(key, AES.MODE_ECB).encrypt(nonce + (ctr0 + i // 16).to_bytes(8, "big"))
    out[i:i+16] = bytes(a ^ b for a, b in zip(payload[i:i+16], ks))
```
**Expected:** `classes2.dex` 227,684 B + `classes3.dex` 21,392 B, `dex\n035`, file_size + adler32 + sha1 all valid

### Step 4: Decode `ViRexData.bin` (T-0007) [V]
**LCG stream XOR:**
```python
state = 0xA4BD76EC
for i in range(4, len(data)):
    state = (state * 0x41C64E6D + 0x3039) & 0xFFFFFFFF
    data[i] ^= (state >> 16) & 0xFF
# header: 'DVMP' | u32 xorKey=0xAB | u32 methods=59 | u32 crc32
```
**Cross-check:** every derived offset against runtime log lines (`VMInterpreter: String pool at offset 1432`) — logcat is a free oracle (T-0009)

### Step 5: Cert anti-tamper bypass (T-0012) [V] — the step that unblocked it
**Problem:** re-signing -> `strong verify: cert hash MISMATCH` -> `TAMPER DETECTED: strong_signature` -> crash loop
**Recipe:**
1. `raw.find(bytes.fromhex("a40da80a...bf5dc"))` in **every** ABI's `libViRex.so` (4 hits) -> replace with your signer's SHA-256 (same length)
2. also patch the **vectorized compare pool** on x86/x86_64: `POOL = b''.join(bytes([b,0,0,0]) for b in EXPECTED_32)` (found @ x86 `0x66E20`, x86_64 `0x67D50`) — arm64/arm32 use a byte loop, raw patch suffices
3. **`pm clear <pkg>`** after patching — the stub caches the lib in `<codeCacheDir>/virex_lib/` and would reuse the stale copy; confirm on-device sha256 matches your build
**Success:** `hasSigningCertificate: PASS` -> `strong verify: PASS`

### Step 6: Repack + verify (T-0013/T-0014) [V]
**Action:** zip rewrite entry-by-entry (drop old `META-INF/*.RSA|*.SF|MANIFEST.MF`, patch lib bytes, append decrypted dex as `classes2.dex`/`classes3.dex`) -> `zipalign -f -p 4` -> `apksigner sign` -> `verify --print-certs` -> `zipalign -c -p 4`
**Build variants [V]:** *Readable build* (original zip + decrypted dex added; packer loader still runs) = works. *Pure strip* (stub/assets/lib removed) = **not viable** while method bodies are `nativeInvoke` stubs -> crash at launch.
**Runtime verification:** `strong verify: PASS`, `VM data loaded successfully: 59 methods`, stable pid, UI + tap test — executed on MuMu x86_64/Android 15 and physical arm64/Android 14

## Decision Points

| Situation | Condition | Action |
|---|---|---|
| Heap/mapping carving finds no `dex\n035` | `InMemoryDexClassLoader` only | abandon T-0010 early (ViRex negative control) — use offline decrypt |
| Crash loop after re-sign | `TAMPER DETECTED` | Step 5 cert patch + `pm clear` + on-device sha256 check |
| Per-method VM stubs seen | `invoke-static ... nativeInvoke` | keep packer runtime, add decrypted dex; do not strip |
| jadx fails on odd offsets | `struct.error` | verify strides vs map_list (string_ids=4, class_def=32) |

## Verification

| Category | Check | Pass condition |
|---|---|---|
| PARSER | classes2/classes3 | magic/size/adler32/sha1 valid |
| STRUCTURAL | rebuilt zip + zipalign | exit 0 |
| DOWNSTREAM | `apksigner verify --print-certs` | signer printed |
| RUNTIME | logcat | `strong verify: PASS`, `59 methods`, stable pid, UI tap OK |

## Evidence

| Source | APK / Target | Result |
|---|---|---|
| playbook Evidence row [V] | `o_sign (1).apk` (2,055,482 B), `com.signature` | classes2+3 decrypted & validated; cert anti-tamper patched; `o_sign-unpacked.apk` verified on MuMu x86_64 **and** physical arm64; UI + tap test pass |

## What This Article Does NOT Cover
- Decompiling the 59 VM bytecode methods back to readable Dalvik
- Frida-based hooking / SSL-pinning bypass
- Non-DEX payloads (`.so`-only, Unity/IL2CPP)

## Related
- [[wiki/techniques/apk-unpacking-playbook]] — verbatim scripts (Phases 1-9)
- [[wiki/packers/_index]] — packer index
- [[wiki/packers/xuandun]] — sibling packer (memory-carve path)
- [[wiki/packers/360-jiagu]] — sibling packer (on-device harvest path)
