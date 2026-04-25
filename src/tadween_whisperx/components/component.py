from abc import ABC, abstractmethod
from typing import Literal

from tadween_core.coord import StageContextConfig, WorkflowContext
from tadween_core.handler.defaults.s3_downloader import S3DownloadHandler
from tadween_core.task_queue import init_queue
from tadween_core.workflow.workflow import Workflow

from tadween_whisperx.components.alignment.handler import (
    AlignmentConfig as AlignmentModelConfig,
)
from tadween_whisperx.components.alignment.handler import AlignmentHandler
from tadween_whisperx.components.alignment.policy import AlignmentPolicy
from tadween_whisperx.components.artifact import (
    STASH_EVENT,
    claim_stash,
    release_stash,
    rollback_stash,
    stash_predicate,
)
from tadween_whisperx.components.diarization.handler import DiarizationHandler
from tadween_whisperx.components.diarization.handler import (
    ModelConfig as DiarizationModelConfig,  # noqa
)
from tadween_whisperx.components.diarization.policy import DiarizationPolicy
from tadween_whisperx.components.loader.handler import (
    AudioLoader,
    AVHandler,
    TorchCodecHandler,
)
from tadween_whisperx.components.loader.policy import LoaderPolicy, S3Policy
from tadween_whisperx.components.normalizer.handler import NormalizeHandler
from tadween_whisperx.components.normalizer.policy import NormalizerPolicy
from tadween_whisperx.components.transcription.handler import (
    TranscriptionHandler,
    TranscriptionModelConfig,
)
from tadween_whisperx.components.transcription.policy import TranscriptionPolicy
from tadween_whisperx.config import AppConfig


def is_terminal_audio(component_name: str, config: AppConfig) -> bool:
    """Returns True if the component is the last one needing audio in its branch."""
    if component_name == "diarization":
        return True
    if component_name == "transcription":
        # Terminal if no alignment follows
        return not config.alignment.enabled
    if component_name == "alignment":
        return True
    return False


class WorkflowComponent(ABC):
    """Pre-configured workflow component.

    Used to provide registry for workflow builder to get a pre-configured linking, stages, and logical order.
    """

    name: str
    depends_on: list[str]

    @abstractmethod
    def is_enabled(self, config: AppConfig) -> bool:
        """Returns True if this component should be added to the workflow."""
        pass

    @abstractmethod
    def add_to_workflow(
        self, config: AppConfig, wf: Workflow, wf_context: WorkflowContext
    ):
        """Initializes the handler and calls wf.add_stage(...)"""
        pass


class DownloaderComponent(WorkflowComponent):
    name = "downloader"
    depends_on = []

    def is_enabled(self, config: AppConfig) -> bool:
        return not config.input.type == "local"

    def add_to_workflow(
        self, config: AppConfig, wf: Workflow, wf_context: WorkflowContext
    ):
        wf.add_stage(
            self.name,
            handler=S3DownloadHandler(
                config.input.download_path,
                access_key=config.input.aws_access_key_id,
                secret_key=config.input.aws_secret_access_key,
                endpoint_url=config.input.endpoint_url,
                session_token=config.input.aws_session_token,
                max_retries=config.input.max_retries,
                multipart_threshold_mb=config.input.multipart_threshold_mb,
                max_workers=config.input.max_workers,
                max_concurrency_per_file=config.input.max_concurrency_per_file,
            ),
            policy=S3Policy(),
        )


class AudioLoaderComponent(WorkflowComponent):
    name = "audio_loader"
    depends_on = ["downloader"]

    def is_enabled(self, config: AppConfig) -> bool:
        # Audio loader is always needed if we have any ASR task
        return True

    def add_to_workflow(
        self, config: AppConfig, wf: Workflow, wf_context: WorkflowContext
    ):
        if config.loader.type == "torchcodec":
            handler = TorchCodecHandler()
        elif config.loader.type == "av":
            handler = AVHandler()
        else:
            handler = AudioLoader()

        wf.add_stage(
            self.name,
            handler=handler,
            policy=LoaderPolicy(),
            context_config=StageContextConfig(
                context=wf_context,
                defer_predicate=stash_predicate,
                defer_event=STASH_EVENT,
                defer_state_update=claim_stash,
                rollback_state_update=rollback_stash,
            ),
            task_queue=init_queue(**config.loader.task_queue),
        )


class DiarizationComponent(WorkflowComponent):
    name = "diarization"
    depends_on = ["audio_loader"]

    def is_enabled(self, config: AppConfig) -> bool:
        return config.diarization.enabled

    def add_to_workflow(
        self, config: AppConfig, wf: Workflow, wf_context: WorkflowContext
    ):
        handler = DiarizationHandler(
            DiarizationModelConfig.model_construct(**config.diarization.__dict__)
        )

        wf.add_stage(
            self.name,
            handler=handler,
            policy=DiarizationPolicy(),
            task_queue=init_queue(**config.diarization.task_queue),
            demands={"cuda": 1},
            context_config=StageContextConfig(
                context=wf_context,
                done_state_update=release_stash,
                notify_events=[STASH_EVENT],
            ),
        )


class TranscriptionComponent(WorkflowComponent):
    name = "transcription"
    depends_on = ["audio_loader"]

    def is_enabled(self, config: AppConfig) -> bool:
        return config.transcription.enabled

    def add_to_workflow(
        self, config: AppConfig, wf: Workflow, wf_context: WorkflowContext
    ):
        cfg = TranscriptionModelConfig.model_construct(**config.transcription.__dict__)
        handler = TranscriptionHandler(cfg)

        wf.add_stage(
            self.name,
            handler=handler,
            policy=TranscriptionPolicy(),
            task_queue=init_queue(**config.transcription.task_queue),
            demands={"cuda": 1},
            context_config=StageContextConfig(
                context=wf_context,
                done_state_update=release_stash
                if is_terminal_audio(self.name, config)
                else None,
                notify_events=[STASH_EVENT],
            ),
        )


class AlignmentComponent(WorkflowComponent):
    name = "alignment"
    depends_on = ["transcription"]

    def is_enabled(self, config: AppConfig) -> bool:
        return config.alignment.enabled

    def add_to_workflow(
        self, config: AppConfig, wf: Workflow, wf_context: WorkflowContext
    ):
        handler = AlignmentHandler(
            AlignmentModelConfig.model_construct(**config.alignment.__dict__)
        )
        handler.warmup()

        wf.add_stage(
            self.name,
            handler=handler,
            policy=AlignmentPolicy(),
            task_queue=init_queue(**config.alignment.task_queue),
            demands={"cuda": 1},
            context_config=StageContextConfig(
                context=wf_context,
                done_state_update=release_stash,
                notify_events=[STASH_EVENT],
            ),
        )


class NormalizerComponent(WorkflowComponent):
    name = "norm"
    depends_on = ["transcription"]

    def is_enabled(self, config: AppConfig) -> bool:
        return config.normalizer.enabled

    def add_to_workflow(
        self, config: AppConfig, wf: Workflow, wf_context: WorkflowContext
    ):
        handler = NormalizeHandler(
            allowed_chars=config.normalizer.allowed_chars,
            max_word_len=config.normalizer.max_word_len,
            allowed_words=config.normalizer.allowed_words,
        )
        wf.add_stage(
            self.name,
            handler=handler,
            policy=NormalizerPolicy(),
        )


COMPONENTS_NAME = Literal[
    "downloader", "audio_loader", "diarization", "transcription", "alignment", "norm"
]
