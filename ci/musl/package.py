"""Audit every ELF in the repaired wheel and package C++ and Python assets."""
import hashlib
import json
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

work = Path('/work')
dist = work / 'dist'
wheel = next((work / 'artifacts/wheels').glob('*.whl'))
rows = []
with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        data = archive.read(name)
        if data[:4] != b'\x7fELF':
            continue
        path = Path(tmp) / 'elf'
        path.write_bytes(data)
        versions = subprocess.check_output(['readelf', '--version-info', str(path)], text=True)
        dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
        rows.append({'path': name, 'glibc_versions': sorted(set(re.findall(r'\bGLIBC_[0-9.]+', versions))), 'needed': re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic)})
assert rows and all(not row['glibc_versions'] for row in rows), 'Unexpected GLIBC symbols'
manifest = {
    'project': 'ruckig', 'version': '0.19.4', 'python': platform.python_version(),
    'platform': 'musllinux_1_2_x86_64',
    'source_commit': subprocess.check_output(['git', '-C', '/src', 'rev-parse', 'HEAD'], text=True).strip(),
    'wheel_core_linkage': 'static', 'cpp_library_linkage': 'shared', 'cloud_client': True,
    'elf_audit': rows, 'tests': 'upstream C++ suite and 1/3/14-DOF Python trajectory checks',
}
(dist / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
shutil.copy2(wheel, dist / wheel.name)
cpp = dist / 'ruckig-0.19.4-musl-x86_64-cpp.tar.gz'
with tarfile.open(cpp, 'w:gz') as archive:
    archive.add(work / 'prefix', arcname='prefix')
    archive.add('/src/LICENSE', arcname='LICENSE')
    archive.add(dist / 'build-manifest.json', arcname='build-manifest.json')
shutil.copy2('/src/ci/musl/README.md', dist / 'RELEASE_NOTES.md')
paths = [dist / wheel.name, cpp, dist / 'build-manifest.json']
(dist / 'SHA256SUMS').write_text(''.join(f'{hashlib.file_digest(p.open("rb"), "sha256").hexdigest()}  {p.name}\n' for p in paths))
