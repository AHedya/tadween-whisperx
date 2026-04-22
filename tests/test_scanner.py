from pathlib import Path

import pytest

from tadween_whisperx.config import LocalInputConfig, S3InputConfig
from tadween_whisperx.scanners import SUPPORTED_AUDIO_EXTENSIONS, create_scanner
from tadween_whisperx.scanners.base import ScanResult
from tadween_whisperx.scanners.local import LocalScanner


class TestSupportedAudioExtensions:
    def test_contains_common_formats(self):
        assert ".wav" in SUPPORTED_AUDIO_EXTENSIONS
        assert ".mp3" in SUPPORTED_AUDIO_EXTENSIONS
        assert ".m4a" in SUPPORTED_AUDIO_EXTENSIONS
        assert ".flac" in SUPPORTED_AUDIO_EXTENSIONS
        assert ".opus" in SUPPORTED_AUDIO_EXTENSIONS

    def test_excludes_non_audio(self):
        assert ".txt" not in SUPPORTED_AUDIO_EXTENSIONS
        assert ".pdf" not in SUPPORTED_AUDIO_EXTENSIONS
        assert ".py" not in SUPPORTED_AUDIO_EXTENSIONS

    def test_is_frozenset(self):
        assert isinstance(SUPPORTED_AUDIO_EXTENSIONS, frozenset)


class TestScanResult:
    def test_local_scan_result(self):
        from tadween_whisperx.components.loader.handler import AudioLoaderInput

        task_input = AudioLoaderInput(file_path=Path("/tmp/test.wav"))
        result = ScanResult(
            artifact_id="test.wav",
            file_path="/tmp/test.wav",
            task_input=task_input,
        )
        assert result.artifact_id == "test.wav"
        assert result.file_path == Path("/tmp/test.wav")
        assert isinstance(result.task_input, AudioLoaderInput)

    def test_s3_scan_result(self):
        from tadween_core.handler.defaults.s3_downloader import S3DownloadInput

        task_input = S3DownloadInput(bucket="b", key="audio/test.wav")
        result = ScanResult(
            artifact_id="audio_test.wav",
            file_path="audio/test.wav",
            task_input=task_input,
        )
        assert result.artifact_id == "audio_test.wav"
        assert str(result.file_path) == "audio/test.wav"
        assert isinstance(result.task_input, S3DownloadInput)


class TestCreateScanner:
    def test_local_config_returns_local_scanner(self):
        config = LocalInputConfig(paths=[])
        scanner = create_scanner(config)
        assert isinstance(scanner, LocalScanner)

    def test_s3_config_returns_s3_scanner(self):
        from unittest.mock import patch

        from tadween_whisperx.scanners.s3 import S3Scanner

        config = S3InputConfig(
            bucket="test-bucket",
            prefix="audio/",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
        )
        with patch("tadween_whisperx.scanners.s3.preflight_check"):
            scanner = create_scanner(config)
        assert isinstance(scanner, S3Scanner)

    def test_unknown_type_raises(self):
        config = LocalInputConfig(paths=[])
        config.__dict__["type"] = "ftp"
        with pytest.raises(ValueError, match="Unknown scanner type"):
            create_scanner(config)


class TestLocalScanner:
    def test_scan_single_file(self, tmp_path: Path):
        wav_file = tmp_path / "test.wav"
        wav_file.touch()
        config = LocalInputConfig(paths=[wav_file])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 1
        assert results[0].artifact_id == "test.wav"
        assert results[0].file_path == wav_file
        scanner.close()

    def test_scan_skips_non_audio_file(self, tmp_path: Path):
        txt_file = tmp_path / "notes.txt"
        txt_file.touch()
        config = LocalInputConfig(paths=[txt_file])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 0
        scanner.close()

    def test_scan_directory(self, tmp_path: Path):
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        wav1 = audio_dir / "a.wav"
        wav2 = audio_dir / "b.mp3"
        txt = audio_dir / "readme.txt"
        wav1.touch()
        wav2.touch()
        txt.touch()
        config = LocalInputConfig(paths=[audio_dir])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 2
        names = {r.artifact_id for r in results}
        assert names == {"a.wav", "b.mp3"}
        scanner.close()

    def test_scan_deduplicates_paths(self, tmp_path: Path):
        wav_file = tmp_path / "test.wav"
        wav_file.touch()
        config = LocalInputConfig(paths=[wav_file, wav_file])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 1
        scanner.close()

    def test_scan_preserves_order(self, tmp_path: Path):
        f1 = tmp_path / "a.wav"
        f2 = tmp_path / "b.mp3"
        f1.touch()
        f2.touch()
        config = LocalInputConfig(paths=[f1, f2])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 2
        assert results[0].artifact_id == "a.wav"
        assert results[1].artifact_id == "b.mp3"
        scanner.close()

    def test_scan_empty_paths(self):
        config = LocalInputConfig(paths=[])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 0
        scanner.close()

    def test_scan_nonexistent_path(self):
        config = LocalInputConfig(paths=[Path("/nonexistent/path.wav")])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 0
        scanner.close()

    def test_scan_recursive_directory(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        wav = sub / "deep.wav"
        wav.touch()
        config = LocalInputConfig(paths=[tmp_path])
        scanner = LocalScanner(config)
        results = list(scanner.scan())
        assert len(results) == 1
        assert results[0].artifact_id == "deep.wav"
        scanner.close()
