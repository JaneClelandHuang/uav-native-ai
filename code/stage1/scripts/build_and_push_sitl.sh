#!/usr/bin/env bash
set -euo pipefail

# Instructor-only. Builds the pinned SITL image once and pushes it to GHCR so
# students `docker compose pull` instead of compiling ArduPilot from source
# in class (a source build commonly takes 10-20 minutes -- fine for us,
# bad for a live session).
#
# The ardupilot-dev-base image this builds on is linux/amd64 only, so this
# image is amd64 only too. On Apple Silicon it runs under Docker Desktop's
# Rosetta-accelerated emulation -- see SETUP.md for the one-time setting to
# enable that.
#
# Usage: GHCR_OWNER=your-org ./scripts/build_and_push_sitl.sh [ardupilot-tag]

cd "$(dirname "${BASH_SOURCE[0]}")/.."

ARDUPILOT_TAG="${1:-Copter-4.6.3}"
GHCR_OWNER="${GHCR_OWNER:?Set GHCR_OWNER to your GitHub org/user, e.g. GHCR_OWNER=my-org}"
TAG_LOWER="$(echo "${ARDUPILOT_TAG}" | tr '[:upper:]' '[:lower:]')"
# Docker repository paths (everything before the tag) must be lowercase --
# GitHub usernames/orgs commonly aren't, so lowercase it here rather than
# asking instructors to pass it in lowercase themselves.
OWNER_LOWER="$(echo "${GHCR_OWNER}" | tr '[:upper:]' '[:lower:]')"
IMAGE="ghcr.io/${OWNER_LOWER}/uav-course-sitl:${TAG_LOWER}"

echo "Building ${IMAGE} (platform linux/amd64)"
docker build \
    --platform linux/amd64 \
    --build-arg ARDUPILOT_TAG="${ARDUPILOT_TAG}" \
    -f docker/Dockerfile.sitl \
    -t "${IMAGE}" \
    .

echo "Pushing ${IMAGE}"
docker push "${IMAGE}"

echo "Done. Set SITL_IMAGE=${IMAGE} in .env for students."
