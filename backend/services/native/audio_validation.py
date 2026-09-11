"""Bounded full-stream validation of newly acquired local audio."""
import asyncio
from pathlib import Path


class AudioValidationError(Exception):
    def __init__(self, message: str, *, corrupt: bool = False):
        super().__init__(message)
        self.corrupt = corrupt


async def validate_audio(path: Path, *, timeout: float = 180) -> None:
    # Only local file/pipe access is needed. A media playlist cannot fetch URLs.
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "crccheck+bitstream+buffer+explode", "-threads", "1",
            "-protocol_whitelist", "file,pipe", "-i", str(path),
            "-map", "0:a:0", "-progress", "pipe:1", "-nostats", "-f", "null", "-",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError as exc:
        raise AudioValidationError("Audio validation is unavailable on this server") from exc
    try:
        try:
            progress, _ = await asyncio.wait_for(process.communicate(), timeout)
        except TimeoutError as exc:
            raise AudioValidationError("Audio validation exceeded its time limit") from exc
        if process.returncode != 0:
            raise AudioValidationError("Audio stream is damaged or cannot be decoded", corrupt=True)
        # FLAC STREAMINFO declares the exact sample count. A clean EOF between
        # frames can hide a truncated tail from the decoder's exit status.
        if path.suffix.lower() == ".flac":
            from mutagen.flac import FLAC
            try:
                info = await asyncio.to_thread(lambda: FLAC(path).info)
                times = [int(line.split(b"=", 1)[1]) for line in progress.splitlines()
                         if line.startswith(b"out_time_us=")]
                if info.total_samples and (not times or
                        abs(times[-1] / 1_000_000 - info.length) > 2 / info.sample_rate):
                    raise AudioValidationError("Audio stream is incomplete", corrupt=True)
            except AudioValidationError:
                raise
            except (OSError, ValueError, TypeError) as exc:
                raise AudioValidationError("Audio stream metadata is invalid", corrupt=True) from exc
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
