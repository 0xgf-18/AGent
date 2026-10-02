---
type: analysis-notes
topic: wiki/techniques/_index
source: session-replays: xuanDun Test DumpV2.apk (com.my.newproject) + ViRex o_sign (1).apk (com.signature) + PokeGuard myprotectorproject.apk (pokemon.dex.guard)
tags: [unpacking, apk, native-re, crypto, anti-tamper, dex, vm-protection, pokeguard]
complexity: advanced
completeness: complete
last_verified: 2026-09-29
tool_versions: [apktool 2.11.1, Android build-tools 35.0.0, capstone 5.0.7, Python 3.14, adb (platform-tools), MuMu 6.7.1 (Android 15/API 35, x86_64), physical arm64 (Android 14/API 34)]
llm_summary: "Complete reusable playbook of every technique used to unpack the XuanDun v3.3 and ViRex protectors: packer triage, stub/classloader mapping, capstone-based native RE, offline payload decryption (AES-256-GCM container, AES-128 counter-mode BXDV blob, LCG stream XOR), DEX validation/class listing, logcat-driven runtime analysis, memory-scarfing fallback, signing-cert anti-tamper patching (raw hash + vectorized compare pool), repack/sign, and dual-ABI verification. Apply this checklist to every future APK intake."
---

# APK Unpacking Playbook — All Techniques Used (XuanDun v3.3 + ViRex)

> **Scope of this file:** every technique actually executed — not theory — while unpacking
> the two APKs handed to this agent. Reuse this file as the intake checklist for **any future APK**.

## This Article Answers
- "What exact techniques did the agent use to unpack APKs?"
- "What is the end-to-end order of operations for a packed Android APK?"
- "Which techniques apply when a packer blocks dexdump / jadx / memory dumping?"
- "How was the ViRex signing-cert anti-tamper check bypassed, byte-for-byte?"

## Key Takeaways
- [PROBLEM] Packed APKs hide the real dex (encrypted asset, native loader, VM-protected method bodies) and may kill the process on re-signing.
- [PREREQUISITES] Python 3.14 + capstone 5.0.7 + apktool 2.11.1 + build-tools 35.0.0 + an emulator (MuMu) + `adb`.
- [WORKFLOW] triage → map stub/classloader → native RE for the decryptor → offline decrypt → validate dex → runtime logcat → patch anti-tamper → repack/sign → verify on emulator **and** physical device.
- [VERIFICATION] logcat PASS lines (`strong verify: PASS`, `VM data loaded successfully`), rendered UI screenshot, interaction test, `apksigner verify`, `zipalign -c -p 4`.
- [CONFIDENCE] 0.9 — both APKs unpacked and verified end-to-end on 2 ABIs; VM-protected method bodies still execute through the native VM (not decompiled).

---

## Master Technique Catalog

| ID | Technique | Category | Phase | First proven on |
|---|---|---|---|---|
| T-0001 | APK triage & packer fingerprinting | static-analysis | 1 | both |
| T-0002 | Stub / Application / ClassLoader mapping | unpacking | 2 | both |
| T-0003 | apktool → smali reading of the stub | static-analysis | 2 | XuanDun |
| T-0004 | capstone native RE toolkit (disasm + string xref + ELF parse) | static-analysis | 3 | ViRex |
| T-0005 | Constant/key extraction from native libraries | static-analysis | 3 | both |
| T-0006 | Offline payload decryption — custom container formats | unpacking | 4 | both |
| T-0007 | Stream-cipher (LCG) payload decode | unpacking | 4 | ViRex |
| T-0008 | DEX structural validation & class/method listing | static-analysis | 5 | both |
| T-0009 | Runtime deployment & logcat-driven analysis | dynamic-dump | 6 | both |
| T-0010 | Memory-scarfing fallback (maps/heap carve + dex validate) | dynamic-dump | 6 | XuanDun (success) / ViRex (negative) / **Chiko-NeoArk (success, EXP-0003)** |
| T-0011 | VM / protected-method identification | deobfuscation | 6 | ViRex |
| T-0012 | Signing-cert anti-tamper bypass (raw hash + vector pool) | anti-debug-bypass | 7 | ViRex |
| T-0013 | Repack, align, sign | unpacking | 8 | both |
| T-0014 | Dual-ABI verification loop | static-analysis | 9 | ViRex |
| T-0015 | Host-environment hygiene (PowerShell / tooling pitfalls) | other | 0 | both |
| T-0016 | Native-decoder char-table recovery (`short[]` + XOR key) | deobfuscation | 2 | PokeGuard |
| T-0017 | Custom container reverse (walk header to EOF-exact proof) | unpacking | 4 | PokeGuard |
| T-0018 | VMP detection via exports (`vmInterpret`/`gVm`) → pivot to dynamic | dynamic-dump | 3 | PokeGuard |
| T-0019 | On-device unpack-dir harvesting (`no_backup/dex_unpack`) | dynamic-dump | 6 | PokeGuard / **negative on Chiko-NeoArk (EXP-0003 — writes nothing to disk)** |
| T-0020 | Packed-APK baseline verification gate (shell-dex triage) | static-analysis | 0 | 360-jiagu |
| T-0021 | **Packer storage-model detection → T-0010 or T-0019 router** | dynamic-dump | 6 | Chiko-NeoArk (EXP-0003) |
| T-0022 | **Repeating-key XOR period detection (harmonic comb)** | static-analysis | 7 | Chiko-NeoArk (EXP-0002) |

