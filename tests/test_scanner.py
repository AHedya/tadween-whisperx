from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tadween_core.handler.defaults.s3_downloader import S3DownloadInput

from tadween_whisperx.components.loader.handler import AudioLoaderInput
from tadween_whisperx.config import HTTPInputConfig, LocalInputConfig, S3InputConfig
from tadween_whisperx.scanners import SUPPORTED_AUDIO_EXTENSIONS, create_scanner
from tadween_whisperx.scanners.base import ScanResult
from tadween_whisperx.scanners.http import HTTPScanner
from tadween_whisperx.scanners.local import LocalScanner
from tadween_whisperx.scanners.s3 import S3Scanner


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

        task_input = AudioLoaderInput(file_path=Path("/tmp/test.wav"))
        result = ScanResult(
            artifact_id="test.wav",
            source="/tmp/test.wav",
            task_input=task_input,
        )
        assert result.artifact_id == "test.wav"
        assert result.source == "/tmp/test.wav"
        assert isinstance(result.task_input, AudioLoaderInput)

    def test_s3_scan_result(self):

        task_input = S3DownloadInput(bucket="b", key="audio/test.wav")
        result = ScanResult(
            artifact_id="audio_test.wav",
            source="audio/test.wav",
            task_input=task_input,
        )
        assert result.artifact_id == "audio_test.wav"
        assert result.source == "audio/test.wav"
        assert isinstance(result.task_input, S3DownloadInput)


class TestCreateScanner:
    def test_local_config_returns_local_scanner(self):
        config = LocalInputConfig(paths=[])
        scanner = create_scanner(config)
        assert isinstance(scanner, LocalScanner)

    def test_s3_config_returns_s3_scanner(self):

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
        assert results[0].source == str(wav_file)
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


class TestScannerFiltering:
    def test_local_include_filter(self, tmp_path: Path):
        (tmp_path / "match_1.wav").touch()
        (tmp_path / "skip_1.wav").touch()
        config = LocalInputConfig(paths=[tmp_path])
        scanner = LocalScanner(config)
        results = list(scanner.scan(include=["match_*"]))
        assert len(results) == 1
        assert results[0].artifact_id == "match_1.wav"

    def test_local_include_str(self, tmp_path: Path):
        (tmp_path / "match_1.wav").touch()
        config = LocalInputConfig(paths=[tmp_path])
        scanner = LocalScanner(config)
        results = list(scanner.scan(include="match_*"))
        assert len(results) == 1

    def test_local_exclude_filter(self, tmp_path: Path):
        (tmp_path / "keep.wav").touch()
        (tmp_path / "ignore.wav").touch()
        config = LocalInputConfig(paths=[tmp_path])
        scanner = LocalScanner(config)
        results = list(scanner.scan(exclude=["ignore*"]))
        assert len(results) == 1
        assert results[0].artifact_id == "keep.wav"

    def test_local_combined_filters(self, tmp_path: Path):
        (tmp_path / "audio_v1.wav").touch()
        (tmp_path / "audio_v2.wav").touch()
        (tmp_path / "other.wav").touch()
        config = LocalInputConfig(paths=[tmp_path])
        scanner = LocalScanner(config)
        results = list(scanner.scan(include=["audio_*"], exclude=["*_v1.wav"]))
        assert len(results) == 1
        assert results[0].artifact_id == "audio_v2.wav"

    def test_s3_key_filtering(self):

        config = S3InputConfig(
            bucket="b",
            prefix="p/",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )

        with (
            patch("boto3.client") as mock_boto,
            patch("tadween_whisperx.scanners.s3.preflight_check"),
        ):
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            paginator = MagicMock()
            mock_s3.get_paginator.return_value = paginator
            paginator.paginate.return_value = [
                {
                    "Contents": [
                        {"Key": "p/sub1/match.wav"},
                        {"Key": "p/sub1/ignore.wav"},
                        {"Key": "p/sub2/no_match.wav"},
                    ]
                }
            ]

            scanner = S3Scanner(config)
            results = list(
                scanner.scan(include=["*/match.wav"], exclude=["*/ignore.wav"])
            )

            assert len(results) == 1
            assert results[0].source == "p/sub1/match.wav"


class TestHTTPScanner:
    def test_scan_with_extension(self):
        config = HTTPInputConfig(urls=["https://example.com/audio.wav"])
        scanner = HTTPScanner(config)
        results = list(scanner.scan())
        assert len(results) == 1
        assert results[0].source == "https://example.com/audio.wav"
        assert results[0].artifact_id.endswith("audio.wav")
        scanner.close()

    @patch("requests.head")
    def test_scan_without_extension_success(self, mock_head):
        # Mock successful HEAD request for audio/mpeg
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "audio/mpeg"}
        mock_head.return_value = mock_response

        config = HTTPInputConfig(urls=["https://example.com/stream"])
        scanner = HTTPScanner(config)
        results = list(scanner.scan())

        assert len(results) == 1
        assert results[0].source == "https://example.com/stream"
        assert "stream" in results[0].artifact_id
        mock_head.assert_called_once_with(
            "https://example.com/stream", timeout=10, allow_redirects=True
        )
        scanner.close()

    @patch("requests.head")
    def test_scan_without_extension_failure(self, mock_head):
        # Mock HEAD request for text/html
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_head.return_value = mock_response

        config = HTTPInputConfig(urls=["https://example.com/page"])
        scanner = HTTPScanner(config)
        results = list(scanner.scan())

        assert len(results) == 0
        scanner.close()
