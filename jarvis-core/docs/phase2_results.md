# Phase 2 results: local transcription

Date: 2026-11-07. Verdict: **pass**, with the memory caveat below.

## Build

| Item | Value |
| --- | --- |
| whisper.cpp | v1.9.1 (tag, commit f049fff) |
| Built with | cmake 4.4.4 from the venv (native arm64), not Homebrew's x86_64 cmake |
| Flags | `-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF` |
| Binary | `build/bin/whisper-cli`, Mach-O arm64, statically linked |
| Backends | Metal (Apple M1 GPU), Accelerate BLAS, CPU |
| Core ML | Not built; not needed at current speed |
| Model | `ggml-base.en.bin`, 141 MB, SHA-1 137c40403d78fd54d454da0f9bd998f78703390c |

Static linking matters: the first shared-library build broke when the folder moved, because the binary looked up its libraries by absolute path.

## Input

`workspace/mic_test.wav`: 16 kHz mono int16, 5.0 s, continuous speech from 0.5 s to 4.6 s.

Transcript: "Create a folder in my workspace called Research Jarvis agent."

## Offline runs

Run with `scripts/bench_whisper.sh`, which refuses to start while the network is reachable. Raw output in [phase2_offline.log](phase2_offline.log).

| Run | Wall clock | Peak RSS | Transcript |
| --- | --- | --- | --- |
| 1 | 0.56 s | 263 MB | same |
| 2 | 0.35 s | 341 MB | same |
| 3 | 0.36 s | 341 MB | same |
| 4 | 0.35 s | 341 MB | same |
| 5 | 0.36 s | 341 MB | same |

The very first run after the build took about 14 s, of which 13.3 s was loading the Metal shader library once. macOS caches it after that.

## Verdict

| Metric | Target | Result |
| --- | --- | --- |
| Transcription time | < 5 s for 5 s clip | 0.35 s warm, 0.56 s first run of a batch: pass |
| Accuracy | recognisably the sentence | pass; word-level score not taken |
| Peak memory | pressure stays green | whisper ~341 MB for under 0.5 s; see caveat |
| Repeatability | no drift over 5 runs | identical transcript on every run: pass |
| Offline | runs with network unreachable | pass |

## Memory caveat

Memory pressure on this Mac is yellow before Jarvis runs anything. After a restart, with normal apps open, VS Code alone used about 4.7 GB of 8 GB, one extension host process at 2.1 GB, with Google Cloud Code (416 MB) and Pylance (366 MB) next. Swap sat at about 2.9 GB.

Whisper does not move the needle: free memory was 41% before the offline runs and 37% after, within normal drift. Its ~341 MB is a third of the plan's 1 GB budget for the voice pipeline.

Re-check at Phase 10, when Node, FastAPI and a browser tab join. If pressure goes red then, the fallbacks in order are `tiny.en`, `base.en` quantised to q5_0, and trimming VS Code extensions.