> **Read T-0021 before attempting any on-device unpack.** T-0010 (memory carve) and T-0019 (disk harvest) are mutually exclusive and each is silent-failing on the other's packers: T-0019 finds *nothing* on Chiko/NeoArk, and T-0010 finds nothing when the payload really is on disk. T-0021 decides between them in ~2 s by diffing the `/data/data/<pkg>` file count across a launch. Full article: [[wiki/techniques/T-0021]]

---

## Phase 0 — Environment (T-0015)

**Host layout is runtime-discovered [V] — absolute paths are never stored:**

```
Python 3.x    (cryptography + capstone preinstalled)
OpenJDK 17
apktool        <repo>/tools/apktool.jar                  (TR-0002)
build-tools    <android-sdk>/build-tools/<ver>/          (aapt, dexdump, zipalign, apksigner; TR-0005..TR-0009)
adb            <android-sdk>/platform-tools/adb.exe      (TR-0001)
emulator       adb connect <host>:<port>                 (root via su when available)
```

Discover per host: `python .kb/scripts/tool_discover.py` — registry articles
carry capability/install info only, no host paths; device state comes from
`env_probe.py --health` (runtime-only).

**Pitfalls that cost time (never repeat) [V]:**
- Long `python -c "..."` breaks PowerShell quoting → write helper `.py` files under a temp dir and run `py -X utf8 <file>`.
- PowerShell has **no heredoc** (`<<`); PowerShell treats git/adb stderr as errors — judge by printed output.
- **Never name a helper `dis.py`** — it shadows stdlib `dis` and capstone import fails.
- `& keytool`, `& java -jar` needed for exe/jar invocation; use `-s <serial>` with adb for multi-device.

---

## Phase 1 — Triage (T-0001)

**Goal:** identify packer, entry points, payload locations in < 5 minutes.

```powershell
# entry inventory + sizes
py -X utf8 -c "import zipfile; z=zipfile.ZipFile(r'<apk>'); [print('%9d %s' % (i.file_size, i.filename)) for i in z.infolist()]"
# manifest (binary XML)
& "$bt\aapt.exe" dump xmltree "<apk>" AndroidManifest.xml
# stub method bodies
& "$bt\dexdump.exe" -d <classes.dex> > out.txt
# strings from native libs
# (python: search b'...' in lib/*.so)
```

**What the fingerprint revealed [V]:**

| Signal | XuanDun v3.3 | ViRex |
|---|---|---|
| Manifest entry points | `appComponentFactory=com.xuan.factory.AndroidComponet`, `application=com.xuan.XuanDunApp` | `application=ViRexVM.Bridge`, `.MainActivity`, `.DebugActivity` |
| Stub dex | `classes.dex` 49,392 B, 11 classes, ~500 methods **native** | `classes.dex` 11,632 B, 1 class `LViRexVM/Bridge;` |
| Payload | `assets/xuanDun_wifi` 7,879,121 B (AES-256-GCM) | `assets/virex.dexb` 249,140 B (`BXDV`) + `assets/ViRexData.bin` 32,585 B (`DVMP`) |
| Native libs | libvms.so 1,010,000 B / libXuanVM.so / libHardening.so | `libViRex.so` ×4 ABIs (arm64 444,696 · arm32 272,028 · x86 484,980 · x86_64 493,856) |
| Packer family | payload never written to disk; RAM-only dex map | InMemoryDexClassLoader + native VM interpreter |

**Decision point:** payload present as asset blob → prefer **offline decryption** over dynamic dumping.

---

## Phase 2 — Stub / Application / ClassLoader mapping (T-0002, T-0003)

**Goal:** learn *who loads the real code and how*, before touching crypto.

**ViRex stub API surface (from `dexdump -d classes.dex`) [V]:**

```
LViRexVM/Bridge;
  REAL_APP_CLASS = "com.signature.SketchApplication"   (const-string in <clinit>)
  <clinit>  : System.loadLibrary("ViRex")   + logs "libViRex loaded"
  bypassHiddenApi()          → VMRuntime.setHiddenApiExemptions("L")
  createDexClassLoader()     → dalvik.system.InMemoryDexClassLoader (API≥26) else file-based DexClassLoader
  extractAndSetLibPath()     → copies lib/<abi>/libViRex.so → <codeCacheDir>/virex_lib/libViRex.so
  patchNativeLibPaths()      → DexPathList.nativeLibraryDirectories / NativeLibraryElement
  installLoadedApkClassLoader() / installRealApplication() / invokeAttach() / readRealAppClass()
  nativeLoadDexes(...)       → NATIVE (Java_ViRexVM_Bridge_nativeLoadDexes) — passes dex buffers to the VM
  attachBaseContext() / onCreate()
strings: "virex.lib.path", "virex_lib", "Context CL set to realLoader",
         "LoadedApk.mClassLoader → realLoader", "API 26: native lib paths patched"
```

