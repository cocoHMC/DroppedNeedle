import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest
from services.native.audio_validation import AudioValidationError, validate_audio


@pytest.fixture
def flac(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg required for full audio validation")
    path = tmp_path / "original.flac"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anoisesrc=duration=2:sample_rate=44100", str(path)], check=True)
    return path


@pytest.mark.asyncio
async def test_complete_audio_decodes(flac):
    await validate_audio(flac)


@pytest.mark.asyncio
async def test_corrupt_tail_with_readable_metadata_is_rejected(flac):
    from mutagen.flac import FLAC
    data = bytearray(flac.read_bytes())
    data[len(data)//2:len(data)//2+4000] = bytes(4000)
    flac.write_bytes(data)
    assert FLAC(flac).info.length > 0
    with pytest.raises(AudioValidationError) as error:
        await validate_audio(flac)
    assert error.value.corrupt


@pytest.mark.asyncio
async def test_timeout_kills_child_without_calling_source_corrupt(monkeypatch, flac):
    class Process:
        returncode = None
        killed = False
        async def wait(self):
            if self.killed:
                self.returncode = -9
                return -9
            await asyncio.sleep(60)
        async def communicate(self):
            await self.wait()
            return b"", None
        def kill(self): self.killed = True
    process = Process()
    async def spawn(*args, **kwargs): return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(AudioValidationError) as error:
        await validate_audio(flac, timeout=0.01)
    assert not error.value.corrupt
    assert process.killed and process.returncode == -9


@pytest.mark.asyncio
async def test_truncated_tail_at_frame_boundary_is_rejected(flac):
    import json
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "packet=pos",
                             "-of", "json", str(flac)], capture_output=True, check=True)
    last_frame = int(json.loads(result.stdout)["packets"][-1]["pos"])
    flac.write_bytes(flac.read_bytes()[:last_frame])
    with pytest.raises(AudioValidationError) as error:
        await validate_audio(flac)
    assert error.value.corrupt


@pytest.mark.asyncio
async def test_processor_classifies_corruption_as_bad_source(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    from services.native.file_processor import FileProcessor, VerificationFailed, QUARANTINE_REASONS
    async def invalid(_): raise AudioValidationError("damaged", corrupt=True)
    monkeypatch.setattr("services.native.file_processor.validate_audio", invalid)
    with pytest.raises(VerificationFailed) as error:
        await FileProcessor(MagicMock())._verify_audio(tmp_path / "song.flac")
    assert error.value.reason in QUARANTINE_REASONS


@pytest.mark.asyncio
async def test_unavailable_validator_does_not_quarantine_peer(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    from services.native.file_processor import FileProcessor, VerificationFailed, QUARANTINE_REASONS
    async def unavailable(_): raise AudioValidationError("unavailable")
    monkeypatch.setattr("services.native.file_processor.validate_audio", unavailable)
    with pytest.raises(VerificationFailed) as error:
        await FileProcessor(MagicMock())._verify_audio(tmp_path / "song.flac")
    assert error.value.reason not in QUARANTINE_REASONS
