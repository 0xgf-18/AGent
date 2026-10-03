---
type: analysis-notes
topic: vault/articles/techniques/_index
source: GitHub research 2026-10-03
tags: [detection, packers, protectors, obfuscation, fingerprinting, analysis]
complexity: advanced
completeness: complete
last_verified: 2026-10-03
tool_versions: []
llm_summary: "Comprehensive APK protection detection techniques covering packer identification, obfuscation detection, integrity/anti-tamper mechanism analysis, and native library analysis. Includes static and dynamic detection methods, tool selection guidance, and detection signatures for major packers."
---

# APK Protection Detection Techniques

## This Article Answers
- "How do I detect what packer/protector an APK uses?"
- "What are the common protection signatures?"
- "How do I identify obfuscation and anti-tamper mechanisms?"

## Key Takeaways
- **Static detection** — Entry-name heuristics, string analysis, magic bytes [V]
- **Dynamic detection** — Runtime library loading, memory maps, logcat [V]
- **APKiD** — PEiD for Android — comprehensive packer/protector detection [V]
- **Multiple layers** — Some APKs use packer + obfuscator + anti-tamper [V]

## Detection Signatures

### Chinese Packers

| Packer | Library | Manifest | Strings |
|---|---|---|---|
| 360 Jiagu | `libjiagu.so`, `libjiagu_*.so` | `com.stub.StubApp` | `jiagu`, `qihoo` |
| Bangcle | `libsecexe.so`, `libsecmain.so` | `com.secneo.apkwrapper` | `secneo`, `bangcle` |
| ijiami | `libijiami.so` | `com.ijiami.StubApp` | `ijiami` |
| Qihoo 360 | `lib360protect.so` | `com.qihoo.util.*` | `360protect` |
| Tencent Legu | `libshella.so`, `libshellx.so` | `com.tencent.StubApp` | `tencent`, `legu` |
| Ali Protect | `libsgmain.so`, `libsgsecuritybody.so` | `com.ali.mobisecenhance` | `ali`, `sgmain` |
| Bangcle (SecNeo) | `libSecNeo.so` | `com.secneo.apkwrapper` | `secneo` |

### International Packers

| Packer | Library | Detection |
|---|---|---|
| DexProtector | `libdexprotector.so` | `dexprotector`, `DexProtector` |
| APKProtect | `libAPKProtect.so` | `APKProtect`, `apkprotect` |
| LIAPP | `libLIAPP.so` | `LIAPP`, `liapp` |
| Arxan | `libarxan.so` | `arxan`, `Arxan` |
| Promon | `libpromon.so` | `promon`, `Promon` |
| DEXGuard | `libdexguard.so` | `dexguard`, `DEXGuard` |

### Obfuscators

| Obfuscator | Detection |
|---|---|
| ProGuard | `proguard`, `ProGuard` |
| R8 | `r8`, `R8` |
| DexGuard | `dexguard`, `DEXGuard` |
| Allatori | `allatori`, `Allatori` |
| DashO | `dasho`, `DashO` |
| Zelix KlassMaster | `zelix`, `KlassMaster` |
| Stringer | `stringer`, `Stringer` |

## Static Detection Methods

### 1. Entry-Name Heuristics
```bash
# List all native libraries
unzip -l <apk> | grep "\.so$"

# Check for packer-specific libraries
unzip -l <apk> | grep -iE "libjiagu|libsecexe|libsecmain|libAPKProtect|libdexprotector|lib360protect|libjaigu|libSecNeo|libijiami|libshella|libshellx|libsgmain|libsgsecuritybody"
```

### 2. String Analysis
```bash
# Extract strings from APK
strings <apk> | grep -iE "jiagu|bangcle|apkprotect|dexprotector|qihoo|secneo|liapp|arxan|promon|dexguard|allatori|dasho|stringer"

# Check native library strings
unzip -p <apk> lib/arm64-v8a/libnative.so | strings | grep -iE "pack|protect|encrypt|decrypt|unpack"
```

### 3. Magic Bytes
```bash
# Check for custom container formats
xxd <apk> | head -20

# Check for encrypted DEX (non-standard magic)
unzip -p <apk> classes.dex | xxd | head -5
# Normal DEX: 64 65 78 0a 30 33 35 00 (dex\n035\0)
# Encrypted: different magic
```

### 4. Manifest Analysis
```bash
# Check application class
aapt dump xmltree <apk> AndroidManifest.xml | grep -A2 "application"

# Check for packer-specific classes
aapt dump xmltree <apk> AndroidManifest.xml | grep -iE "StubApp|SecNeo|ijiami|tencent|qihoo"
```

### 5. DEX Header Analysis
```bash
# Extract and check DEX header
unzip -p <apk> classes.dex > classes.dex
xxd classes.dex | head -10

# Check for shell DEX (small, few classes)
python -c "import struct; d=open('classes.dex','rb').read(); print(f'Size: {len(d)}, class_defs: {struct.unpack_from(\"<I\", d, 0x60)[0]}')"
```

