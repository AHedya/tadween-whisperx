import logging
import os
from collections import OrderedDict
from pathlib import Path

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
                # If parent is disabled, inherit the parent's dependencies!
                self.logger.debug(
                    f"Component '{parent_name}' is disabled. Inheriting its dependencies for '{target_name}'."
                )
                active_deps.extend(
                    self._resolve_active_dependencies(parent_name, active_nodes)
                )
        return active_deps

    def build(self) -> Workflow:
        wf = None
        try:
            self.logger.info("Building workflow...")
            # Broker & Cache
            broker = InMemoryBroker()
            cache = SimpleCache(CacheSchema)
            repo = self._get_repo(self.config.repo)
            wf_context = WorkflowContext()
            wf = Workflow(
                broker=broker,
                cache=cache,
                repo=repo,
                context=wf_context,
                resources={
                    "cuda": 1,
                },
            )

            active_nodes: set[COMPONENTS_NAME] = set()
            for name, component in self._components.items():
                if component.is_enabled(self.config):
                    active_nodes.add(name)

            self.logger.debug(f"Active components: {active_nodes}")

            for name in active_nodes:
                self.logger.info(f"Adding stage: {name}")
                self._components[name].add_to_workflow(self.config, wf, wf_context)

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
                self.logger.info("Closing partially built workflow resources...")
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
                raise ConfigError(f"Unsupported repo type: {type(active)}")
        except ConfigError as e:
            pth = Path(os.getcwd()) / "json-repo"
            pth.mkdir(exist_ok=True)
            repo = FsRepo(pth, Artifact)
            self.logger.warning(
                f"Error initializing repo from config. Falling back default json repo at [{pth}]. Error: {e}."
            )
            return repo
        except Exception as e:
            raise e
