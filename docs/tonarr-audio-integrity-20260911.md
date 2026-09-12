# Audio integrity before import

New native acquisitions now receive full audio-stream validation with bounded FFmpeg execution before tagging/publishing. CRC checking rejects damaged FLAC frames even when the decoder would conceal the error. Comparing FLAC STREAMINFO sample count to decoded duration rejects a missing tail at a valid frame boundary. Validation permits local file/pipe protocols only, runs with one decoder thread, and kills timed-out/cancelled child processes.

Corrupt files follow the existing bad-source quarantine/retry path. A missing validator or validation timeout is a local failure, not evidence against a peer. Existing library files and explicit manual import-anyway behavior are preserved.

Finalization no longer marks an album completed when its known expected count exceeds imported tracks. It retains partial/failed status with actual counts.

Validation: 199 tests passed across audio integrity, file import, orchestration, and single-track acquisition. Real generated audio exercises valid decoding, CRC damage, and truncated-tail detection. This prevents new unverified imports; it does not retroactively repair earlier damaged library files.

A live repair then exposed a separate admission bug: any held album quality tier prevented filling missing tracks. Normal album requests now compare expected recording/position coverage against indexed files; a partial album can acquire missing songs without enabling quality upgrades. Explicit edition requests check that edition. Duplicate encodings cannot satisfy missing tracks. A genuinely complete album resolves its request-history entry as completed instead of leaving a permanent pending entry.

The live follow-up exposed a second completeness assumption: fast library tracklists contain only owned tracks. Acquisition and completion now fetch the selected exact catalog edition before checking coverage. The regression explicitly models five local tracks versus a ten-track catalog and verifies a ten-track acquisition target. Request/orchestration regressions: 230 passed.
