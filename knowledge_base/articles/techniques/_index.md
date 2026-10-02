---
type: index
topic: wiki
source: session-replays
tags: [index, techniques]
complexity: intro
completeness: complete
last_verified: 2026-09-29
tool_versions: [graph_generator.py]
llm_summary: "Topic index for wiki/techniques — Android APK unpacking techniques. T-0001..T-0019 are catalog rows inside the single playbook article; T-0020 and T-0021 are standalone structured technique articles. For any on-device unpack, start with T-0021 (storage-model detection) to choose between T-0010 memory carving and T-0019 disk harvesting."
---

# Techniques — Topic Index

Single canonical article holding the full technique catalog (T-0001 … T-0015).
Every future APK intake should start here.

## Articles

| Article | Type | Summary |
|---|---|---|
| [[wiki/techniques/apk-unpacking-playbook]] | analysis-notes | All techniques used to unpack XuanDun v3.3, ViRex, PokeGuard and Chiko/NeoArk: triage, stub mapping, capstone native RE, offline decryption, DEX validation, logcat analysis, memory scarfing, storage-model routing, cert anti-tamper patch, repack/sign, dual-ABI verification |
| [[wiki/techniques/T-0020]] | technique | Packed-APK baseline verification gate — prove the container is healthy and the plaintext dex is a shell, host-only, no root |
| [[wiki/techniques/T-0021]] | technique | **Packer storage-model detection - decides T-0010 (memory carve) vs T-0019 (disk harvest) in ~2 s via a `/data/data` file-count diff. Start here for any on-device unpack.** |
| [[wiki/techniques/T-0022]] | technique | **Repeating-key XOR period detection - finds the fundamental key length from the harmonic comb, not the tallest autocorrelation peak. Host-only.** |

## Technique catalog (defined in the playbook)

| ID | Technique | Phase |
|---|---|---|
| T-0001 | APK triage & packer fingerprinting | 1 |
| T-0002 | Stub / Application / ClassLoader mapping | 2 |
| T-0003 | apktool → smali reading of the stub | 2 |
| T-0004 | capstone native RE toolkit (disasm + string xref + ELF parse) | 3 |
| T-0005 | Constant/key extraction from native libraries | 3 |
| T-0006 | Offline payload decryption — custom container formats | 4 |
| T-0007 | Stream-cipher (LCG) payload decode | 4 |
| T-0008 | DEX structural validation & class/method listing | 5 |
| T-0009 | Runtime deployment & logcat-driven analysis | 6 |
| T-0010 | Memory-scarfing fallback (maps/heap carve + dex validate) | 6 |
| T-0011 | VM / protected-method identification | 6 |
| T-0012 | Signing-cert anti-tamper bypass (raw hash + vector pool) | 7 |
| T-0013 | Repack, align, sign | 8 |
| T-0014 | Dual-ABI verification loop | 9 |
| T-0015 | Host-environment hygiene (PowerShell / tooling pitfalls) | 0 |
| T-0016 | Native-decoder char-table recovery (`short[]` + XOR key) | 2 |
| T-0017 | Custom container reverse (walk header to EOF-exact proof) | 4 |
| T-0018 | VMP detection via exports (`vmInterpret`/`gVm`) → pivot to dynamic | 3 |
| T-0019 | On-device unpack-dir harvesting (`no_backup/dex_unpack`) | 6 |
| [[wiki/techniques/T-0020]] | Packed-APK baseline verification gate (shell-dex triage) | 1 |
| [[wiki/techniques/T-0021]] | **Packer storage-model detection → routes to T-0010 or T-0019** | 6 |
| [[wiki/techniques/T-0022]] | **Repeating-key XOR period detection via harmonic comb** | 7 |

T-0001..T-0019 are catalog rows inside the playbook article; T-0020+ are
standalone structured technique articles extracted by
`.kb/scripts/record_technique.py` (Phase 4).

> **T-0010 and T-0019 are mutually exclusive and each fails silently on the
> other's packer.** T-0019 finds nothing on memory-resident packers; T-0010
> finds nothing when the payload is genuinely on disk. Run
> [[wiki/techniques/T-0021]] to pick between them before harvesting.

Cases covered: XuanDun v3.3 · ViRex · PokeGuard/"VenKiT Guard" · Chiko/NeoArk.

## Planned topics (empty — to be populated by future articles)
`wiki/binary-format/` · `wiki/dynamic-analysis/` · `wiki/native-analysis/` · `wiki/native-analysis//hooks` · `wiki/native-analysis//jni` · `wiki/native-analysis//nlc` · `wiki/packers/` · `wiki/static-analysis/` · `wiki/vm-packing/`

## Related
- [[wiki/_master-index]] — KB root
- [[wiki/_technique-index]] — cross-topic technique index