**XuanDun stub (apktool → smali) [V]:** `AndroidComponet.<clinit>` → `VMP.classesInit0(4)`; `instantiateApplication(ClassLoader,String)` declared **native**; `XuanDunApp.attachBaseContext/onCreate` **native**; real Application name never in Java code.

**Reusable rule [I]:** if `application` name is a packer class and the real app class is a string constant inside the stub, the real class name is your first recovery target.

---

## Phase 3 — Native RE toolkit (T-0004, T-0005)

**Goal:** find the decryptor and every hardcoded constant without IDA.

**Three scripts (capstone 5.0.7) [V]** (kept in the session workdir, reusable):

```python
# vrx_dis.py — disassemble a named dynsym function with rodata string annotations
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.detail = True
# TEXT_OFF==TEXT_VA, RO_OFF==RO_VA for libViRex.so: text 0xe580 size 0x4ca20, rodata 0x5afa0 size 0x55f9
# dynsym @0x1478 size 0x3cd8, strtab @0x5150  →  {name: (value,size)}

# xref.py — string xref scanner: ADRP page + (ADD|LDR) with imm in same page
if ins.mnemonic == 'adrp': pg = ins.operands[1].imm
va = pg + (imm & 0xfff)            # ADD imm12
va = pg + mem.disp                  # LDR literal

# range.py — dump any VA window: range.py 0x25f00 0x700
```

**x86_64 variant (needed because the device ABI differs from arm64) [V]:**

```python
md = Cs(CS_ARCH_X86, CS_MODE_64); md.skipdata = True
# RIP-relative targets: tgt = ins.address + ins.size + disp
# NOTE: md.disasm() STOPS at first undecodable byte — use skipdata=True,
# and start decoding at a known-good instruction boundary (e.g. after a call),
# otherwise the whole window is garbage.
```

**Constant extraction results [V]:**

| What | Where | Value |
|---|---|---|
| BXDV AES-128 key | `libViRex.so` offset/VA `0x5CEE9` | `7a3f9e1cd46288512b4af105c3196e7d` |
| AES S-box / Rcon | `0x5DB40` / `0x5DC40` | standard tables |
| AES key-expand / enc / dec | `0x2837c` / `0x28428` / `0x28948` | called from `Java_ViRexVM_Bridge_nativeLoadDexes` (`0x1CD18`, xref `0x1d1fc`) |
| Expected signing cert SHA-256 (raw 32 B) | arm64 `0x5D99A` · arm32 `0x38D67` · x86 `0x6792A` · x86_64 `0x68860` | `a40da80a59d170caa950cf15c18c454d47a39b26989d8b640ecd745ba71bf5dc` |
| XuanDun AES keys (Java) | `XuanDunApp.smali:138-154` | `xuanDun1029Key!2`, fallback `PokGuard1029Key!!` (overwritten at runtime by cert-derived key) |

**Search recipe [V]:** `raw.find(bytes.fromhex("<expected>"))`, `raw.find(b"ascii substring")`, plus a regex for `\b[0-9a-f]{64}\b` — then xref the hit to see whether it is compared, logged, or dead.

---

## Phase 4 — Offline payload decryption (T-0006, T-0007)

### T-0006a — ViRex `virex.dexb` (`BXDV`), solved byte-exact [V]

```
Header:  +00 magic 'BXDV' | +04 ver=1 | +08 dexCount=2 | +0C totalSize=249140
         +10..1F 16-byte block key = 282cd5ad a5d380ca 954d58d9 715381ed
         +20 entries[dexCount] × 16B { u32 offset, u32 size, 8B pad }
Payload starts at 0x20 + dexCount*16 (= 0x40)
```

Keystream = **AES-128-ECB encrypt** of `header[0x10:0x18]` (nonce) ‖ `BE_u64(header[0x18:0x20] + blockIndex)`, key from `libViRex.so@0x5CEE9`; XOR per 16-byte block:

```python
from Crypto.Cipher import AES   # or cryptography
key = bytes.fromhex("7a3f9e1cd46288512b4af105c3196e7d")
nonce, ctr0 = blk[0x10:0x18], int.from_bytes(blk[0x18:0x20], "big")
for i in range(0, len(payload), 16):
    ks = AES.new(key, AES.MODE_ECB).encrypt(nonce + (ctr0 + i // 16).to_bytes(8, "big"))
    out[i:i+16] = bytes(a ^ b for a, b in zip(payload[i:i+16], ks))
```

Result: `classes2.dex` 227,684 B · `classes3.dex` 21,392 B — both `dex\n035`, **file_size + adler32 + sha1 all valid**.

