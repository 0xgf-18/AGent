---
type: analysis-notes
topic: vault/articles/packers/_index
source: GitHub research 2026-10-03
tags: [packers, protection, unpacking, detection, bypass, reverse-engineering, comprehensive]
complexity: advanced
completeness: complete
last_verified: 2026-10-03
tool_versions: []
llm_summary: "Comprehensive knowledge base of 40+ Android packers/protectors with detection signatures, unpacking methods, and bypass techniques. Covers Chinese packers (360 Jiagu, Tencent Legu, Bangcle, iJiami, AliProtect, Baidu, NetEase YiDun) and international packers (DexProtector, DexGuard, Arxan, Promon, AppSealing, LIAPP, Virbox, etc.). Includes tool references, detection methods, and unpacking strategies for each packer."
---

# Android Packer Knowledge Base — 40+ Protectors

## This Article Answers
- "What packers/protectors exist for Android?"
- "How do I detect each packer?"
- "How do I unpack/bypass each packer?"
- "What tools work for each packer?"

## Key Takeaways
- **40+ packers** documented with detection + unpacking methods [V]
- **Chinese packers** dominate: 360 Jiagu, Tencent Legu, Bangcle, iJiami, AliProtect, Baidu [V]
- **International packers**: DexProtector, DexGuard, Arxan, Promon, AppSealing, LIAPP [V]
- **Tools**: strazzere/android-unpacker, SafaSafari/jiagu_unpacker, YSaxon/legu_unpacker, Alexjr2/Android_Dump_Dex [V]

---

## Chinese Packers

### 360 Jiagu (360加固)

| Property | Value |
|---|---|
| **Detection** | `libjiagu.so`, `libjiagu_*.so`, `com.stub.StubApp`, `com.qihoo.util.*` |
| **Difficulty** | Hard |
| **Unpacking** | On-device harvest (`no_backup/dex_unpack`), memory carve, offline AES+XOR |
| **Tools** | `SafaSafari/jiagu_unpacker` (offline AES+XOR), `strazzere/android-unpacker` (native) |
| **Method** | T-0016 char-table decode → T-0017 container walk → T-0018 VMP detect → T-0019 on-device harvest |
| **Evidence** | [[vault/articles/packers/360-jiagu]] — 74 dex recovered, 11,378 classes |

### Qihoo 360

| Property | Value |
|---|---|
| **Detection** | `lib360protect.so`, `com.qihoo.util.*` |
| **Difficulty** | Hard |
| **Unpacking** | Same as 360 Jiagu (same vendor) |
| **Tools** | `strazzere/android-unpacker` |

### Tencent Legu (腾讯乐固)