## Dynamic Detection Methods

### 1. Runtime Library Loading
```bash
# Get PID
adb shell pidof <package>

# Check loaded libraries
adb shell cat /proc/<pid>/maps | grep "\.so"

# Look for packer libraries
adb shell cat /proc/<pid>/maps | grep -iE "jiagu|secexe|secmain|APKProtect|dexprotector|360protect|SecNeo|ijiami|shella|shellx|sgmain"
```

### 2. Memory Maps Analysis
```bash
# Check for anonymous DEX regions
adb shell cat /proc/<pid>/maps | grep "dalvik-DEX"

# Check for decrypted code regions
adb shell cat /proc/<pid>/maps | grep -E "rwx|rw-p"
```

### 3. Logcat Monitoring
```bash
# Monitor for unpacking activity
adb logcat | grep -iE "unpack|decrypt|dex|load|protect|jiagu|bangcle|secneo"

# Monitor for class loading
adb logcat | grep -iE "ClassLoader|loadClass|DexClassLoader|InMemoryDexClassLoader"
```

### 4. File System Monitoring
```bash
# Check for unpacked DEX on disk
adb shell find /data/data/<package> -name "*.dex"

# Check for unpack directory
adb shell ls -la /data/data/<package>/no_backup/
adb shell ls -la /data/data/<package>/files/
```

## APKiD — Comprehensive Detection

### Installation
```bash
pip install apkid
```

### Usage
```bash
# Scan APK
apkid <apk_file>

# Scan with JSON output
apkid -j <apk_file>

# Scan directory
apkid -r <directory>
```

### Output Interpretation
```
APKiD Results:
  Packer: 360 Jiagu
  Obfuscator: DexGuard
  Anti-tamper: Arxan
  Compiler: dx
```

## Multi-Layer Protection Detection

Some APKs use multiple protection layers:

```
Layer 1: Packer (e.g., 360 Jiagu)
  ↓
Layer 2: Obfuscator (e.g., DexGuard)
  ↓
Layer 3: Anti-tamper (e.g., Arxan)
  ↓
Layer 4: Native protection (e.g., VMP)
```

### Detection Strategy
1. **Detect outer layer first** (packer)
2. **Unpack outer layer**
3. **Detect inner layer** (obfuscator)
4. **Deobfuscate**
5. **Detect anti-tamper**
6. **Bypass anti-tamper**
7. **Analyze native protection**

## Integrity / Anti-Tamper Detection

### Common Mechanisms

| Mechanism | Detection | Bypass |
|---|---|---|
| APK self-hashing | `MessageDigest`, `SHA-256` | Patch hash comparison |
| Certificate verification | `getPackageInfo`, `GET_SIGNATURES` | Patch signature check |
| Package name check | `getPackageName` | Hook method |
| File integrity | `File.exists`, `File.length` | Hook file methods |
| DEX integrity | `DexFile.loadDex` | Hook DEX loading |
| Native integrity | `dlopen`, `dlsym` | Hook linker |
| Debugger detection | `android.os.Debug.isDebuggerConnected` | Patch return value |
| Root detection | `su`, `Superuser.apk` | Hook file checks |
| Emulator detection | `qemu`, `goldfish`, `ranchu` | Patch property checks |
| Frida detection | `/proc/self/maps` scan | Hide Frida artifacts |
| Xposed detection | `de.robv.android.xposed` | Hook class loading |

### Detection Commands
```bash
# Check for debugger detection
strings <apk> | grep -iE "isDebuggerConnected|android.os.Debug"

# Check for root detection
strings <apk> | grep -iE "su|Superuser|superuser|magisk"

# Check for emulator detection
strings <apk> | grep -iE "qemu|goldfish|ranchu|genymotion|bluestacks"

# Check for Frida detection
strings <apk> | grep -iE "frida|gadget|linjector"

# Check for Xposed detection
strings <apk> | grep -iE "xposed|de.robv.android.xposed"
```

## What This Article Does NOT Cover
- Detailed bypass techniques for each mechanism
- Frida scripting for bypass
- Native code patching
- VM/VMP analysis

## Open Questions / Unverified Claims
- [U] Whether APKiD detects all latest packer versions
- [U] Whether dynamic detection works on all Android versions
- [U] Whether multi-layer detection order is always correct

## Related
- [[vault/articles/techniques/apk-unpacking-playbook]] — Full unpacking playbook
- [[vault/articles/techniques/unpacking-tools-github]] — GitHub tools collection
- [[vault/articles/packers/360-jiagu]] — 360 Jiagu detection
- [[vault/articles/packers/chiko-neoark]] — Chiko/NeoArk detection
