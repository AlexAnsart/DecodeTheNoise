#!/usr/bin/env sh
# Runs on the VPS, from the repository root: starts the stack on the images of one commit.
# Usage: deploy/up.sh <tag>   (the images noisemap-api:<tag> and noisemap-web:<tag> must be loaded)
set -eu

TAG="$1"
COMPOSE="docker compose --project-directory . -f deploy/docker-compose.yml"

# The tag is kept in .env so that a later plain "compose up" starts the same images.
if grep -q '^NOISEMAP_TAG=' .env; then
  sed -i "s/^NOISEMAP_TAG=.*/NOISEMAP_TAG=${TAG}/" .env
else
  printf 'NOISEMAP_TAG=%s\n' "${TAG}" >> .env
fi

${COMPOSE} up -d --no-build --remove-orphans

# The model is pulled once; afterwards this only checks the digest.
MODEL="$(grep '^EMBEDDING_MODEL=' .env | cut -d= -f2-)"
${COMPOSE} exec -T ollama ollama pull "${MODEL}" >/dev/null

# Images of earlier commits are no longer used: free the disk.
docker images --format "{{.Repository}}:{{.Tag}}"   | grep -E "^noisemap-(api|web):" | grep -v ":${TAG}$" | xargs -r docker rmi >/dev/null 2>&1 || true
${COMPOSE} ps
