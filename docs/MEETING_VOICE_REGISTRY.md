# Meeting Voice Registry Lanes

Issue #12502 is tracked through explicit registry ids where the orchestrator can
run a stable harness, plus non-orchestrator rationale for low-level lab probes
that are not a single scored benchmark.

| Requested lane | Registry id or rationale | CI lane | Notes |
| --- | --- | --- | --- |
| `meeting_voice` | `meeting_voice` | smoke | Provider-aware alias for `meeting_transcription_proof`; mock provider builds the no-key mocked-plumbing route, real provider builds `real_product`. Mocked plumbing is not product proof. |
| `meeting_voice_real` | `meeting_voice_real` | manual | Requires a real-product manifest with reviewed media, logs, screenshots, model outputs, and metrics. |
| `meeting_voice_stress` | `meeting_voice_stress` | manual | Real-product manifest focused on music, noise, babble, overlap, far-field, and single-stream multi-speaker stressors. |
| `meeting_voice_av` | `meeting_voice_av` | manual | Real-product manifest focused on video, active-speaker metadata, screenshots, media refs, and transcript/diarization artifacts. |
| `voicebench-quality` | `voicebench_quality` | manual | Registry ids use underscores; package path remains `packages/benchmarks/voicebench-quality`. |
| `voiceagentbench` | `voiceagentbench` | manual | Real audio dataset and STT/model credentials are evidence-gated. |
| `mmau-audio` | `mmau` | manual | Registry id is the benchmark name; package path remains `packages/benchmarks/mmau-audio`. |
| `voice` | non-orchestrator rationale | manual direct | `packages/benchmarks/voice` is a collection of device/acoustic/local scripts, not one scored report with a stable JSON schema. Keep it direct until a single report writer and scorer exist. |
| `voice-emotion` | non-orchestrator rationale | manual direct | `packages/benchmarks/voice-emotion` has its own CLI and ONNX/audio prerequisites. Keep it direct until the registered lane can fail closed on missing models while producing a scored artifact. |

The `meeting_voice*` ids all route through
`packages/benchmarks/meeting-transcription-proof`. The smoke lane may run with
the bundled mocked manifest; the real/stress/AV lanes must be run with
`extra.manifest=<path>` pointing at reviewed evidence. The scorer rejects
`real_product` reports that are missing named evidence files, required metadata
sections, or detailed regression metrics.
