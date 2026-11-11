#!/usr/bin/env bash
# Installs tippecanoe on a GitHub runner, for the three workflows that build
# or check vector-tile archives (vector-tiles.yml, update-tiger-tiles.yml,
# update-portal-tiles.yml). One copy, so the three cannot install it three
# different ways.
#
# apt first, because the runner image's Ubuntu ships the release the tile
# gates were last measured with (2.53.0-1build1 on the 26.04 image, read from
# the tiles job's own log on 2026-11-11).
#
# If apt cannot install it, the same release is built from its source on
# GitHub. On 2026-11-11 every Ubuntu package host (azure.archive.ubuntu.com,
# archive.ubuntu.com, security.ubuntu.com) stopped resolving from the runners
# for hours while github.com still answered, so the tiles check failed on
# every pull request five times running for a reason no pull request could
# fix. The source is pinned by commit as well as by tag: a tag can be moved,
# and the build stops if the tag no longer names the commit recorded here.
#
# The build needs a C++ compiler, make and the SQLite and zlib headers. The
# runner image has carried all four; if one is missing the script says which
# and stops, because installing it would need the apt hosts that failed.
set -euo pipefail

TAG="2.53.0"
COMMIT="bb4f22067885c2cc9a5d6db5aa34742db63dd74d"
REPO="https://github.com/felt/tippecanoe.git"

# The runner image's Google Chrome apt source is unused here and once served
# a Packages file whose hash did not match its own Release file, failing every
# apt-get update (smoke-test.yml records it).
sudo find /etc/apt/sources.list.d -maxdepth 1 -type f \
     \( -name '*.list' -o -name '*.sources' \) \
     -exec grep -q 'dl\.google\.com' {} \; -print -delete 2>/dev/null || true

# apt-get update reports an unreachable host as a warning and carries on, so
# only the install's own exit status says whether apt worked.
sudo apt-get update -q || true
if sudo apt-get install -y -q tippecanoe; then
  tippecanoe --version
  exit 0
fi

echo "::warning::apt could not install tippecanoe; building ${TAG} from its source on GitHub"

missing=""
command -v g++ >/dev/null || missing="$missing g++"
command -v make >/dev/null || missing="$missing make"
printf '#include <sqlite3.h>\nint main(void){return 0;}\n' | g++ -x c++ -fsyntax-only - 2>/dev/null \
  || missing="$missing libsqlite3-dev"
printf '#include <zlib.h>\nint main(void){return 0;}\n' | g++ -x c++ -fsyntax-only - 2>/dev/null \
  || missing="$missing zlib1g-dev"
if [ -n "$missing" ]; then
  echo "::error::cannot build tippecanoe: the runner lacks${missing}, and apt could not install packages"
  exit 1
fi

src="${RUNNER_TEMP:-/tmp}/tippecanoe-src"
rm -rf "$src"
git clone --quiet --depth 1 --branch "$TAG" "$REPO" "$src"
head="$(git -C "$src" rev-parse HEAD)"
if [ "$head" != "$COMMIT" ]; then
  echo "::error::tippecanoe tag ${TAG} names ${head}, not the recorded ${COMMIT}; refusing to build it"
  exit 1
fi
make -C "$src" -j"$(nproc)" >/dev/null
sudo make -C "$src" install >/dev/null
tippecanoe --version
