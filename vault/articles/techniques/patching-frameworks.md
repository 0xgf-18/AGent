---
type: analysis-notes
topic: vault/articles/techniques/_index
source: GitHub research 2026-10-03
tags: [patching, smali, native, elf, frameworks, tools, modification]
complexity: advanced
completeness: complete
last_verified: 2026-10-03
tool_versions: []
llm_summary: "Comprehensive collection of APK patching frameworks and tools from GitHub. Covers smali patching (SameerAlSahab/smali_patch), native patching, Frida-based patching, apk.sh automation, dalvikus GUI editor, and more. Includes patch planning, DEX patching, native patching, and build/sign pipeline."
---

# APK Patching Frameworks — GitHub Research

## This Article Answers
- "What tools exist for patching APKs?"
- "How do I patch DEX/smali code?"
- "How do I patch native libraries?"
- "What is the build and sign pipeline?"

## Key Takeaways
- [SameerAlSahab/smali_patch](https://github.com/SameerAlSahab/smali_patch) — Context-based smali patching [V]
- [ax/apk.sh](https://github.com/ax/apk.sh) — Full automation: pull/decode/build/patch/sign [V]
- [loerting/dalvikus](https://github.com/loerting/dalvikus) — GUI smali editor with decompiler integration [V]
- [orhun/ApkServInject](https://github.com/orhun/apkservinject) — Smali service injection [V]
- [osm0sis/APK-Patcher](https://github.com/osm0sis/APK-Patcher) — On-device patching from recovery [V]
- [enovella/fridroid-unpacker](https://github.com/enovella/fridroid-unpacker) — Runtime patching via Frida [V]

## Patching Workflow

```
1. Analyze → 2. Plan → 3. Patch → 4. Rebuild → 5. Sign → 6. Validate
```

## DEX / Smali Patching

### Method 1: apktool + manual edit
```bash
# Decode APK
apktool d -f -s -o decoded <apk>

# Edit smali files
# ... edit decoded/smali/com/example/MainActivity.smali ...

# Rebuild
apktool b decoded -o modified-unsigned.apk

# Sign
apksigner sign --ks <keystore> --ks-pass pass:<password> modified-unsigned.apk
```

### Method 2: smali_patch (context-based)
```bash
# Apply patch
python3 smali_patch.py <work_dir> <patch_file>

# Patch file format:
# FILE com/example/MainActivity.smali
# PATCH .method public onCreate(Landroid/os/Bundle;)V
# .locals 1
# invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
# - const-string v0, "Hello"
# + const-string v0, "Patched"
# END
```

### Method 3: dalvikus (GUI)
```bash
# Open APK directly in dalvikus
# Edit smali with syntax highlighting
# Rebuild and sign from within the app
```

### Method 4: apk.sh (automation)
```bash
# Decode
./apk.sh decode <apk>

# Patch (manual edit in decoded directory)

# Build
./apk.sh build <decoded_dir>

# Sign
./apk.sh patch <apk> -a arm64-v8a
```

## Native Patching

### ARM64 Patching
```python
# Find function offset
# Read instruction at offset
# Modify instruction
# Write back

# Example: NOP a branch
# Original: B.NE loc_crash
# Patched: NOP (0xD503201F)

# Example: Change return value
# Original: MOV W0, #0
# Patched: MOV W0, #1
```

### x86_64 Patching
```python
# RIP-relative addressing
# tgt = ins.address + ins.size + disp

# Example: JNE → JE
# Original: 75 XX (JNE)
# Patched: 74 XX (JE)
```

### Patching Tools
- **capstone** — Disassembler
- **keystone** — Assembler
- **radare2** — Full RE framework
- **Ghidra** — NSA RE framework
- **IDA Pro** — Commercial disassembler

## Frida-Based Runtime Patching

### Hook Java Methods
```javascript
Java.perform(() => {
    const MainActivity = Java.use("com.example.MainActivity");
    MainActivity.onCreate.implementation = function(savedInstanceState) {
        console.log("onCreate called");
        this.onCreate(savedInstanceState);
    };
});
```

### Hook Native Functions
```javascript
Interceptor.attach(Module.findExportByName("libnative.so", "check_integrity"), {
    onEnter: function(args) {
        console.log("check_integrity called");
    },
    onLeave: function(retval) {
        retval.replace(1); // Force return true
    }
});
```

### Bypass Certificate Pinning
```javascript
Java.perform(() => {
    const X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
    const SSLContext = Java.use("javax.net.ssl.SSLContext");
    
    // Create custom trust manager that trusts all
    const TrustAll = Java.registerClass({
        name: "com.example.TrustAll",
        implements: [X509TrustManager],
        methods: {
            checkClientTrusted(chain, authType) {},
            checkServerTrusted(chain, authType) {},
            getAcceptedIssuers() { return []; }
        }
    });
    
    // Set as default
    const trustManagers = [TrustAll.$new()];
    const sslContext = SSLContext.getInstance("TLS");
    sslContext.init(null, trustManagers, null);
    SSLContext.setDefault(sslContext);
});
```

## Build and Sign Pipeline

### Step 1: Rebuild
```bash
apktool b decoded -o modified-unsigned.apk
```

### Step 2: Align
```bash
zipalign -f -p 4 modified-unsigned.apk modified-aligned.apk
```

### Step 3: Sign
```bash
# Debug keystore
apksigner sign --ks ~/.android/debug.keystore \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --v1-signing-enabled true \
    --v2-signing-enabled true \
    --v3-signing-enabled true \
    modified-aligned.apk

# Custom keystore
apksigner sign --ks <keystore> \
    --ks-pass pass:<password> \
    --key-pass pass:<password> \
    --ks-key-alias <alias> \
    modified-aligned.apk
```

### Step 4: Verify
```bash
apksigner verify --print-certs modified-aligned.apk
zipalign -c -p 4 modified-aligned.apk
```

### Step 5: Install and Test
```bash
adb install -r modified-aligned.apk
adb shell am start -n <package>/.MainActivity
adb logcat | grep -iE "FATAL|Exception|Error"
```

## Patch Planning Template

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

## Failure Recovery

| Failure | Cause | Recovery |
|---|---|---|
| Build fails | Smali syntax error | Fix smali, rebuild |
| Install fails | Signature mismatch | Uninstall original first |
| Crash on launch | Wrong patch | Roll back, re-patch |
| DEX verification fails | Corrupted DEX | Re-extract, re-patch |
| Resource not found | Wrong resource ID | Check public.xml |

## What This Article Does NOT Cover
- Detailed Frida scripting
- Advanced native RE
- VM/VMP patching
- Specific packer bypasses

## Open Questions / Unverified Claims
- [U] Whether smali_patch works on all smali dialects
- [U] Whether dalvikus supports all Android versions
- [U] Whether Frida works on all devices

## Related
- [[vault/articles/techniques/apk-unpacking-playbook]] — Full unpacking playbook
- [[vault/articles/techniques/unpacking-tools-github]] — GitHub tools collection
- [[vault/articles/techniques/detection-techniques]] — Protection detection
