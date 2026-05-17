ARG HF_DEST="/app/models"
ARG FFMPEG_VERSION="7.1.1"


FROM ubuntu:24.04 AS ffmpeg-builder
ARG FFMPEG_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        yasm \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.gz \
    | tar xz \
    && cd ffmpeg-${FFMPEG_VERSION} \
    && ./configure --enable-shared --disable-static --prefix=/usr/local \
    && make -j$(nproc) \
    && make install



# ------------------------------
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/ffprobe /usr/bin/
COPY --from=ffmpeg-builder /usr/local/lib/ /usr/local/lib/
COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/
RUN ldconfig

# ------------------------------
FROM scratch AS hf_cache
# a fallback net for host huggingface cache context

# ------------------------------
FROM python:3.11-slim AS stash_models

ARG HF_DEST
ENV HF_DEST="${HF_DEST}" \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/

WORKDIR /app
RUN uv init --python 3.11 && \
    uv add huggingface-hub hf_transfer
COPY scripts/download_model.py .

RUN --mount=type=secret,id=HF_TOKEN,required=false \
    --mount=type=bind,from=hf_cache,source=/,target=/tmp/host-cache,readonly \
    HF_TOKEN=$(cat /run/secrets/HF_TOKEN) \
    uv run download_model.py "${HF_DEST}"


# ------------------------------
FROM runtime AS app
WORKDIR /app

ARG HF_DEST
ENV HF_HOME=/app/models/hf \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=stash_models ${HF_DEST} /app/models/hf

COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENTRYPOINT ["tadweenx"]
CMD ["run"]
