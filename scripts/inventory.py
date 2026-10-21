#!/usr/bin/env python3
"""Index source metadata without importing or executing project code."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

SKIP = {'node_modules', '.git', '.venv', 'venv', '__pycache__', 'dist', 'build', '.next', '.pytest_cache'}
EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}


def inventory(root):
    records = []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if any(part in SKIP or part.startswith('.') for part in rel.parts) or path.is_symlink():
            continue
        if path.suffix not in EXTENSIONS or not path.is_file():
            continue
        if any(term in path.name.lower() for term in ('credential', 'secret', 'serviceaccount')):
            continue
        data = path.read_bytes()
        entry = {'file': rel.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(),
                 'lines': len(data.splitlines()), 'status': 'indexed-not-semantically-reviewed'}
        if path.suffix == '.py':
            try:
                tree = ast.parse(data.decode('utf-8-sig'))
                entry['symbols'] = [{'name': n.name, 'line': n.lineno, 'end_line': n.end_lineno}
                                    for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                entry['branches'] = sum(isinstance(n, (ast.If, ast.Try, ast.Match)) for n in ast.walk(tree))
            except (SyntaxError, UnicodeDecodeError) as exc:
                entry['parse_error'] = type(exc).__name__
        records.append(entry)
    return {'scope': 'Source metadata only; indexing is not semantic inspection.', 'files': records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'Indexed {len(result["files"])} source files.')
