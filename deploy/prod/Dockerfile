ARG PYTHON_BUILDER_IMAGE=3.11-slim-bookworm

FROM python:${PYTHON_BUILDER_IMAGE} AS python-base
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends git tini \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /root/.cache \
    && rm -rf /var/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false\
    && mkdir -p /workspace/app \
    && pip install --quiet -U pip wheel setuptools virtualenv

FROM python-base AS build-base
ENV PATH="/workspace/app/.venv/bin:/usr/local/bin:$PATH"
RUN apt-get install -y --no-install-recommends build-essential curl \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /root/.cache \
    && rm -rf /var/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false

WORKDIR /workspace/app
COPY pyproject.toml README.md .pre-commit-config.yaml LICENSE ./
# COPY scripts ./scripts/
# COPY public ./public/
# COPY resources ./resources/
RUN python -m venv /workspace/app/.venv

FROM build-base AS prod-image
ARG ENV_SECRETS="runtime-secrets"
ENV PATH="/workspace/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/workspace/app/.venv" \
    ENV_SECRETS="${ENV_SECRETS}"  \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random
WORKDIR /workspace/app
COPY docs/ docs/
COPY tests/ tests/
COPY src/ src/
RUN pip install -e .
STOPSIGNAL SIGINT
EXPOSE 8000
ENV BLACKFISH_HOST="0.0.0.0"
ENV BLACKFISH_PORT="8080"
ENV BLACKFISH_HOME_DIR="/data"
ENTRYPOINT ["tini","--" ]
CMD [ "blackfish", "start"]

# docker run -v /var/run/docker.sock:/var/run/docker.sock ... something like this
# is recommended to allow the container to start sibling containers instead of
# running docker-in-docker ("dind"). Equivalent for apptainer?