### T-0006b — XuanDun asset container (AES-256-GCM) [V]

```
[u8 ivLen=0x0C][u8 iv ×12][u16be digLen=0x0020][u8 digest ×32][u32be ctLen][ct ×ctLen]
```
Key is **re-derived from the installed signing certificate at runtime** (`blobKeyFromRuntimeCert`) → constant-key attacks fail (`UNLOCK_FAIL (tamper/resign?)`). Escape hatch: memory recovery (T-0010).

### T-0007 — ViRex `ViRexData.bin` (LCG stream XOR) [V]

```
state = 0xA4BD76EC
for i in range(4, len(data)):
    state = (state * 0x41C64E6D + 0x3039) & 0xFFFFFFFF
    data[i] ^= (state >> 16) & 0xFF
# header: 'DVMP' | u32 xorKey=0xAB | u32 methods=59 | u32 crc32=0x5AABDDEB
# index @16, 59 × 24 B = 1416 → strings @1432 (35) → 1982 → methods @1982 (185)
#   → 13588 → fields @13588 (24) → 15196 → types @15196 (42) → 16413 → bodies @16413
```
Cross-check every derived offset against the runtime log (`VMInterpreter: String pool at offset 1432` etc.) — log lines are a free oracle.

---

## Phase 5 — DEX validation & listing (T-0008)

**Validate before trusting [V]:** `file_size` field vs real length · `adler32` of `d[12:]` vs `d[8:12]` · `SHA-1` of `d[32:]` vs `d[12:32]`.

**Section map check (catches wrong-offset parsers) [V]:** `map_off = u32(0x34)`; each entry `{u16 type, u32 size, u32 offset}` at `map_off + 4 + i*12`:

```
type 0x0001 string_ids  | 0x0002 type_ids | 0x0003 proto_ids | 0x0004 field_ids
      0x0005 method_ids | 0x0006 class_defs | 0x2001 class_data | 0x1000 map_list
```

**Stride bugs that break naive parsers (both hit in-session) [V]:**

| Item | Correct layout | Wrong (broken script) |
|---|---|---|
| `string_id_item` | **single u32** → `string_data_off`, stride **4** | treated as `{uleb, offset}` stride 8 → `struct.error: unpack_from ... offset 883032` |
| `class_def_item` | **32 bytes** (class_idx, access_flags, superclass_idx, interfaces_off, source_file_idx, annotations_off, class_data_off, static_values_off) | stride 4 → `class_idx=1402 > type_ids_size=532` |

**Listing [V]:** `dexdump -d <dex> > out.txt` then grep `Class descriptor` / `name  :` / `invoke-*`.

**Recovered contents [V]:**
- `classes2.dex` → 420 classes, all bundled libs (`org.apache.http.*`, `org.apache.commons.*`, `androidx`-free Sketchware deps).
- `classes3.dex` → 20 classes = real app: `LViRexVM;`, `com.signature.MainActivity`, `SketchApplication`, `DebugActivity`, `FileUtil`, `SketchwareUtil`, `R$*`.
- XuanDun: 54 dex, 7,865,640 B, 4,240 classes (recovered from memory, T-0010).

---

## Phase 6 — Runtime analysis (T-0009, T-0010, T-0011)

### T-0009 — logcat-driven analysis [V]

```powershell
& $adb -s 127.0.0.1:16416 shell pm clear <pkg>     # flush cached decrypt artifacts
& $adb -s 127.0.0.1:16416 logcat -c
& $adb -s 127.0.0.1:16416 shell am start -n <pkg>/.MainActivity
& $adb -s 127.0.0.1:16416 logcat -d | Select-String "VMSecurity|VMInterpreter|FATAL|has died"
```
ViRex emits an unusually rich oracle: decrypt key, header fields, CRC32 stored vs computed, every pool offset/count, per-method `{hash, offset, len}`.

### T-0010 — memory scarfing (fallback when offline decrypt is blocked) [V]

Used successfully on XuanDun: carve **anonymous `rw` mappings** from `/proc/self/maps` (+ heap), search `dex\n035` magic, then apply the T-0008 validators → 54 unique dex, 0 duplicate classes (66 non-empty regions, ~275 MB scanned).
**Negative control (ViRex) [V]:** heap (`heap.bin`, 192 MB), 96 scudo/bionic regions, `Anonymous-DexFile@*.vdex` → **no dex magic**; wasted effort — abandon this path early when the packer loads dex only via `InMemoryDexClassLoader`.
**Second success (Chiko/NeoArk) [V]:** 4 `[anon:dalvik-DEX data]` regions, one dex each at offset 0, all passing adler32 **and** sha1 → 6,738 class_defs (EXP-0003). See T-0021 below for how to choose this path.

### T-0021 — storage-model detection: pick T-0010 or T-0019 first [V]

