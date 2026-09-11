#!/bin/sh
set -eu
cd /work
mkdir -p logs artifacts/raw artifacts/wheels build prefix dist
exec >logs/build.log 2>&1
date -u
apk add --no-cache build-base cmake ninja git linux-headers patchelf binutils
git config --global --add safe.directory '*'
export PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
export CMAKE_BUILD_PARALLEL_LEVEL=2
python -m pip install -r /src/ci/musl/build-requirements.txt
python -m pip install --only-binary=:all: numpy==2.3.5 pytest==8.3.5
python -m pip freeze > logs/python-packages.txt
apk info -v > logs/apk-packages.txt
python -m pip wheel --no-deps --no-build-isolation /src \
  --wheel-dir artifacts/raw -Cbuild-dir=/work/build/wheel \
  -Ccmake.define.BUILD_EXAMPLES=OFF -Ccmake.define.BUILD_TESTS=OFF > logs/wheel-build.log 2>&1
auditwheel show artifacts/raw/*.whl > logs/auditwheel-before.log 2>&1
auditwheel repair --plat musllinux_1_2_x86_64 --wheel-dir artifacts/wheels artifacts/raw/*.whl > logs/auditwheel-repair.log 2>&1
auditwheel show artifacts/wheels/*.whl > logs/auditwheel-after.log 2>&1
cmake -S /src -B build/cpp -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/work/prefix \
  -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF -DBUILD_PYTHON_MODULE=OFF \
  -DBUILD_SHARED_LIBS=ON > logs/cpp-configure.log 2>&1
cmake --build build/cpp --parallel 2 > logs/cpp-build.log 2>&1
cmake --install build/cpp > logs/cpp-install.log 2>&1
ctest --test-dir build/cpp --output-on-failure --timeout 600 -V > logs/cpp-tests.log 2>&1
python -m pip install --no-index --no-deps artifacts/wheels/*.whl > logs/wheel-install.log 2>&1
python -m pytest -p no:cacheprovider -q /src/ci/musl/test_runtime.py > logs/python-tests.log 2>&1
python /src/ci/musl/package.py
echo BUILD_AND_TEST_COMPLETE
date -u
