"""Repair known startup baseline failures in a staged copy, never in the source."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


def repair_demo(path):
    path = pathlib.Path(path).resolve()
    base = pathlib.Path(getattr(sys, '_MEIPASS', pathlib.Path(__file__).resolve().parent))
    vendor = base / 'vendor' / 'demo-fixer'
    # QuickJS's Windows stdio uses narrow paths. Relative ASCII filenames inside
    # a Unicode-capable process cwd avoid breaking non-Latin Windows accounts.
    with tempfile.TemporaryDirectory(prefix='.voice-repair-', dir=path.parent) as directory:
        work = pathlib.Path(directory)
        for name in ('demofix.js', 'run.js'):
            shutil.copyfile(vendor / name, work / name)
        try:
            os.link(path, work / 'input.dem')
        except OSError:
            shutil.copyfile(path, work / 'input.dem')
        output = work / 'output.dem'
        try:
            proc = subprocess.run(
                [str(vendor / 'qjs.exe'), '--std', '-I', 'demofix.js',
                 '-C', 'run.js', 'input.dem', 'output.dem'], cwd=work,
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('Проверка демки превысила 3 минуты. Исходный файл сохранён.') from exc
        if proc.returncode:
            raise RuntimeError('Не удалось проверить или исправить демку: ' + proc.stderr[-500:].strip())
        report = json.loads(proc.stdout)
        if report['changed']:
            if not output.is_file() or output.stat().st_size != report['outSize']:
                raise RuntimeError('Исправленная демка записана не полностью.')
            output.replace(path)
        return report
