---
type: apk-analysis
topic: wiki/apks/_index
source: 2481b4e47617b97f82cd20bec79d07542f2dab1747580bf75299ff0280aee7bb
tags: [apk, fingerprint, 360 jiagu (360加固)]
complexity: advanced
completeness: partial
last_verified: 2026-09-29
tool_versions: [apktool 2.11.1, aapt2 35.0.0, apksigner 35.0.0]
apk_sha256: 2481b4e47617b97f82cd20bec79d07542f2dab1747580bf75299ff0280aee7bb
package_name: pokemon.dex.guard
version_name: 1.5
version_code: 1
min_sdk: 21
target_sdk: 28
architectures: ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"]
protection_detected: ["360 jiagu (360\u52a0\u56fa)", "360 jiagu marker", "Tencent Legu (\u4e50\u56fa)", "VM protection marker", "VMP / custom VM interpreter", "custom container (assets)"]
analysis_id: A-000001
status: in-progress
bypass_status: not-attempted
llm_summary: "pokemon.dex.guard (1.5): 360 jiagu (360加固), 360 jiagu marker, Tencent Legu (乐固), VM protection marker, VMP / custom VM interpreter, custom container (assets) — 1 dex, 16 native libs, cert 68f2c92dc4044973..."
---

# pokemon.dex.guard — APK Analysis

## This Article Answers
- "What protections does pokemon.dex.guard use?"
- "How can this APK be unpacked/analyzed?"
- "What techniques were successful against 360 jiagu (360加固), 360 jiagu marker, Tencent Legu (乐固), VM p?"

## Key Takeaways
- [PROTECTION] 360 jiagu (360加固), 360 jiagu marker, Tencent Legu (乐固), VM protection marker, VMP / custom VM interpreter, custom container (assets)
- [PACKER] ['360 jiagu (360加固)', 'custom container (assets)']
- [OBSERVATION] 1 dex, 16 native libs, zip integrity OK
- [RESULT] fingerprint intake only — analysis in-progress

## APK Fingerprint
| Property | Value |
|---|---|
| SHA256 | `2481b4e47617b97f82cd20bec79d07542f2dab1747580bf75299ff0280aee7bb` |
| Package | `pokemon.dex.guard` |
| Version | 1.5 (code: 1) |
| Min SDK | 21 |
| Target SDK | 28 |
| Architectures | `arm64-v8a, armeabi-v7a, x86, x86_64` |
| File Size | `21.78 MB` |
| DEX Count | 1 |
| Native Libraries | 16 |
| Entry count | 771 |
| Zip integrity | OK |
| Launch activity | `pokemon.dex.guard.MainActivity` |
| Permissions | 7 |
| Signature schemes | v1=True, v2=True, v3=True, v3.1=False, v4=False |
| Cert SHA-256 | `68f2c92dc4044973c8bf6a58cc7a6d11689625f5a863457e77d3c09b7bcd8037` |
| Source APK | `myprotectorproject.apk` (host path runtime-only, never stored) |

## Protection Detection Results
| Protection Type | Detected | Tool | Confidence | Details |
|---|---|---|---|---|
| packer | Yes | entry-name heuristic | High | 6 matching entries, e.g. assets/libjiagu.so |
| custom | Yes | entry-name heuristic | High | 4 matching entries, e.g. assets/lib/armeabi-v7a/libSecShell.so |
| packer | Yes | entry-name heuristic | Med | 3 matching entries, e.g. assets/ProtectV1.zip |
| native-marker | Yes | byte-marker scan | High | vmInterpret in lib/arm64-v8a/libPokemonGuard.so |
| native-marker | Yes | byte-marker scan | Med | gVm in lib/arm64-v8a/libPokemonGuard.so |
| native-marker | Yes | byte-marker scan | High | vmInterpret in lib/arm64-v8a/libSecShell.so |
| native-marker | Yes | byte-marker scan | Med | gVm in lib/arm64-v8a/libSecShell.so |
| native-marker | Yes | byte-marker scan | High | vmInterpret in lib/arm64-v8a/libjiagu.so |
| native-marker | Yes | byte-marker scan | Med | gVm in lib/arm64-v8a/libjiagu.so |
| native-marker | Yes | byte-marker scan | Med | jiagu in lib/arm64-v8a/libjiagu.so |
| native-marker | Yes | byte-marker scan | High | vmInterpret in lib/arm64-v8a/libjiagu_68.so |
| native-marker | Yes | byte-marker scan | Med | gVm in lib/arm64-v8a/libjiagu_68.so |
| native-marker | Yes | byte-marker scan | Med | jiagu in lib/arm64-v8a/libjiagu_68.so |
| native-marker | Yes | byte-marker scan | High | vmInterpret in lib/arm64-v8a/libIts_PokemonZ.so |
| native-marker | Yes | byte-marker scan | Med | gVm in lib/arm64-v8a/libIts_PokemonZ.so |
| native-marker | Yes | byte-marker scan | High | vmInterpret in lib/arm64-v8a/libPokemonZ.so |
| native-marker | Yes | byte-marker scan | Med | gVm in lib/arm64-v8a/libPokemonZ.so |