> ⚠️ **Corrects the ViRex note above.** "`InMemoryDexClassLoader` ⇒ abandon T-0010" is **wrong as a general rule**. Chiko/NeoArk *also* uses `InMemoryDexClassLoader` — and T-0010 recovered **all four** of its dex from it. The string is not the discriminator. The only reliable discriminator is empirical: **does the process have `[anon:dalvik-DEX data]` regions in `/proc/<pid>/maps`?** ViRex did not; Chiko/NeoArk did.

Decide in ~2 s, before harvesting anything:

```powershell
# 1. baseline the data dir BEFORE launching
& $adb -s $s shell "su -c 'find /data/data/<pkg> -type f | wc -l'"
# 2. launch, wait for attachBaseContext
& $adb -s $s shell am start -n <pkg>/.MainActivity; Start-Sleep 12
# 3. re-count -- IDENTICAL means the loader writes nothing to disk
& $adb -s $s shell "su -c 'find /data/data/<pkg> -type f | wc -l'"
# 4. corroborate: anon DEX regions? sizes?
& $adb -s $s shell "su -c cat /proc/<pid>/maps" | Select-String "dalvik-DEX"
```

| Verdict | Route to | Evidence |
|---|---|---|
| count identical + `InMemoryDexClassLoader` + anon DEX regions present | **T-0010** — `dd` each anon region out of `/proc/<pid>/mem` (`iflag=skip_bytes,count_bytes`), carve, require adler32 **and** sha1 | Chiko/NeoArk: 4 regions → 4 dex, 6,738 classes |
| count **increased**, unpack dir populated | **T-0019** — copy the unpack dir, validate each dex | PokeGuard |
| count identical, **no** anon DEX regions | neither — T-0010 already burned (ViRex). Re-read maps after a longer wait; the payload may load another way | ViRex |

