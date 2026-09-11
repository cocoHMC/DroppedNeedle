# Audio integrity before import

New native acquisitions now receive full audio-stream validation with bounded FFmpeg execution before tagging/publishing. CRC checking rejects damaged FLAC frames even when the decoder would conceal the error. Comparing FLAC STREAMINFO sample count to decoded duration rejects a missing tail at a valid frame boundary. Validation permits local file/pipe protocols only, runs with one decoder thread, and kills timed-out/cancelled child processes.

Corrupt files follow the existing bad-source quarantine/retry path. A missing validator or validation timeout is a local failure, not evidence against a peer. Existing library files and explicit manual import-anyway behavior are preserved.

Finalization no longer marks an album completed when its known expected count exceeds imported tracks. It retains partial/failed status with actual counts.

Validation: 199 tests passed across audio integrity, file import, orchestration, and single-track acquisition. Real generated audio exercises valid decoding, CRC damage, and truncated-tail detection. This prevents new unverified imports; it does not retroactively repair earlier damaged library files.
