#!/usr/bin/env python3
"""Fetch pinned public source ZIPs with retries; refuse changed content."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from pathlib import Path
import subprocess
import sys

from audit_individual_rivers import sources


def fetch(source, directory):
    dest = directory / source['source_url'].rsplit('/', 1)[-1]
    expected = source['checksum_sha256']
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == expected:
        return source['region'], source['group'], dest.stat().st_size
    temp = dest.with_suffix('.part')
    for attempt in range(4):
        result = subprocess.run([
            'curl', '--fail', '--location', '--silent', '--show-error',
            '--max-time', '300', '--retry', '2', '--retry-delay', '2',
            source['source_url'], '-o', str(temp),
        ], capture_output=True, text=True)
        if result.returncode == 0 and temp.exists() and hashlib.sha256(temp.read_bytes()).hexdigest() == expected:
            temp.replace(dest)
            return source['region'], source['group'], dest.stat().st_size
        print('RETRY', source['region'], source['group'], attempt + 1,
              result.stderr[-200:], flush=True)
    raise ValueError('Official archive unavailable or SHA mismatch: ' + source['source_url'])


if __name__ == '__main__':
    directory = Path(sys.argv[1]); directory.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch, s, directory) for s in sources()]
        failures = []
        for future in as_completed(futures):
            try:
                print('SOURCE_OK', *future.result(), flush=True)
            except Exception as exc:
                failures.append(str(exc)); print('SOURCE_FAILED', exc, flush=True)
    if failures:
        raise SystemExit(f'{len(failures)} pinned sources unavailable')
