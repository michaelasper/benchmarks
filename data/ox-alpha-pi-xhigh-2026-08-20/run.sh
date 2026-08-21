#!/usr/bin/env bash
# Historical launcher copied from the SlopCodeBench source root. It expects to
# be placed back at that root beside configs/; it is provenance, not a
# standalone launcher from this published data directory.
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_dir"

# Keep bind-mounted temporary paths inside a Colima-shared directory.
mkdir -p "$repo_dir/tmp/slop-code"
export TMPDIR="$repo_dir/tmp/slop-code"

if [[ -z "${OPENROUTER_API_KEY:-}" && -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

: "${OPENROUTER_API_KEY:?Set OPENROUTER_API_KEY in the environment or .env}"

if ! command -v uv >/dev/null 2>&1; then
    echo "error: uv is required (https://docs.astral.sh/uv/)" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "error: Docker is required" >&2
    exit 1
fi

# docker-py does not honor Docker CLI contexts. Export the active endpoint.
if [[ -z "${DOCKER_HOST:-}" ]]; then
    docker_context="$(docker context show 2>/dev/null || true)"
    if [[ -n "$docker_context" ]]; then
        docker_host="$(
            docker context inspect \
                --format '{{.Endpoints.docker.Host}}' \
                "$docker_context" 2>/dev/null || true
        )"
        if [[ -n "$docker_host" ]]; then
            export DOCKER_HOST="$docker_host"
        fi
    fi
fi

if ! docker info >/dev/null 2>&1; then
    echo "error: Docker is installed but its daemon is not running" >&2
    exit 1
fi

# Eight workers run all eight problems simultaneously. Concurrent evaluation
# overlaps each checkpoint's tests with that problem's next checkpoint solve.
exec uv run slop-code run \
    --config configs/runs/ox-alpha-pi-both-subsets.yaml \
    --num-workers "${SCBENCH_NUM_WORKERS:-8}" \
    --concurrent-evaluation \
    "$@"
