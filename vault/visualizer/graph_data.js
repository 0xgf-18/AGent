window.GRAPH_DATA = {
  "nodes": [
    {
      "id": "wiki/techniques/detection-techniques",
      "display_id": "wiki/techniques/detection-techniques",
      "title": "APK Protection Detection Techniques",
      "rel_path": "vault/articles/techniques/detection-techniques.md",
      "topic": "techniques",
      "color": "#10b981",
      "type": "analysis-notes",
      "complexity": "advanced",
      "summary": "Comprehensive APK protection detection techniques covering packer identification, obfuscation detection, integrity/anti-tamper mechanism analysis, and native library analysis. Includes static and dynamic detection methods, tool selection guidance, and detection signatures for major packers.",
      "tags": [
        "detection",
        "packers",
        "protectors",
        "obfuscation",
        "fingerprinting",
        "analysis"
      ],
      "content": "\n\n# APK Protection Detection Techniques\n\n## This Article Answers\n- \"How do I detect what packer/protector an APK uses?\"\n- \"What are the common protection signatures?\"\n- \"How do I identify obfuscation and anti-tamper mechanisms?\"\n\n## Key Takeaways\n- **Static detection** \u2014 Entry-name heuristics, string analysis, magic bytes [V]\n- **Dynamic detection** \u2014 Runtime library loading, memory maps, logcat [V]\n- **APKiD** \u2014 PEiD for Android \u2014 comprehensive packer/protector detection [V]\n- **Multiple layers** \u2014 Some APKs use packer + obfuscator + anti-tamper [V]\n\n## Detection Signatures\n\n### Chinese Packers\n\n| Packer | Library | Manifest | Strings |\n|---|---|---|---|\n| 360 Jiagu | `libjiagu.so`, `libjiagu_*.so` | `com.stub.StubApp` | `jiagu`, `qihoo` |\n| Bangcle | `libsecexe.so`, `libsecmain.so` | `com.secneo.apkwrapper` | `secneo`, `bangcle` |\n| ijiami | `libijiami.so` | `com.ijiami.StubApp` | `ijiami` |\n| Qihoo 360 | `lib360protect.so` | `com.qihoo.util.*` | `360protect` |\n| Tencent Legu | `libshella.so`, `libshellx.so` | `com.tencent.StubApp` | `tencent`, `legu` |\n| Ali Protect | `libsgmain.so`, `libsgsecuritybody.so` | `com.ali.mobisecenhance` | `ali`, `sgmain` |\n| Bangcle (SecNeo) | `libSecNeo.so` | `com.secneo.apkwrapper` | `secneo` |\n\n### International Packers\n\n| Packer | Library | Detection |\n|---|---|---|\n| DexProtector | `libdexprotector.so` | `dexprotector`, `DexProtector` |\n| APKProtect | `libAPKProtect.so` | `APKProtect`, `apkprotect` |\n| LIAPP | `libLIAPP.so` | `LIAPP`, `li...",
      "val": 2.2
    },
    {
      "id": "wiki/techniques/patching-frameworks",
      "display_id": "wiki/techniques/patching-frameworks",
      "title": "APK Patching Frameworks \u2014 GitHub Research",
      "rel_path": "vault/articles/techniques/patching-frameworks.md",
      "topic": "techniques",
      "color": "#10b981",
      "type": "analysis-notes",
      "complexity": "advanced",
      "summary": "Comprehensive collection of APK patching frameworks and tools from GitHub. Covers smali patching (SameerAlSahab/smali_patch), native patching, Frida-based patching, apk.sh automation, dalvikus GUI editor, and more. Includes patch planning, DEX patching, native patching, and build/sign pipeline.",
      "tags": [
        "patching",
        "smali",
        "native",
        "elf",
        "frameworks",
        "tools",
        "modification"
      ],
      "content": "\n\n# APK Patching Frameworks \u2014 GitHub Research\n\n## This Article Answers\n- \"What tools exist for patching APKs?\"\n- \"How do I patch DEX/smali code?\"\n- \"How do I patch native libraries?\"\n- \"What is the build and sign pipeline?\"\n\n## Key Takeaways\n- [SameerAlSahab/smali_patch](https://github.com/SameerAlSahab/smali_patch) \u2014 Context-based smali patching [V]\n- [ax/apk.sh](https://github.com/ax/apk.sh) \u2014 Full automation: pull/decode/build/patch/sign [V]\n- [loerting/dalvikus](https://github.com/loerting/dalvikus) \u2014 GUI smali editor with decompiler integration [V]\n- [orhun/ApkServInject](https://github.com/orhun/apkservinject) \u2014 Smali service injection [V]\n- [osm0sis/APK-Patcher](https://github.com/osm0sis/APK-Patcher) \u2014 On-device patching from recovery [V]\n- [enovella/fridroid-unpacker](https://github.com/enovella/fridroid-unpacker) \u2014 Runtime patching via Frida [V]\n\n## Patching Workflow\n\n```\n1. Analyze \u2192 2. Plan \u2192 3. Patch \u2192 4. Rebuild \u2192 5. Sign \u2192 6. Validate\n```\n\n## DEX / Smali Patching\n\n### Method 1: apktool + manual edit\n```bash\n# Decode APK\napktool d -f -s -o decoded <apk>\n\n# Edit smali files\n# ... edit decoded/smali/com/example/MainActivity.smali ...\n\n# Rebuild\napktool b decoded -o modified-unsigned.apk\n\n# Sign\napksigner sign --ks <keystore> --ks-pass pass:<password> modified-unsigned.apk\n```\n\n### Method 2: smali_patch (context-based)\n```bash\n# Apply patch\npython3 smali_patch.py <work_dir> <patch_file>\n\n# Patch file format:\n# FILE com/example/MainActivity.smali\n# PATCH .method pub...",
      "val": 2.2
    },
    {
      "id": "wiki/techniques/unpacking-tools-github",
      "display_id": "wiki/techniques/unpacking-tools-github",
      "title": "APK Unpacking Tools \u2014 GitHub Research",
      "rel_path": "vault/articles/techniques/unpacking-tools-github.md",
      "topic": "techniques",
      "color": "#10b981",
      "type": "analysis-notes",
      "complexity": "advanced",
      "summary": "Comprehensive collection of GitHub tools and repos for APK unpacking, deobfuscation, and protection bypass. Covers CheckPointSW/android_unpacker, strazzere/android-unpacker, SafaSafari/jiagu_unpacker, rewhy/adaptiveunpacker, enovella/fridroid-unpacker, and more. Includes detection methods, unpacking strategies, and tool selection guidance.",
      "tags": [
        "unpacking",
        "tools",
        "github",
        "packers",
        "protection",
        "reverse-engineering"
      ],
      "content": "\n\n# APK Unpacking Tools \u2014 GitHub Research\n\n## This Article Answers\n- \"What GitHub tools exist for APK unpacking?\"\n- \"How do I detect and bypass common packers?\"\n- \"What tools should I use for packed APK analysis?\"\n\n## Key Takeaways\n- [strazzere/android-unpacker](https://github.com/strazzere/android-unpacker) \u2014 Native unpacker for Bangcle/APKProtect/LIAPP/Qihoo/Jaigu [V]\n- [CheckPointSW/android_unpacker](https://github.com/CheckPointSW/android_unpacker) \u2014 Emulator-based unpacking via ADB [V]\n- [SafaSafari/jiagu_unpacker](https://github.com/SafaSafari/jiagu_unpacker) \u2014 Automated DEX extraction from Jiagu-packed APKs with AES+XOR decryption [V]\n- [rewhy/adaptiveunpacker](https://github.com/rewhy/adaptiveunpacker) \u2014 Adaptive unpacking with packer signatures [V]\n- [enovella/fridroid-unpacker](https://github.com/enovella/fridroid-unpacker) \u2014 Defeat Java packers via Frida instrumentation [V]\n- [gmh5225/Android-APKiD](https://github.com/gmh5225/Android-APKiD) \u2014 PEiD for Android \u2014 packer/protector detection [V]\n- [ax/apk.sh](https://github.com/ax/apk.sh) \u2014 Bash automation for pull/decode/build/patch/sign [V]\n- [loerting/dalvikus](https://github.com/loerting/dalvikus) \u2014 Modern smali editor with decompiler integration [V]\n- [SameerAlSahab/smali_patch](https://github.com/SameerAlSahab/smali_patch) \u2014 Context-based smali patching without line matching [V]\n\n## Unpacking Strategy Matrix\n\n| Packer | Detection | Unpacking Method | Tool |\n|---|---|---|---|\n| 360 Jiagu | `libjiagu.so`, `libjiagu...",
      "val": 2.2
    },
    {
      "id": "wiki/techniques/_index",
      "display_id": "wiki/techniques/_index",
      "title": "Techniques \u2014 Index",
      "rel_path": "vault/articles/techniques/_index.md",
      "topic": "techniques",
      "color": "#10b981",
      "type": "concept",
      "complexity": "intermediate",
      "summary": "No summary provided.",
      "tags": [],
      "content": "<!-- generated by index_builder.py -->\n# Techniques \u2014 Index\n\n## Quick Navigation\nLooking for... -> browse `techniques/` articles below.\n\n## Articles\n| Article | Covers (Summary) | Type | Completeness | Last updated |\n|---|---|---|---|---|\n| [[wiki/techniques/detection-techniques]] | Comprehensive APK protection detection techniques covering packer identification, obfuscation detection, integrity/anti-tamper mechanism ana | analysis-notes | complete | 2026-10-03 |\n| [[wiki/techniques/patching-frameworks]] | Comprehensive collection of APK patching frameworks and tools from GitHub. Covers smali patching (SameerAlSahab/smali_patch), native patchin | analysis-notes | complete | 2026-10-03 |\n| [[wiki/techniques/unpacking-tools-github]] | Comprehensive collection of GitHub tools and repos for APK unpacking, deobfuscation, and protection bypass. Covers CheckPointSW/android_unpa | analysis-notes | complete | 2026-10-03 |\n\n**Articles:** 3 | **Last reindexed:** 2026-10-03\n",
      "val": 3.4000000000000004
    }
  ],
  "links": [
    {
      "source": "wiki/techniques/_index",
      "target": "wiki/techniques/detection-techniques"
    },
    {
      "source": "wiki/techniques/_index",
      "target": "wiki/techniques/patching-frameworks"
    },
    {
      "source": "wiki/techniques/_index",
      "target": "wiki/techniques/unpacking-tools-github"
    }
  ]
};