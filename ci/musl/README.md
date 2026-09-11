# InsightOS musl build of Ruckig 0.19.4

This fork's `insightos/musl` branch maintains upstream **v0.19.4** with a musl build/release pipeline. Ruckig's source is unchanged; upstream branches remain available.

## Release assets

- `ruckig-0.19.4-cp313-cp313-musllinux_1_2_x86_64.whl`: CPython 3.13, x86_64, musl 1.2+.
- `ruckig-0.19.4-musl-x86_64-cpp.tar.gz`: C++ shared library, headers, CMake files, license and build manifest.
- `build-manifest.json` and `SHA256SUMS`.

Install the wheel using a musl Python interpreter:

```sh
python -m pip install --no-index --no-deps ./ruckig-0.19.4-cp313-cp313-musllinux_1_2_x86_64.whl
```

Ruckig's core is statically linked into the extension. `auditwheel repair` bundles the required C++ runtime libraries, validates the `musllinux_1_2_x86_64` tag, and the packaging check rejects GLIBC symbol requirements. The system's musl is still required. This wheel cannot be loaded by glibc Python. NumPy is used for testing, not required by Ruckig itself.

## Build and validation

The `Musl build and release` workflow runs on a standard GitHub `ubuntu-24.04` runner inside a digest-pinned Python 3.13 Alpine container. It builds from this repository's checked-out source, not an upstream prebuilt wheel.

CI runs the upstream C++ test suite (locally: 15 cases and 1,441,973 assertions), Python trajectory checks for 1/3/14 DOFs and online updates, and a clean Python-container install with networking disabled. Speed, acceleration, jerk and final state are checked. The original cloud-client compile option is retained; these tests calculate local start-to-target trajectories.

From the repository root, use an empty build directory:

```sh
musl_work=$(mktemp -d)
docker run --rm --cpus=2 --memory=12g --memory-swap=12g \
  --mount "type=bind,src=$PWD,dst=/src,readonly" \
  --mount "type=bind,src=$musl_work,dst=/work" \
  python:3.13-alpine3.23@sha256:75f27d686432419c9d42420b2b9ef605868c7a0682a6be10a6601fad46c2df01 \
  sh /src/ci/musl/build.sh
```

The workflow also verifies installation in a second, clean container. Build requirements are pinned in `build-requirements.txt`; installed Python/APK versions and test logs are saved as Actions artifacts. Transitive build dependencies are recorded but not fully locked.

Pushes and PRs to `insightos/musl`, plus manual dispatches, upload build artifacts. Tags matching `musl-v0.19.4-*` publish Releases after every check succeeds:

```sh
git tag -a musl-v0.19.4-1 -m 'Ruckig 0.19.4 musl build 1'
git push origin musl-v0.19.4-1
```

Upstream tags are preserved. Published release assets are not replaced by reruns; use a new build tag. An incomplete draft upload can be retried.

The earlier local experiment also passed Robot SDK trajectory checks and a shared-process check with musl Pinocchio 3.9.0 and NumPy 2.3.5. This repository's CI stays independent of those other repositories and does not claim full installer or scene-task validation.
