import subprocess
from pathlib import Path

import av
import numpy as np
from pydantic import BaseModel, ConfigDict, SkipValidation
from tadween_core.handler import BaseHandler
from torchcodec.decoders import AudioDecoder


class AudioLoaderInput(BaseModel):
    file_path: Path
    sr: int = 16_000


class AudioLoaderOutput(BaseModel):
    audio_array: SkipValidation[np.ndarray]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AudioLoader(BaseHandler[AudioLoaderInput, AudioLoaderOutput]):
    def run(self, inputs):
        file = str(inputs.file_path)
        sr = str(inputs.sr)
        try:
            cmd = [
                "ffmpeg",
                "-nostdin",
                "-threads",
                "0",
                "-i",
                file,
                "-f",
                "s16le",
                "-ac",
                "1",
                "-acodec",
                "pcm_s16le",
                "-ar",
                sr,
                "-",
            ]
            out = subprocess.run(cmd, capture_output=True, check=True).stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

        audio_array = (
            np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
        )
        return AudioLoaderOutput(audio_array=audio_array)

    def warmup(self):
        pass

    def shutdown(self):
        pass


class AVHandler(BaseHandler[AudioLoaderInput, AudioLoaderOutput]):
    def run(self, inputs):
        with av.open(inputs.file_path) as container:
            stream = container.streams.audio[0]

            resampler = av.AudioResampler(
                format="s16",
                layout="mono",
                rate=inputs.sr,
            )

            chunks = []
            for frame in container.decode(stream):
                for rf in resampler.resample(frame):
                    chunks.append(rf.to_ndarray()[0])
            # flush resampler. Retrieves buffered tail samples
            for rf in resampler.resample(None):
                chunks.append(rf.to_ndarray()[0])

            return AudioLoaderOutput(
                audio_array=np.concatenate(chunks).astype(np.float32) / 32768.0
            )

    def warmup(self):
        pass

    def shutdown(self):
        pass


class TorchCodecHandler(BaseHandler[AudioLoaderInput, AudioLoaderOutput]):
    def run(self, inputs):
        decoder = AudioDecoder(inputs.file_path, sample_rate=inputs.sr, num_channels=1)
        waveform = decoder.get_all_samples()

        return AudioLoaderOutput(audio_array=waveform.data.view(-1).numpy())

    def warmup(self):
        pass

    def shutdown(self):
        pass
