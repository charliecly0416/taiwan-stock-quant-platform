"""Build the pinned Taiwan Qlib source into a new isolated wheel directory."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tarfile

COMMIT = 'a4179eed3d32fd21c296345fb3fba14f3e01cdaa'
VERSION = '0.9.8.dev31'
SOURCE_FILES = ['qlib', 'setup.py', 'pyproject.toml', 'README.md', 'LICENSE', 'MANIFEST.in']
BUILD_REQUIREMENTS = ['pip==25.1.1', 'setuptools==84.0.0', 'wheel==0.48.0',
                      'Cython==3.3.0', 'numpy==2.5.3', 'setuptools-scm==10.3.4', 'packaging==26.3']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13) or platform.system() != 'Linux':
        parser.error('the audited runtime is CPython 3.13 on Linux')
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    source = out / 'source'; source.mkdir()
    archive = out / 'source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(args.source), 'archive', COMMIT, *SOURCE_FILES],
                       stdout=stream, check=True)
    with tarfile.open(archive) as bundle:
        bundle.extractall(source, filter='data')
    epoch = subprocess.check_output(['git', '-C', str(args.source), 'show', '-s', '--format=%ct', COMMIT], text=True).strip()
    os.environ['SOURCE_DATE_EPOCH'] = epoch
    os.environ['PYTHONHASHSEED'] = '0'
    os.environ['SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYQLIB'] = VERSION
    os.environ['CFLAGS'] = '-g0 -ffile-prefix-map=' + str(source) + '=/qlib-source'
    os.environ['CXXFLAGS'] = os.environ['CFLAGS']
    buildenv = out / 'buildenv'; wheels = out / 'wheels'; wheels.mkdir()
    subprocess.run([sys.executable, '-m', 'venv', str(buildenv)], check=True)
    python = str(buildenv / 'bin/python')
    with (out / 'build.log').open('w') as log:
        for command in ([python, '-m', 'pip', '--isolated', 'install', '--index-url', 'https://pypi.org/simple', *BUILD_REQUIREMENTS],
                        [python, '-m', 'pip', '--isolated', 'wheel', '--no-index', '--no-deps', '--no-build-isolation',
                         '--wheel-dir', str(wheels), str(source)]):
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    files = list(wheels.glob('*.whl'))
    if len(files) != 1: raise ValueError('expected exactly one Qlib wheel')
    wheel = files[0]
    report = {'commit': COMMIT, 'version': VERSION, 'source_date_epoch': epoch,
              'source_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'wheel': wheel.name, 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
              'python': platform.python_version(), 'platform': platform.platform(),
              'build_requirements': BUILD_REQUIREMENTS, 'source_allowlist': SOURCE_FILES}
    (wheels / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__': raise SystemExit(main())
