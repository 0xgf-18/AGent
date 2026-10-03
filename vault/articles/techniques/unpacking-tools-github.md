---
type: analysis-notes
topic: vault/articles/techniques/_index
source: GitHub research 2026-10-03
tags: [unpacking, tools, github, packers, protection, reverse-engineering]
complexity: advanced
completeness: complete
last_verified: 2026-10-03
tool_versions: []
llm_summary: "Comprehensive collection of GitHub tools and repos for APK unpacking, deobfuscation, and protection bypass. Covers CheckPointSW/android_unpacker, strazzere/android-unpacker, SafaSafari/jiagu_unpacker, rewhy/adaptiveunpacker, enovella/fridroid-unpacker, and more. Includes detection methods, unpacking strategies, and tool selection guidance."
---

# APK Unpacking Tools — GitHub Research

## This Article Answers
- "What GitHub tools exist for APK unpacking?"
- "How do I detect and bypass common packers?"
- "What tools should I use for packed APK analysis?"

## Key Takeaways
- [strazzere/android-unpacker](https://github.com/strazzere/android-unpacker) — Native unpacker for Bangcle/APKProtect/LIAPP/Qihoo/Jaigu [V]
- [CheckPointSW/android_unpacker](https://github.com/CheckPointSW/android_unpacker) — Emulator-based unpacking via ADB [V]
- [SafaSafari/jiagu_unpacker](https://github.com/SafaSafari/jiagu_unpacker) — Automated DEX extraction from Jiagu-packed APKs with AES+XOR decryption [V]
- [rewhy/adaptiveunpacker](https://github.com/rewhy/adaptiveunpacker) — Adaptive unpacking with packer signatures [V]
- [enovella/fridroid-unpacker](https://github.com/enovella/fridroid-unpacker) — Defeat Java packers via Frida instrumentation [V]
- [gmh5225/Android-APKiD](https://github.com/gmh5225/Android-APKiD) — PEiD for Android — packer/protector detection [V]
- [ax/apk.sh](https://github.com/ax/apk.sh) — Bash automation for pull/decode/build/patch/sign [V]
- [loerting/dalvikus](https://github.com/loerting/dalvikus) — Modern smali editor with decompiler integration [V]
- [SameerAlSahab/smali_patch](https://github.com/SameerAlSahab/smali_patch) — Context-based smali patching without line matching [V]

## Unpacking Strategy Matrix

| Packer | Detection | Unpacking Method | Tool |
|---|---|---|---|
| 360 Jiagu | `libjiagu.so`, `libjiagu_*.so` | On-device harvest / memory carve | `jiagu_unpacker.py`, `android-unpacker` |
| Bangcle | `libsecexe.so`, `libsecmain.so` | Native unpacker / Frida | `android-unpacker`, `fridroid-unpacker` |
| APKProtect | `libAPKProtect.so` | Native unpacker | `android-unpacker` |
| LIAPP | `libLIAPP.so` | Native unpacker | `android-unpacker` |
| Qihoo | `lib360protect.so` | Native unpacker | `android-unpacker` |
| Jaigu | `libjaigu.so` | Native unpacker | `android-unpacker` |
| DexProtector | `libdexprotector.so` | Frida / memory carve | `fridroid-unpacker` |
| Bangcle (SecNeo) | `libSecNeo.so` | Native unpacker | `android-unpacker` |
| Custom | Varies | Adaptive unpacking | `adaptiveunpacker` |

## Tool Details

### strazzere/android-unpacker (1,179 stars)
- **Method:** Native ptrace-based unpacker
- **Supports:** Bangcle, APKProtect, LIAPP, Qihoo, Jaigu
- **Requirements:** Android NDK, ARM/x86 device
- **Key feature:** No gdb dependency — runs natively on device
- **Usage:** `adb shell ./data/local/tmp/kisskiss com.package.name`

### CheckPointSW/android_unpacker
- **Method:** Emulator-based — launches app, waits for unpack, pulls DEX
- **Requirements:** AOSP build environment, emulator
- **Key feature:** Fully automated — install, launch, pull, uninstall
- **Usage:** `./unpacker.sh <aosp_dir> <apk_path>`

### SafaSafari/jiagu_unpacker (44 stars)
- **Method:** Offline — AES-CBC + XOR decryption
- **Supports:** Jiagu (加固) packer
- **Key features:**
  - Automatic DEX extraction
  - AES & XOR decryption layers
  - ZIP password bypass (fake encryption flags)
  - Multiple DEX support
- **Usage:** `python3 jiagu_unpacker.py -apk packed.apk -out extracted`

### rewhy/adaptiveunpacker
- **Method:** Adaptive — tracks packing behavior, uses signatures
- **Key features:**
  - Packer signatures database
  - DVM (Android 4.4) and ART (Android 6.0) runtime support
  - Sample directory for testing
- **Usage:** Adaptive unpacking with behavior tracking

### enovella/fridroid-unpacker
- **Method:** Frida instrumentation
- **Key feature:** Defeats Java packers via runtime hooking
- **Best for:** Java-level packers (not native)

### gmh5225/Android-APKiD
- **Method:** Static fingerprinting
- **Key feature:** Identifies compilers, packers, obfuscators
- **Usage:** `apkid <apk_file>`

### ax/apk.sh (3,825 stars)
- **Method:** Bash automation
- **Features:**
  - Pull APK from device
  - Decode with apktool
  - Build/rebuild
  - Patch with Frida gadget
  - Sign with apksigner
  - Multi-arch support (arm, arm64, x86, x86_64)
  - Split APK support
- **Usage:** `./apk.sh pull <pkg>`, `./apk.sh decode <apk>`, `./apk.sh build <dir>`

### loerting/dalvikus (271 stars)
- **Method:** GUI smali editor
- **Features:**
  - Open APK and DEX files directly
  - Smali editor with syntax highlighting
  - Multiple decompiler integration
  - Integrated signing
  - ADB runner for deployment
  - Resource browsing
- **Best for:** Manual smali editing and analysis

### SameerAlSahab/smali_patch (4 stars)
- **Method:** Context-based patching
- **Key feature:** No line/hunk matching — uses context
- **Actions:** PATCH, CREATE, REMOVE
- **Usage:** `python3 smali_patch.py <work_dir> <patch_file>`

## Detection Methods

### Static Detection
```bash
# Check for packer libraries
unzip -l <apk> | grep -iE "libjiagu|libsecexe|libsecmain|libAPKProtect|libdexprotector|lib360protect|libjaigu|libSecNeo"

# Check for packer strings
strings <apk> | grep -iE "jiagu|bangcle|apkprotect|dexprotector|qihoo|secneo|liapp"

# Check manifest for packer application class
aapt dump xmltree <apk> AndroidManifest.xml | grep -iE "application.*name"
```

### Dynamic Detection
```bash
# Check loaded libraries at runtime
adb shell cat /proc/<pid>/maps | grep -iE "\.so"

# Check for unpacking activity
adb logcat | grep -iE "unpack|decrypt|dex|load"
```

### APKiD Detection
```bash
# Install APKiD
pip install apkid

# Scan APK
apkid <apk_file>
```

## Unpacking Workflow

### Step 1: Detect the Packer
```bash
# Use APKiD
apkid <apk_file>

# Or manual detection
unzip -l <apk> | grep -iE "libjiagu|libsecexe|libsecmain|libAPKProtect|libdexprotector"
```

### Step 2: Choose Unpacking Method
- **Known packer** → Use specific tool (e.g., `jiagu_unpacker.py` for Jiagu)
- **Unknown packer** → Use adaptive unpacking (`adaptiveunpacker`)
- **Java packer** → Use Frida (`fridroid-unpacker`)
- **Native packer** → Use native unpacker (`android-unpacker`)

### Step 3: Unpack
```bash
# Example: Jiagu
python3 jiagu_unpacker.py -apk packed.apk -out extracted

# Example: Native unpacker
adb shell ./data/local/tmp/kisskiss com.package.name

# Example: Emulator-based
./unpacker.sh <aosp_dir> <apk_path>
```

### Step 4: Validate
```bash
# Verify DEX integrity
python .agent/scripts/verify_result.py parser --dex <dex>

# Verify structure
python .agent/scripts/verify_result.py structural --file <apk> --kind zip
```

## What This Article Does NOT Cover
- Detailed usage of each tool (see respective repos)
- Frida scripting techniques
- Native code analysis
- VM/VMP unpacking

## Open Questions / Unverified Claims
- [U] Whether `jiagu_unpacker.py` works on latest Jiagu versions
- [U] Whether `adaptiveunpacker` supports Android 14+ runtimes
- [U] Whether `fridroid-unpacker` works on non-rooted devices

## Related
- [[vault/articles/techniques/apk-unpacking-playbook]] — Full unpacking playbook
- [[vault/articles/packers/360-jiagu]] — 360 Jiagu method
- [[vault/articles/packers/chiko-neoark]] — Chiko/NeoArk method
- [[vault/articles/packers/virex]] — ViRex method
- [[vault/articles/packers/xuandun]] — XuanDun method