| Property | Value |
|---|---|
| **Detection** | `libshella-<version>.so`, `libshellx-<version>.so`, `orange-super.2019.so` |
| **Difficulty** | Medium |
| **Unpacking** | Static: XTEA decrypt + NRV decompress |
| **Tools** | [YSaxon/legu_unpacker_2023](https://github.com/YSaxon/legu_unpacker_2023) (supports v4.1.0.15-31) |
| **Method** | DEX stored in `assets/0OO00l111l1l` with NOP-ed bytecode; hashmap links class names to offsets; XTEA decrypt with key from `assets/tosversion` |
| **Key insight** | DEX bytecode is NOP-ed; hashmap + encrypted data blocks; NRV compression |
| **Blog** | [Quarkslab analysis](https://blog.quarkslab.com/a-glimpse-into-tencents-legu-packer.html) |

### Tencent Protect / Tencent Security

| Property | Value |
|---|---|
| **Detection** | `libtencent.so`, `com.tencent.StubApp` |
| **Difficulty** | Medium-Hard |
| **Unpacking** | Frida hook ClassLoader, memory dump |
| **Tools** | `frida-dexdump`, `Alexjr2/Android_Dump_Dex` |

### Bangcle (梆梆加固)

| Property | Value |
|---|---|
| **Detection** | `libsecexe.so`, `libsecmain.so`, `com.secneo.apkwrapper` |
| **Difficulty** | Medium |
| **Unpacking** | Native unpacker, Frida hook |
| **Tools** | `strazzere/android-unpacker`, `frida-dexdump` |
| **Method** | Shell DEX ~20KB; real code in `assets/meta-data/manifest.mf` (Base64 encrypted); native unpacker self-packed with aPLib |

### Bangcle SecShell / SecNeo

| Property | Value |
|---|---|
| **Detection** | `libSecShell.so`, `__b_a_n_g_c_l_e__check1234567_` marker |
| **Difficulty** | Hard |
| **Unpacking** | Self-packed native (aPLib compress → XOR decrypt → ELF relocate) |
| **Tools** | `strazzere/android-unpacker`, `strazzere/secneo-gadget` |
| **Key insight** | Native lib is self-packed: aPLib decompression → XOR decryption → ELF relocation → Bangcle anti-tamper check |

### iJiami (爱加密)

| Property | Value |
|---|---|
| **Detection** | `libijiami.so`, `libexec.so`, `libexecmain.so`, `assets/ijiami.dat` |
| **Difficulty** | Easy (legacy), Hard (v4) |
| **Unpacking** | v4: Two-library Dalvik-style bytecode VM, 80-byte chunk key derivation |
| **Tools** | [Krainium/DarkDex](https://github.com/Krainium/DarkDex) (bypasses iJiami 4th gen) |
| **v4 layers** | zlib+PK-ZIP wrap → bytecode VM cipher → MD5 integrity → OLLVM → stack-probe loop |
| **Key insight** | v4 uses custom bytecode VM; decoy exports; OLLVM control-flow flattening |

### Alibaba / AliProtect

| Property | Value |
|---|---|
| **Detection** | `libsgmain.so`, `libsgsecuritybody.so`, `libmobisec.so` |
| **Difficulty** | Medium-Hard |
| **Unpacking** | Frida hook, memory dump |
| **Tools** | `frida-dexdump`, `Alexjr2/Android_Dump_Dex` |

### Baidu Protect

| Property | Value |
|---|---|
| **Detection** | `libbaiduprotect.so`, `libbdt.so` |
| **Difficulty** | Medium |
| **Unpacking** | Memory dumping (dd from /proc/<pid>/mem) |
| **Tools** | Manual: `dd if=/proc/<pid>/mem of=dump.bin` |
| **Method** | Packers modify DEX in memory; dump memory regions; find DEX magic; extract |
| **Blog** | [Trustlook memory dumping](https://blog.trustlook.com/how-to-unpack-baidu-protect-through-memory-dumping) |

### NetEase YiDun (网易易盾)

| Property | Value |
|---|---|
| **Detection** | `libnetease.so`, `libyidun.so` |
| **Difficulty** | Medium |
| **Unpacking** | Frida hook, memory dump |
| **Tools** | `frida-dexdump` |

### PangXie (盘古)

| Property | Value |
|---|---|
| **Detection** | `libpangxie.so` |
| **Difficulty** | Medium |
| **Unpacking** | Frida hook, memory dump |

---

## International Packers

### APKProtect

| Property | Value |
|---|---|
| **Detection** | `libAPKProtect.so` |
| **Difficulty** | Medium |
| **Unpacking** | Native unpacker (ptrace-based) |
| **Tools** | `strazzere/android-unpacker` |
| **Anti-analysis** | QEMU/debugger detection, port scanning |

### DexProtector

| Property | Value |
|---|---|
| **Detection** | `libdexprotector.so`, `dexprotector` strings |
| **Difficulty** | Medium-Hard |
| **Unpacking** | Frida hook, memory dump |
| **Tools** | `Alexjr2/Android_Dump_Dex` (detects + dumps), `frida-dexdump` |
| **Key insight** | Anti-VM checks (Build.BOARD, Build.MANUFACTURER); white-box crypto |
| **Blog** | [romainthomas/dexprotector](https://github.com/romainthomas/dexprotector) |

### DexGuard

| Property | Value |
|---|---|
| **Detection** | `libdexguard.so`, `dexguard` strings |
| **Difficulty** | Medium-Hard |
| **Unpacking** | Frida hook, memory dump |
| **Tools** | `frida-dexdump` |
| **Key insight** | Class-level encryption, string encryption, anti-tamper |

### Arxan

| Property | Value |
|---|---|
| **Detection** | `libAppProtection.so`, `libarxan.so` |
| **Difficulty** | Hard |
| **Unpacking** | Frida hook, memory dump |
| **Tools** | `frida-dexdump` |
| **Key insight** | Multi-layer protection, integrity checks |

### Promon SHIELD

| Property | Value |
|---|---|
| **Detection** | `libpromon.so` |
| **Difficulty** | Medium (bypass) |
| **Unpacking** | Frida hook, memory dump |
| **Tools** | `frida-dexdump` |
| **Blog** | [KiFilterFiberContext/promon-reversal](https://github.com/KiFilterFiberContext/promon-reversal) |

### AppSealing

| Property | Value |
|---|---|
| **Detection** | `libappsealing.so` |
| **Difficulty** | Low-Medium |
| **Unpacking** | Memory dump + replace DEX in APK |
| **Tools** | [xiamojes/apprec](https://github.com/xiamojes/apprec) (reversal + bypass) |
| **Method** | Dump DEX from memory, replace in APK |

### LIAPP

| Property | Value |
|---|---|
| **Detection** | `libLIAPP.so`, `libil2cpp.so` encryption |
| **Difficulty** | Hard |
| **Unpacking** | No comprehensive public bypass; partial methods only |
| **Tools** | `frida-dexdump` (partial) |
| **Key insight** | Hybrid packer+RASP; encrypts native .so files; IL2CPP metadata protection |

### Virbox

| Property | Value |
|---|---|
| **Detection** | `libvirbox.so`, `libstark.so` |
| **Difficulty** | Medium-Hard |
| **Unpacking** | Position-dependent XOR cipher decrypt |
| **Tools** | [zboralski/virbox-unpack-sens](https://github.com/zboralski/virbox-unpack-sens) |
| **Key insight** | Encrypts APK payloads with position-dependent XOR; blob in assets folder |

### DPT Shell

| Property | Value |
|---|---|
| **Detection** | `libdpt.so`, `assets/OoooooOooo` |
| **Difficulty** | Medium |
| **Unpacking** | AES decrypt (key `DPT_UNKNOWN_DATA` in lib) |
| **Tools** | Manual: extract `assets/OoooooOooo`, decrypt with AES |
| **Key insight** | Lifts method instruction bytes to assets; overwrites with garbage; native loader patches back at runtime |

### Ducex

| Property | Value |
|---|---|
| **Detection** | `libducex.so` |
| **Difficulty** | Medium |
| **Unpacking** | Frida hook, memory dump |

---

## Emerging / Niche Packers

| Packer | Detection | Difficulty | Notes |
|---|---|---|---|
| Naga | `libnaga.so` | Medium | Frida dump |
| Kiwisec | `libkiwisec.so` | Medium | Frida dump |
| AppGuard | `libappguard.so` | Medium | Frida dump |
| DxShield | `libdxshield.so` | Medium | Frida dump |
| NQ Shield | `libnqshield.so` | Medium | Frida dump |
| AppIron | `libappiron.so` | Medium | Frida dump |
| Ahope AppShield | `libahope.so` | Medium | Frida dump |
| Eversafe | `libeversafe.so` | Medium | Frida dump |
| AppCamo | `libappcamo.so` | Medium | Frida dump |
| Verimatrix / InsideSecure | `libverimatrix.so` | Hard | Frida dump |
| Zimperium zShield | `libzshield.so` | Hard | Frida dump |
| Appdome | `libappdome.so` | Hard | Frida dump |
| Approov | `libapproov.so` | Hard | Frida dump |
| Medusah / AppSolid | `libmedusah.so` | Medium | Frida dump |
| Kony | `libkony.so` | Medium | Frida dump |
| Kiro | `libkiro.so` | Medium | Frida dump |
| ApkPacker | `libapkpacker.so` | Easy | Frida dump |
| ApkGuard | `libapkguard.so` | Easy | Frida dump |
| CryptoShell | `libcryptoshell.so` | Medium | Frida dump |
| Secenh | `libsecenh.so` | Medium | Frida dump |
| ApkEncryptor | `libapkencryptor.so` | Easy | Frida dump |
| Epic VM | `libepicvm.so` | Hard | VM-based protection |
| UPX | `libupx.so` | Easy | Standard UPX unpacking |

---

## Universal Unpacking Methods

### Method 1: Frida Memory Dump (Works for most packers)
```bash
# Install frida-server on device
adb push frida-server /data/local/tmp/
adb shell chmod 755 /data/local/tmp/frida-server
adb shell /data/local/tmp/frida-server &

# Dump DEX from memory
frida-dexdump -U -f <package> --all
```

### Method 2: ClassLoader Hook
```javascript
// Hook DexClassLoader to intercept DEX loading
Java.perform(function() {
    var DexClassLoader = Java.use("dalvik.system.DexClassLoader");
    DexClassLoader.$init.implementation = function(dexPath, optDir, libPath, parent) {
        console.log("[*] DEX loaded: " + dexPath);
        // Dump DEX bytes here
        this.$init(dexPath, optDir, libPath, parent);
    };
});
```

### Method 3: Memory Carve (Root required)
```bash
# Find DEX regions in memory
adb shell cat /proc/<pid>/maps | grep "dalvik-DEX"

# Dump each region
adb shell dd if=/proc/<pid>/mem of=/data/local/tmp/dump.bin bs=4096 iflag=skip_bytes,count_bytes skip=<addr> count=<size>
adb pull /data/local/tmp/dump.bin

# Carve DEX from dump
python -c "
data = open('dump.bin', 'rb').read()
pos = 0
while True:
    i = data.find(b'dex\n', pos)
    if i < 0: break
    # Validate and extract DEX
    pos = i + 1
"
```

### Method 4: On-Device Harvest (For disk-writing packers)
```bash
# Launch app, wait for unpack
adb shell am start -n <package>/.MainActivity
sleep 12

# Find unpacked DEX on disk
adb shell find /data/data/<package> -name "*.dex"

# Pull
adb pull /data/data/<package>/no_backup/dex_unpack/
```

---

## Tool Reference

| Tool | URL | Purpose |
|---|---|---|
| strazzere/android-unpacker | [GitHub](https://github.com/strazzere/android-unpacker) | Native unpacker (Bangcle/APKProtect/LIAPP/Qihoo/Jaigu) |
| SafaSafari/jiagu_unpacker | [GitHub](https://github.com/SafaSafari/jiagu_unpacker) | Offline Jiagu AES+XOR decrypt |
| YSaxon/legu_unpacker_2023 | [GitHub](https://github.com/YSaxon/legu_unpacker_2023) | Tencent Legu static unpacker |
| Alexjr2/Android_Dump_Dex | [GitHub](https://github.com/Alexjr2/Android_Dump_Dex) | Frida DEX dump (DexProtector/Jiagu360/AppGuard/Secneo/Bangcle) |
| Krainium/DarkDex | [GitHub](https://github.com/Krainium/DarkDex) | iJiami 4th gen bypass |
| zboralski/virbox-unpack-sens | [GitHub](https://github.com/zboralski/virbox-unpack-sens) | Virbox XOR decrypt |
| xiamojes/apprec | [GitHub](https://github.com/xiamojes/apprec) | AppSealing reversal |
| enovella/fridroid-unpacker | [GitHub](https://github.com/enovella/fridroid-unpacker) | Java packer Frida bypass |
| gmh5225/Android-APKiD | [GitHub](https://github.com/gmh5225/Android-APKiD) | Packer/protector detection |
| romainthomas/dexprotector | [GitHub](https://github.com/romainthomas/dexprotector) | DexProtector analysis |
| KiFilterFiberContext/promon-reversal | [GitHub](https://github.com/KiFilterFiberContext/promon-reversal) | Promon SHIELD reversal |
| ARandomPerson7/Appsealing-Reversal | [GitHub](https://github.com/ARandomPerson7/Appsealing-Reversal) | AppSealing research |

---

## What This Article Does NOT Cover
- Detailed step-by-step unpacking for each packer (see respective articles)
- Frida scripting techniques
- Native code analysis
- VM/VMP unpacking details

## Open Questions / Unverified Claims
- [U] Whether tools work on latest packer versions
- [U] Whether LIAPP has a complete public bypass
- [U] Whether Epic VM unpacking is feasible

## Related
- [[vault/articles/techniques/apk-unpacking-playbook]] — Full unpacking playbook
- [[vault/articles/techniques/unpacking-tools-github]] — GitHub tools collection
- [[vault/articles/techniques/detection-techniques]] — Protection detection
- [[vault/articles/techniques/patching-frameworks]] — Patching frameworks
- [[vault/articles/packers/360-jiagu]] — 360 Jiagu method
- [[vault/articles/packers/chiko-neoark]] — Chiko/NeoArk method
- [[vault/articles/packers/virex]] — ViRex method
- [[vault/articles/packers/xuandun]] — XuanDun method
