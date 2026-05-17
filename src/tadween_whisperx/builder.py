import functools
import logging
import os
from collections import OrderedDict

from tadween_core.broker.memory import InMemoryBroker
from tadween_core.cache import SimpleCache
from tadween_core.coord import WorkflowContext
from tadween_core.repo.base import BaseArtifactRepo
from tadween_core.repo.fs import FsRepo
from tadween_core.repo.json import FsJsonRepo
from tadween_core.repo.s3 import S3Repo
from tadween_core.workflow import Workflow

from tadween_whisperx.components.artifact import Artifact, CacheSchema
from tadween_whisperx.components.component import (
    COMPONENTS_NAME,
    AlignmentComponent,
    AudioLoaderComponent,
    DiarizationComponent,
    DownloaderComponent,
    NormalizerComponent,
    TranscriptionComponent,
    WorkflowComponent,
)
from tadween_whisperx.components.throttle import (
    get_workflow_resources,
    release_cache,
)
from tadween_whisperx.config import (
    AppConfig,
    ConfigError,
    FSRepoConfig,
    JsonRepoConfig,
    RepoProfiles,
    S3RepoConfig,
)
from tadween_whisperx.scanners import BaseScanner, create_scanner


class WorkflowBuilder:
    def __init__(
        self,
        config: AppConfig,
    ):
        self.config = config

        self.logger = logging.getLogger("tadween_whisperx")
        self._components: OrderedDict[COMPONENTS_NAME, WorkflowComponent] = OrderedDict(
            [
                ("downloader", DownloaderComponent()),
                ("audio_loader", AudioLoaderComponent()),
                ("diarization", DiarizationComponent()),
                ("transcription", TranscriptionComponent()),
                ("alignment", AlignmentComponent()),
                ("norm", NormalizerComponent()),
            ]
        )

    def _resolve_active_dependencies(
        self, target_name: COMPONENTS_NAME, active_nodes: set[COMPONENTS_NAME]
    ) -> list[COMPONENTS_NAME]:
        """
        Recursively finds the closest *enabled* parent component.
        """
        active_deps = []
        for parent_name in self._components[target_name].depends_on:
            if parent_name in active_nodes:
                active_deps.append(parent_name)
            else:
                # If parent is disabled, inherit the parent's dependencies
                self.logger.debug(
                    f"Component '{parent_name}' is disabled. Inheriting its dependencies for '{target_name}'."
                )
                active_deps.extend(
                    self._resolve_active_dependencies(parent_name, active_nodes)
                )
        return active_deps

    def preflight_check(self):
        """
        Performs pre-flight checks such as verifying model availability and hardware readiness.
        """
        self.logger.debug("Performing pre-flight checks...")

        # cuda
        import torch

        if not torch.cuda.is_available():
            self.logger.error("CUDA is not available.")
            raise RuntimeError("CUDA must be installed.")
        else:
            self.logger.info(
                f"CUDA is available. Device: {torch.cuda.get_device_name(0)}"
            )

        # check model availability
        hf_offline = os.environ.get("HF_HUB_OFFLINE") == "1"
        hf_token = os.environ.get("HF_TOKEN") or (
            self.config.diarization.token if self.config.diarization.enabled else None
        )

        # Stages to check
        # (stage_attr, repo_id, is_gated)
        checks = []
        if self.config.diarization.enabled:
            checks.append(("diarization", self.config.diarization.model_id, True))
        if self.config.transcription.enabled:
            m_id = self.config.transcription.model_id
            # Common mapping for faster-whisper
            repo_id = m_id
            if m_id in [
                "tiny",
                "base",
                "small",
                "medium",
                "large-v1",
                "large-v2",
                "large-v3",
            ]:
                repo_id = f"Systran/faster-whisper-{m_id}"
            checks.append(("transcription", repo_id, False))
        if self.config.alignment.enabled and self.config.alignment.model_id:
            checks.append(("alignment", self.config.alignment.model_id, False))

        for attr, repo_id, is_gated in checks:
            if not self._is_model_available(repo_id):
                if hf_offline:
                    self.logger.warning(
                        f"Offline mode: Model '{repo_id}' for stage '{attr}' not found. Disabling stage."
                    )
                    getattr(self.config, attr).enabled = False
                elif is_gated and not hf_token:
                    self.logger.warning(
                        f"Gated model '{repo_id}' for stage '{attr}' requires HF_TOKEN and is not cached. Disabling stage."
                    )
                    getattr(self.config, attr).enabled = False
                else:
                    self.logger.warning(
                        f"Model '{repo_id}' for stage '{attr}' is missing. Downloading now..."
                    )
                    try:
                        self._download_model(repo_id, token=hf_token)
                    except Exception as e:
                        self.logger.error(
                            f"Failed to download model '{repo_id}': {e}. Disabling stage."
                        )
                        getattr(self.config, attr).enabled = False

    def build(self) -> Workflow:
        self.config.validate()
        wf = None
        try:
            self.logger.info("Building workflow...")
            broker = InMemoryBroker()
            cache = SimpleCache(CacheSchema)
            repo = self._get_repo(self.config.repo)
            wf_context = WorkflowContext()
            # Inject cache for centralized cleanup in throttle.py
            wf_context.state["__cache__"] = cache

            wf_context.on_artifact_done(
                functools.partial(release_cache, ctx=wf_context)
            )

            wf = Workflow(
                broker=broker,
                cache=cache,
                repo=repo,
                context=wf_context,
                resources=get_workflow_resources(),
                # no payload propagation
                default_payload_extractor=lambda x: {},
            )

            active_nodes: set[COMPONENTS_NAME] = set()
            for name, component in self._components.items():
                if component.is_enabled(self.config):
                    active_nodes.add(name)

            self.logger.debug(f"Active components: {active_nodes}")

            for name in active_nodes:
                self.logger.info(f"Adding stage: {name}")
                self._components[name].add_to_workflow(self.config, wf)

            for name in active_nodes:
                actual_deps = self._resolve_active_dependencies(name, active_nodes)
                for dep in actual_deps:
                    self.logger.info(f"Linking: {dep} -> {name}")
                    wf.link(dep, name)

            # Set entry point to the first enabled component
            if self._components.get("downloader").is_enabled(self.config):
                self.logger.info("Setting entry point to 'downloader'")
                wf.set_entry_point("downloader")
            else:
                self.logger.info("Setting entry point to 'audio_loader'")
                wf.set_entry_point("audio_loader")

            return wf
        except Exception as e:
            self.logger.error(f"Failed to build workflow: {e}")
            if wf is not None:
                self.logger.info("Closing partially-built workflow resources...")
                wf.close()
            raise e

    def get_scanner(self) -> BaseScanner:
        return create_scanner(self.config.input)

    def _get_repo(self, profiles: RepoProfiles) -> BaseArtifactRepo:
        try:
            active = profiles.get_active()
            if type(active) is FSRepoConfig:
                return FsRepo(active.path, artifact_type=Artifact)
            elif type(active) is JsonRepoConfig:
                return FsJsonRepo(active.path, artifact_type=Artifact)
            elif isinstance(active, S3RepoConfig):
                return S3Repo(
                    artifact_type=Artifact,
                    bucket_id=active.bucket,
                    prefix=active.prefix,
                    client_config=active.to_s3_client_config,
                )
            else:
                self.logger.warning(
                    f"Unsupported repo type or missing config: {type(active)}"
                )
                return None
        except ConfigError as e:
            self.logger.warning(
                f"Failed initializing repo from config. Error: {e}. "
                "No results will be saved"
            )
            return None
        except Exception as e:
            raise e

    def _is_model_available(self, repo_id: str) -> bool:
        try:
            from huggingface_hub import scan_cache_dir

            for repo in scan_cache_dir().repos:
                if repo.repo_id == repo_id:
                    return True
        except Exception:
            pass
        return False

    def _download_model(self, repo_id: str, token: str | None = None):
        from huggingface_hub import snapshot_download

        # We don't specify destination, let it use HF_HOME/hub
        snapshot_download(repo_id=repo_id, token=token)
