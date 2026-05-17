import os
import shutil
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

HOST_CACHE = Path("/tmp/host-cache")
MIN_CACHED_SIZE_MB = 5

assert HOST_CACHE.exists()


@dataclass(frozen=True)
class ModelSpec:
    name: str
    repo_id: str
    gated: bool
    allow_patterns: list[str] | None = None  # None fetches everything


TRANSCRIPTION_MODELS: list[ModelSpec] = [
    ModelSpec(
        name="faster-whisper-large-v3",
        repo_id="Systran/faster-whisper-large-v3",
        gated=False,
        allow_patterns=[
            "config.json",
            "preprocessor_config.json",
            "model.bin",
            "tokenizer.json",
            "vocabulary.*",
        ],
    ),
]

DIARIZATION_MODELS: list[ModelSpec] = [
    ModelSpec(
        name="speaker-diarization-community-1",
        repo_id="pyannote/speaker-diarization-community-1",
        gated=True,
    ),
]

ALIGNMENT_MODELS: list[ModelSpec] = []

ALL_MODELS: list[ModelSpec] = (
    TRANSCRIPTION_MODELS + DIARIZATION_MODELS + ALIGNMENT_MODELS
)


def acquire(spec: ModelSpec, dest: Path, token: str | None) -> bool:
    """
    Acquire a single model into dest.  Returns True on success.
    Follows the three-step order: dest cache → host bind → download.
    """
    from huggingface_hub import snapshot_download

    if is_cached(spec.repo_id):
        print("\t already in dest. skipping.")
        return True

    if copy_from_host(spec.repo_id, dest):
        print("\t copied from host cache.")
        return True

    print("\t downloading...")
    try:
        snapshot_download(
            repo_id=spec.repo_id,
            allow_patterns=spec.allow_patterns,
            token=token,
        )
        print("\t downloaded.")
        return True
    except Exception as exc:
        warnings.warn(f"Download failed for '{spec.repo_id}': {exc}", stacklevel=3)
        return False


def hf_cache_dir(repo_id: str) -> str:
    return "models--" + repo_id.replace("/", "--")


def is_cached(repo_id: str) -> bool:
    """Must be called after HF_HOME and dest/hub are both set up."""
    from huggingface_hub import scan_cache_dir

    try:
        for repo in scan_cache_dir().repos:
            if repo.repo_id == repo_id:
                return True
    except Exception:
        pass
    return False


def is_host_cached(repo_id: str) -> bool:
    """
    Return True when the model directory is present and non-trivially sized
    inside the host-cache bind mount.
    """
    src = HOST_CACHE / "hub" / hf_cache_dir(repo_id)
    if src.exists() and src.is_dir():
        return True
    print(f"Host-miss: {repo_id}")
    return False
    size = sum(
        f.stat().st_size for f in src.rglob("*") if f.is_file() and not f.is_symlink()
    )
    return size / (1024 * 1024) >= MIN_CACHED_SIZE_MB


def copy_from_host(repo_id: str, dest: Path) -> bool:
    """
    Copy a model directory from the host-cache bind into dest, preserving
    symlinks so the HuggingFace Hub blob/snapshot structure stays intact.
    Returns True on success, False when the model is absent from the bind.
    """
    if not is_host_cached(repo_id):
        return False

    src = HOST_CACHE / "hub" / hf_cache_dir(repo_id)
    dst = dest / "hub" / hf_cache_dir(repo_id)
    print(f"\t host cache HIT — {src} -> {dst}")
    shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
    return True


def check_gated(token: str | None, models: list[ModelSpec] = ALL_MODELS):
    gated_uncovered = [
        m
        for m in models
        if m.gated and not is_cached(m.repo_id) and not is_host_cached(m.repo_id)
    ]
    if gated_uncovered and not token:
        names = "\n  ".join(m.repo_id for m in gated_uncovered)
        warnings.warn(
            f"HF_TOKEN is not set but the following gated model(s) are not cached:\n"
            f"  {names}\n"
            f"  Accept the user conditions on HuggingFace and re-run with\n"
            f"  --secret id=HF_TOKEN,env=HF_TOKEN, or supply a pre-populated\n"
            f"  host cache via --build-context hf-cache=$HOME/.cache/huggingface.",
            stacklevel=2,
        )


def main():
    dest = Path(
        sys.argv[1] if len(sys.argv) > 1 else os.environ.get("HF_DEST", "/app/models")
    )
    dest.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(dest)
    token: str | None = os.environ.get("HF_TOKEN") or None  # "" -> None
    check_gated(token=token)

    failures: list[str] = []
    for spec in ALL_MODELS:
        print(f"Working on: {spec.repo_id}")

        if (
            spec.gated
            and not token
            and not is_cached(spec.repo_id)
            and not is_host_cached(spec.repo_id)
        ):
            failures.append(spec.name)
            continue

        if not acquire(spec, dest, token):
            failures.append(spec.name)
    print("─" * 60)

    print("~~", dest)
    print("~~", list(dest.iterdir()))
    if failures:
        print(f"\nFailed: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    main()
