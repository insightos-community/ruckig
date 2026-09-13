# ruckig: reproducible platform builds

This guide describes the InsightOS fork/import and the scripts in this checkout.
The validated distribution from this repository is **Linux x86_64 musl**. glibc
and macOS source recipes below are native development builds, not a claim that
this fork publishes or has requalified those binaries. The complete installer
selects different binary formats and dependency locks for each platform.

## Source and tools

Validated musl tag: [`musl-v0.19.4-2`](https://github.com/insightos-community/ruckig/releases/tag/musl-v0.19.4-2);
source commit: `950e957a51f217ac5fe04bb93fea23e3decb5d6f`. Use a normal clone so container packaging can read `.git`.

```bash
git clone https://github.com/insightos-community/ruckig.git ruckig-repro
cd ruckig-repro
git checkout --detach musl-v0.19.4-2
test "$(git rev-parse HEAD)" = 950e957a51f217ac5fe04bb93fea23e3decb5d6f
```

Native build prerequisites: C/C++ compiler, CMake, Ninja and Git. Install toolchain packages using the build host’s configured package repositories.

## Linux glibc

Run on a native Linux x86_64 glibc build host (Ubuntu 24.04 is the project CI
baseline). Install the prerequisites above. This native recipe uses the host
compiler and libraries; it does not apply the musl-only patches or emit a
portable/manylinux wheel.

```bash
cmake -S . -B build-glibc -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_INSTALL_PREFIX="$PWD/prefix-glibc" -DCMAKE_INSTALL_LIBDIR=lib \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF -DBUILD_PYTHON_MODULE=OFF
cmake --build build-glibc --parallel 2
ctest --test-dir build-glibc --output-on-failure --timeout 600
cmake --install build-glibc
```

## Linux musl: reproduce the Release

The authoritative pipeline is [musl-release.yml](.github/workflows/musl-release.yml),
with [build.sh](ci/musl/build.sh) as its local entry point. Run from the checked-out
repository root on a Linux x86_64 Docker host. Building requires network access
for pinned sources and package downloads; the output directory must be fresh.

```bash
REPRO_IMAGE='python:3.13-alpine3.23@sha256:75f27d686432419c9d42420b2b9ef605868c7a0682a6be10a6601fad46c2df01'
REPRO_WORK="$(mktemp -d "${TMPDIR:-/tmp}/ruckig-musl.XXXXXXXX")"
docker run --rm --platform linux/amd64 --cpus=2 --memory=12g --memory-swap=12g --pids-limit=1024 \
  --mount "type=bind,src=$PWD,dst=/src,readonly" \
  --mount "type=bind,src=$REPRO_WORK,dst=/work" \
  "$REPRO_IMAGE" sh /src/ci/musl/build.sh
```

The CI additionally tests the repaired wheel without network:

```bash
docker run --rm --platform linux/amd64 --network none \
  --mount "type=bind,src=$PWD,dst=/src,readonly" \
  --mount "type=bind,src=$REPRO_WORK,dst=/work" \
  "$REPRO_IMAGE" sh -ec 'python -m pip install --no-index --no-deps /work/dist/*.whl; python /src/ci/musl/clean_smoke.py'
```

Outputs are in `$REPRO_WORK/dist/`; build/test logs and package inventories are
in `$REPRO_WORK/logs/`. Retain `build-manifest.json` and `SHA256SUMS` alongside:

- `ruckig-0.19.4-cp313-cp313-musllinux_1_2_x86_64.whl`
- `ruckig-0.19.4-musl-x86_64-cpp.tar.gz`

```bash
(cd "$REPRO_WORK/dist" && sha256sum -c SHA256SUMS)
```

The pinned Python/Alpine image does not freeze every subsequently installed APK
or pip package. Preserve the emitted package inventory; the result is a musl
build, not a completely static application or a bit-for-bit reproducibility claim.

## macOS / macosx

Use a fresh checkout on Apple Silicon, Xcode Command Line Tools and native arm64
versions of the prerequisites. Do not reuse Linux build directories or `$ORIGIN`
RPATHs. The following is a source-development recipe; it is not the macOS installer
release recipe or a universal/x86_64 qualification.

```bash
cmake -S . -B build-macos -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_INSTALL_PREFIX="$PWD/prefix-macos" -DCMAKE_INSTALL_LIBDIR=lib \
  -DBUILD_SHARED_LIBS=ON -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF -DBUILD_PYTHON_MODULE=OFF
cmake --build build-macos --parallel 2
ctest --test-dir build-macos --output-on-failure --timeout 600
cmake --install build-macos
```

The installer uses the upstream CPython 3.13 macOS arm64 wheel for `ruckig==0.19.4`.

For a native CPython 3.13 wheel on either glibc or macOS, use uv 0.12.12:

```bash
uv venv --python 3.13.15 .venv-repro
uv pip install --python .venv-repro/bin/python pip==25.2 scikit-build-core==1.0.3 nanobind==3.0.1
.venv-repro/bin/python -m pip wheel --no-deps --no-build-isolation . -w dist-native \
  -Ccmake.define.BUILD_EXAMPLES=OFF -Ccmake.define.BUILD_TESTS=OFF
uv pip install --python .venv-repro/bin/python dist-native/*.whl
.venv-repro/bin/python ci/musl/clean_smoke.py
```

`auditwheel` repair is only for Linux ELF wheels; do not run it on Mach-O/macOS wheels.

## Run the same build on GitHub

A manual dispatch builds/tests artifacts without publishing. Select the immutable
release tag to reproduce its scripts (GitHub CLI and workflow permission required):

```bash
gh workflow run musl-release.yml --repo insightos-community/ruckig --ref musl-v0.19.4-2
gh run list --repo insightos-community/ruckig --workflow musl-release.yml --limit 5
# Set REPRO_RUN_ID to the run ID printed above.
gh run watch "$REPRO_RUN_ID" --repo insightos-community/ruckig --exit-status
gh run download "$REPRO_RUN_ID" --repo insightos-community/ruckig --name musl-dist --dir downloaded-dist
```

## Reproduction evidence

Build in a fresh checkout and a separate output directory for each ABI. Preserve
source commits, compiler/tool versions, dependency locks, package inventories and
test logs. Fixed source revisions and a container digest reproduce the recipe;
unlocked OS packages, runner images, timestamps and build tools can still change
archive bytes. Compare a downloaded release against its published `SHA256SUMS`;
do not expect a local rebuild to have the same digest.

See the [complete installer and repository index](https://github.com/insightos-community/quick-start/blob/main/README.build.md) for assembly order,
platform locks and end-to-end validation. Local build commands do not publish a
Release. Publishing requires repository write access and a new version tag;
existing release tags/assets should not be replaced.