Requires **root** (the shell uid cannot read another uid's `/proc/<pid>/mem`) and the app must actually **run** — regions are per-launch and only exist after `attachBaseContext`. Full article: [[wiki/techniques/T-0021]]


### T-0011 — identifying VM-protected methods [V]

```smali
# signature of a VM stub method body:
invoke-static {vX, vY}, LViRexVM;.nativeInvoke:(I[Ljava/lang/Object;)Ljava/lang/Object;
# runtime confirmation:
VMInterpreter: Executing Lcom/signature/MainActivity;->initialize(Landroid/os/Bundle;)V (0x17A161B9, len=168)
```
`onCreate` was real (`setContentView`, `initialize`, `initializeLogic` calls) while `initialize`/`initializeLogic` were VM stubs — i.e. protection is **per-method**, not per-class.

---

## Phase 7 — Anti-tamper bypass (T-0012) — the step that unblocked ViRex

**Problem [V]:** re-signing changed the cert → native kill:

```
VMSecurity: SigningInfo cert SHA-256: 60be12efe84feabbf3feeff53505d469613c5aa4276f797a2dc137e0e9a2a034
VMSecurity: strong verify: cert hash MISMATCH
VMSecurity: TAMPER DETECTED: strong_signature — terminating
```
Process crash-looped (`Process com.signature (pid N) has died: fg TOP` repeatedly).

**Patch (reproducible recipe) [V]:**

1. Locate the expected cert: `raw.find(bytes.fromhex("a40da80a...bf5dc"))` in **every** ABI's `libViRex.so` (4 hits).
2. Replace with your signer's SHA-256 (`apksigner verify --print-certs` → `60be12ef...`), same length → no size change.
3. **Also patch the vectorized compare pool** — on x86/x86_64 the compiler compares via `pmovzxbd`/`pxor` against a *separate* constant table where each expected byte is zero-extended to a LE u32 (128 bytes total):
   ```python
   POOL = b''.join(bytes([b,0,0,0]) for b in EXPECTED_32)   # found @ x86 0x66E20, x86_64 0x67D50
   data = data.replace(EXPECTED_32, OURS_32).replace(POOL, POOL_OURS)
   ```
   arm64/armeabi-v7a use a byte loop on the raw buffer → raw patch alone suffices there.
4. Understand the branch logic before patching (arm64) [V]:
   ```
   0x26188 add x23, x23, #0x99a        ; x23 = expected bytes @0x5D99A
   0x26190 bl  0x27904                 ; is_all_zero(buf,32) → 1 if empty
   0x261ac..0x261c4 loop: ldrb ours[i], ldrb exp[i], eor/orr → w8
   0x261cc cset w24, eq                ; w24 = (ours == expected)
   ... slot B @0x5DBA is all-zero (unused) ...
   0x26218 orr w8, w24, w26 ; 0x2621c tbz w8,#0 → MISMATCH @0x26530
   ```
5. **Flush the cached copy:** the stub extracts the lib to `<codeCacheDir>/virex_lib/libViRex.so`; after `install -r` the stale file is reused → always `pm clear <pkg>` after patching, then confirm the on-device sha256 matches your patched build (`su -c sha256sum`).

**Success [V]:** `hasSigningCertificate: PASS` → `strong verify: PASS`.

---

## Phase 8 — Repack, align, sign (T-0013)

```python
# rewrite the zip entry-by-entry (drop old META-INF/*.RSA|*.SF|MANIFEST.MF,
# patch lib bytes, append decrypted dex as classes2.dex / classes3.dex)
zin, zout = zipfile.ZipFile(src), zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
```
```powershell
& "$bt\zipalign.exe" -f -p 4 in.apk aligned.apk
& "$bt\apksigner.bat" sign --ks unpacked.jks --ks-key-alias dpt --ks-pass pass:android --key-pass pass:android --out signed.apk aligned.apk
& "$bt\apksigner.bat" verify --print-certs signed.apk
& "$bt\zipalign.exe" -c -p 4 signed.apk
```
**Two build variants used [V]:**
- *Readable build* (what shipped): original zip + decrypted `classes2.dex`/`classes3.dex` added as APK dex entries → jadx/apktool can see all real code; the packer's own loader still runs (parent-first delegation means single class copies), so VM methods keep working.
- *Pure strip* (stub + assets + lib removed): **not viable** while method bodies are VM stubs — `nativeInvoke` would have no VM table → crash at launch. Requires decompiling VM bytecode first.

---

## Phase 9 — Verification loop (T-0014)

| Check | Command / evidence | Pass condition |
|---|---|---|
| Signature | `apksigner verify --print-certs` | prints signer, no warnings |
| Alignment | `zipalign -c -p 4` | exit 0 |
| Manifest | `aapt dump badging` | package/label/sdk unchanged |
| Install | `adb install -r` (uninstall first if signer changed) | `Success` |
| Anti-tamper | `logcat -d \| findstr VMSecurity` | `strong verify: PASS` |
| Payload | `logcat` | `VM data loaded successfully: 59 methods` |
| Process | `adb shell ps -A \| findstr <pkg>` | stable pid, no `has died` loop |
| UI | `adb shell screencap -p` + pull | title/text/button rendered |
| Interaction | `adb input tap <x> <y>` then logcat | VM/native path executes, no FATAL |

Executed on **MuMu x86_64 / Android 15** and **physical arm64 / Android 14** (`SDK_INT=34` line proves the arm64 lib path) [V].

---

## Case 3 — PokeGuard / "VenKiT Guard" (T-0016 … T-0019)

Target `myprotectorproject.apk` (21,780,000 B) → package `pokemon.dex.guard`, label "VenKiT Guard" v1.5.

**Triage fingerprints [V]:**
```
manifest: application=com.stub.StubApp, activities .MainActivity/.AboutActivity/.LoginActivity/.DebugActivity
stub classes.dex 44,668 B = 15 classes: com.qihoo.util.* + com.stub.StubApp  (360-style names, custom packer)
assets/libjiagu.so 17,826,395 B  → NOT an ELF: magic "PokeGuard" (74-dex container)
assets/ProtectV1|V2|V3.zip       → plain PK zips of stage bundles (dex + libs)
lib/<abi>/{libSecShell,libPokemonGuard,libPokemonZ,libjiagu,libjiagu_68,libIts_PokemonZ}.so
```

**T-0016 char-table recovery [V]** — every `const-string` in the stub is a call
`decoder(short[] table, int start, int len, int key)` with the decoder declared `native`.
The table is `fill-array-data v0, :array_0` (5032 shorts). Decode:

```python
plain = ''.join(chr(table[start + i] ^ key) for i in range(length))
# calls (start, len, key) read from smali:  const v42,0x7c1 / const v40,0x10 / const v41,0x6
# -> ASSET_REAL_APP, XOR_KEY, AES_GCM_KEY, BLOB_MAGIC ...
AES_GCM_KEY = "PokGuard1029Key!"   XOR_KEY = "PoZeHello1#$03992030#1"
ASSET_ENCRYPTED_BLOB = "libjiagu.so"   BLOB_MAGIC = "PokeGuard"   TAG = "CrazyPoke"
```
Recipe: `apktool d` → regex `:array_0\s*\.array-data 2\s*(.*?)\.end array-data` → XOR each candidate `(start,len,key)` from the `invoke-static/range` args; a hit is all-ASCII.

**T-0017 container reverse [V]** — `assets/libjiagu.so` layout:

```
magic "PokeGuard" (9B) + 00 00 00 + u8 dexCount = 0x4A (74)
repeat dexCount ×:  u16be nameLen | name | u32be cipherSize | cipher
proof: walker consumed exactly 0x110025B == file size
```
Entry names are **plaintext** (`classes.dex`, `classes2.dex` … `classes74.dex`); only the bodies are encrypted. Repeating-XOR / single-byte-XOR / AES-ECB / AES-GCM-with-obvious-nonce all failed [V].

**T-0018 VMP detection → dynamic pivot [V]:** `.dynsym` of `libSecShell.so` exports
`vmInterpret`, `gVm`, `cacheInitial`, `getCacheClass` (+ `JNI_OnLoad` only, **0 `Java_*` symbols**)
and `.rodata` holds a sorted table of all 78 native method names (`unpackAesGcmBlob`,
`xorDecrypt`, `loadDexFiles`, …) with no pointer/ADRP xrefs → natives are **VM-interpreted**.
Rule: when you see `vmInterpret` + name-table-without-xrefs, stop static RE — go dynamic.

**T-0019 on-device unpack-dir harvest [V]:** the protector writes plaintext dex to disk:

```
adb install -r <apk>; adb shell am start -n pokemon.dex.guard/.MainActivity   # androidx verify warnings = payload alive
adb shell "su -c 'cp -r /data/data/pokemon.dex.guard/no_backup/dex_unpack /sdcard/dex_unpack; chmod -R 777 /sdcard/dex_unpack'"
adb pull /sdcard/dex_unpack       # 74 files, 17,822,544 B
```
Discovery: `su -c 'find /data/data/<pkg> -type f'` right after first launch.

> **Run that same `find` as a pre-check on every packer — it is also the T-0021 discriminator.** On Chiko/NeoArk the identical command returns the *same* file count before and after launch, proving nothing is written to disk; the harvest above would return nothing while four full dex sit in memory. Don't assume a packer writes an unpack dir because a previous one did. See [[wiki/techniques/T-0021]].

**Validation [V]:** all 74 pass `dex\n035` + `file_size` + adler32 + sha1 → 11,378 class defs.
Real app = `pokemon.dex.guard.SketchApplication` / `.MainActivity` (renamed set) alongside the
original `com.my.newproject4.*` set; `Lpokemon/dex/guard/R;` present.

**Rebuild (clean, no packer) [V]:**
1. synthetic zip = original APK minus `assets/libjiagu.so`, `assets/ProtectV*.zip`, `assets/lib/**`, `META-INF/**`, minus old dex, plus the 74 decrypted dex (kept `lib/` — **the real app needs `libIts_PokemonZ.so`**, first build crashed `UnsatisfiedLinkError at zenoCllass.PokeMonZ.<clinit>` without it).
2. `apktool d -f -s` (no-src: dex pass through untouched) → edit `AndroidManifest.xml`
   `android:name="com.stub.StubApp"` → `"pokemon.dex.guard.SketchApplication"` → `apktool b`.
3. `zipalign -f -p 4` → `apksigner sign` (CN=DPT) → verify + `zipalign -c -p 4`.
4. Install (signature differs → uninstall first), launch, tap through, confirm stable pid.

**Result [V]:** `myprotectorproject-unpacked.apk` 9.58 MB / 74 dex / 16 libs, runs on MuMu
x86_64 (pid 4308 stable, UI renders, navigates to All-files-access screen, no FATAL).

## Decision Points

| Situation | Condition | Action |
|---|---|---|
| jadx fails (`corrupt zip`) | any | go straight to `dexdump -d` / apktool smali — never block on jadx |
| Parser `struct.error` | odd offsets | verify strides against `map_list` (§Phase 5) before blaming the APK |
| Dex in asset blob | packer reads blob via native loader | offline decrypt (T-0006/T-0007); skip memory dumping |
| Offline XOR "succeeds" but the recovered dex has none of the app's classes | you recovered the framework blob, not the app | **This is not an unpack.** Chiko/NeoArk's offline key yields one valid 9.3 MB dex containing 0 `com.mducdz.fakeping` classes. Always assert app-package classes are present before claiming success (T-0022 script asserts this and exits 10) |
| Autocorrelation has many near-equal hot lags | period-P key — harmonics at 2P, 3P, 4P… | the tallest peak is **not** the period and the runner-up is nearly as tall. Take the *smallest* lag ≥40% of peak as P, assert all hot lags are multiples of P, and use the max **non**-multiple lag as the noise floor (T-0022) |
| `validate_dex` rejects a good blob with `file_size != len(blob)` | you passed a whole concatenated stream | slice to the blob's own `file_size` before checksumming; trimming cannot fake a pass because adler32+sha1 are then computed over the trimmed bytes |
| No dex in memory dumps | `InMemoryDexClassLoader` packer | abandon T-0010 after one pass (ViRex lesson) — **but first re-check `/proc/<pid>/maps` for `[anon:dalvik-DEX data]`**; the string alone is NOT the discriminator (T-0021, Chiko/NeoArk succeeded with InMemoryDexClassLoader + anon DEX regions) |
| Crash loop after re-sign | `cert hash MISMATCH` / `TAMPER DETECTED` | T-0012 patch **+** `pm clear` + verify on-device lib hash |
| VM'd method bodies | `nativeInvoke` stubs | keep packer runtime (assets + lib + stub) and add real dex; don't strip |
| ABI mismatch | emulator ≠ target device | patch **all four** ABIs; verify on both ABIs |
| `install -r` fails | `UPDATE_INCOMPATIBLE` | uninstall (original APK retained by user) or keep same keystore |
| Native methods have no `Java_*` symbols | exports `vmInterpret`/`gVm` + sorted name table without xrefs | packer is VMP → abandon static RE of decryptor, run app and harvest (T-0019) |
| Dex written on first launch | `find /data/data/<pkg> -type f` shows `*.dex` | pull from `no_backup/dex_unpack` (or similar) instead of dumping memory |
| **Nothing on disk after launch** | `/data/data` file count identical pre/post launch | **memory-resident** — T-0019 is a dead end, go straight to T-0010 anon-DEX carve (T-0021). Chiko/NeoArk: 4 files before, 4 after, 4 dex in memory |
| Clean build crashes `UnsatisfiedLinkError` | real app loads a native lib you stripped | keep `lib/` from the original APK; only drop packer *assets* |
| All strings are native-decoded | `decoder(short[],int,int,int)` native calls in stub smali | T-0016: decode `fill-array-data` table yourself, `plain[i]=table[start+i]^key` |

---

## Evidence

| APK | Package | Protector | Outcome |
|---|---|---|---|
| `Test DumpV2.apk` (10,558,831 B) | `com.my.newproject` | xuanDun (玄盾) v3.3 | 54 dex recovered + validated; unpacked APK built/signed/verified on MuMu and phone; report `PROTECTION.md` |
| `o_sign (1).apk` (2,055,482 B) | `com.signature` | ViRex (VM + `BXDV`/`DVMP`) | `classes2.dex` + `classes3.dex` decrypted & validated; cert anti-tamper patched; `o_sign-unpacked.apk` verified on MuMu x86_64 **and** physical arm64; UI + tap test pass |
| `myprotectorproject.apk` (21,780,000 B) | `pokemon.dex.guard` | PokeGuard (360-style stub + `PokeGuard` container + VMP natives) | 74 dex harvested from `no_backup/dex_unpack`, all valid (11,378 classes); clean rebuild w/ fixed manifest runs on MuMu (stable pid, UI + navigation verified) |
| `crackme.apk` (12,502,995 B) | `com.mducdz.fakeping` | **Chiko/NeoArk** (`b2al.encryp.vip` + `libchikoStub.so`; appended XOR payload, `InMemoryDexClassLoader`) | **T-0021 router** → memory-resident (data dir 4 files before *and* after) → **T-0010** carve of 4 `[anon:dalvik-DEX data]` regions, all passing adler32+sha1, 6,738 classes; primary blob **byte-identical** to the offline T-0006 XOR result (cross-validated); signed rebuild cold-launches in 1455 ms, crash buffer empty. Filename heuristic misidentified it as 360 jiagu (91-byte decoy asset `assets/libjiagu_mips.a`) |

## What This Article Does NOT Cover
- Decompiling the 59 ViRex / XuanDun VM bytecode methods back into readable Dalvik (only stubs are readable; bodies live in the native interpreter).
- Frida-based hooking, SSL-pinning bypass, and RASP bypasses — no Frida used in any of the three sessions.
- iOS, non-DEX payloads (`.so`-only protectors, Unity/IL2CPP).
- Patching anti-debug/anti-root flags generally (only the signing-cert kill switch was patched).

## Open Questions / Unverified Claims
- The exact CRC32 byte-range for `ViRexData.bin` header field `0x5AABDDEB` was not reproduced offline (runtime log claims `stored=computed`; candidates `[4:]`, `[16:]`, whole file all mismatch) [I].
- Whether `ViRexVM.initVM` is ever invoked from Java, or initialization happens entirely inside `nativeLoadDexes` — no Java call site was found [I].
- XuanDun `ASSET_REAL_APP` char-decode did not yield ASCII — real Application class resolved natively only [V, but unexplained].
- The `b'$' + 64-hex` cert-check branch on armeabi-v7a was inferred from arm64 structure, not disassembled [I].

## Related
- [[wiki/techniques/T-0021]] — **start here for any on-device unpack**: decides T-0010 (memory carve) vs T-0019 (disk harvest) via a `/data/data` file-count diff
- [[wiki/techniques/T-0020]] — packed-APK baseline verification gate (run first, host-only, no root)
- [[wiki/techniques/T-0022]] — **repeating-key XOR period detection**: the tallest autocorrelation peak is *not* the key length; take the smallest lag above 40% of the peak and check every other hot lag is a multiple of it (host-only)
- [[wiki/packers/_index]] — packers (packer name -> verified unpacking method)
- [[wiki/packers/360-jiagu]] — 360 jiagu / PokeGuard method (Case 3, T-0019)
- [[wiki/packers/xuandun]] — XuanDun method (T-0010 memory carve)
- [[wiki/packers/virex]] — ViRex method (offline decrypt + cert patch)
- [[wiki/packers/chiko-neoark]] — Chiko/NeoArk method (appended-payload XOR + T-0010 memory carve)
- [[wiki/techniques/_index]] — techniques topic index
- [[wiki/_master-index]] — KB root
- Sources: `PROTECTION.md` (XuanDun writeup, DPT-UNPACKER repo) · session artifacts under `%TEMP%\opencode\virex\`
