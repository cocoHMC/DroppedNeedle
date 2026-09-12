# Tonarr metadata connection recovery — 2026-09-07

The deployed Dropped Needle service could authenticate users but failed exact-song
requests before a download task existed. Earlier diagnosis described this as a
TLS/network outage. Controlled tests isolated a narrower cause: outbound
application identification.

From the same container, network and destination, the configured Dropped Needle
User-Agent caused HTTP/2 stream resets and HTTP/1.1 disconnects. A diagnostic
identifier succeeded. Adding a missing version alone did not resolve it. The
maintained integration's truthful identifier, including its product/version,
Dropped Needle integration description, operator contact and Tonarr URL, returned
HTTP 200 from both MusicBrainz and ListenBrainz.

## Change

- Add optional `HTTP_USER_AGENT` for a maintained integration to identify itself
  accurately. Reject control characters/header injection and bound its length.
- Preserve the standard upstream identity by default, with a nonempty development
  version even when Docker supplies an empty build argument.
- Keep transient release-group and exact-edition lookup errors retryable instead
  of misreporting them as nonexistent editions. Do not create an acquisition task
  until the exact recording and edition are verified.
- Keep provider rate limits, TLS verification, VPN routing, owner sources, quotas
  and approval rules intact. No other container was recreated.

Production image: `local/droppedneedle:7bfd742`, source
`7bfd742eaf9e7dd822451e95035c696d3f227292`, image digest
`sha256:bcc8ed1b42438244c0fbdb2ba61740c6136fbc787b1c0eb0d9840339ace2c5fb`.
The existing Compose file has a protected rollback beside it. Only Dropped
Needle's image and application-identification environment setting changed.

## Verification

- 780 repository/download/edition/rate-limit tests passed.
- The restarted service is healthy; its metadata-health endpoint reports no
  MusicBrainz or ListenBrainz degradation after the successful request.
- Retrying the original “Make It Right” / BTS request returned success in 8.4 s.
- Durable task `c95b4a0b6b6c4a90aaaae958ef692f6e` retains recording
  `0228077b-505d-4224-a882-d8d044bc8ed5`, edition
  `64160dc9-9841-4301-a0a2-537ec74472de`, and release-track
  `42b30c94-65ea-4211-9447-43e3f870e85f`.
- The task completed: one file imported, zero failures, at
  `2026-09-07T00:44:01.432821Z`. The owner's configured Soulseek fallback
  supplied the recording; no acquisition-source policy changed.
- The imported FLAC is 25,646,191 bytes, stereo 16-bit/44.1 kHz, duration
  226.321020 seconds. `ffprobe` and a full `ffmpeg` decode-to-null both exited
  zero without audio errors. SHA-256:
  `226be34ad830b1609005c83c79227864efb91f9c871083c0bd0ce98e3fa44671`.
- Tonarr's real iOS library found the recording automatically. Native playback
  ran through its natural 3:46 ending; pause/resume and adding/playing the next
  track also worked. Source: `951ff79`.
- Signed Google Store Tonarr 1000011 played the same recording through a public
  HTTPS Navidrome reviewer connection on Android TV API 36, paused/resumed via
  media controls, then automatically advanced to the next track. This proves
  emulator playback, not physical Fire TV certification or later builds.

Sanitized receipts are in `/root/artifacts/tonarr-request-acceptance/`:
`dn-network-recovery-request.json`, `dn-recovered-track-status.json`,
`dn-completed-download-proof.json`, and `dn-android-tv-playback.json`.
iOS observations are in
`/root/artifacts/tonarr-production-apple/dn-native-playback.json`.

Upstream had previously addressed blocked application identification in
[commit a4aa4ad](https://github.com/DroppedNeedle/DroppedNeedle/commit/a4aa4ad48f03319bf5950becf936c9aefec49b76).
This deployment still reproduced header-dependent failures with that identity;
we did not establish the metadata provider's internal blocking rule.