## Static Analysis Findings
### DEX Analysis
- DEX entries: `classes.dex`
- Class counts / obfuscation: _not yet analyzed (Phase 2 static pass pending)_

### Native Library Analysis
| Library | Architecture | Exports | Suspicious Functions | Protection Signs |
|---|---|---|---|---|
| `lib/arm64-v8a/libPokemonGuard.so` | arm64-v8a | — | — | scan pending |
| `lib/arm64-v8a/libSecShell.so` | arm64-v8a | — | — | scan pending |
| `lib/arm64-v8a/libjiagu.so` | arm64-v8a | — | — | scan pending |
| `lib/arm64-v8a/libjiagu_68.so` | arm64-v8a | — | — | scan pending |
| `lib/armeabi-v7a/libPokemonGuard.so` | armeabi-v7a | — | — | scan pending |
| `lib/armeabi-v7a/libSecShell.so` | armeabi-v7a | — | — | scan pending |
| `lib/armeabi-v7a/libjiagu.so` | armeabi-v7a | — | — | scan pending |
| `lib/armeabi-v7a/libjiagu_68.so` | armeabi-v7a | — | — | scan pending |
| `lib/x86/libPokemonGuard.so` | x86 | — | — | scan pending |
| `lib/x86/libSecShell.so` | x86 | — | — | scan pending |

### Resource Analysis
- Assets: 22 files — `assets/.jgapp, assets/jgapp, assets/libjiagu.so, assets/libjiagu_a64.so, assets/ProtectV1.zip, assets/protected_by_np/ApkControlFlowConfusionMilk_22d2864a03ad4750b3f5ed771e270e1d.txt, assets/ProtectV3.zip, assets/lib/x86/libPokemonGuard.so`
- Suspicious files: ['6 matching entries, e.g. assets/libjiagu.so', '4 matching entries, e.g. assets/lib/armeabi-v7a/libSecShell.so', '3 matching entries, e.g. assets/ProtectV1.zip']

## Dynamic Analysis Observations
### Runtime Behavior (MuMu)
- _not yet run_ (dynamic phase pending)

### Frida/Objection Hooks Attempted
| Hook Target | Result | Notes |
|---|---|---|
| — | — | no hooks yet |

## Experiments Conducted
| Experiment ID | Technique | Tools | Environment | Result | Verification |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Successful Workflow (if any)
> References: [[wiki/techniques/apk-unpacking-playbook]] (intake checklist)

## Failed Attempts
| Attempt | Technique | Failure Reason | Evidence |
|---|---|---|---|
| — | — | — | — |

## Extracted Artifacts
| Artifact ID | Type | Source Experiment | Hash | Location | Verified |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## What This Article Does NOT Cover
- Runtime behavior, dynamic instrumentation, and bypass results — filled in as experiments run
- Verbatim unpacking commands — recorded in experiment records, not here

## Open Questions / Unverified Claims
- Protection detections are heuristics ([AI Synthesis]) until confirmed by a tool-verified experiment `[V]`

## Related
- [[wiki/techniques/apk-unpacking-playbook]] — intake checklist
- [[wiki/packers/_index]] — packers (packer name -> verified unpacking method)
- environment: host-runtime (runtime-only, never stored)
- [[wiki/tool-registry/_index]] — tool registry
