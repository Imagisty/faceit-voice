"""Locate CS2 and copy/decompress a replay without replacing existing demos."""
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

from faceit_voice import parser_executable


def csgo_directory(path):
    base = pathlib.Path(path)
    for directory in (base / "game" / "csgo", base / "csgo", base):
        if directory.name.lower() == "csgo" and directory.is_dir() and (directory.parent / "bin" / "win64" / "cs2.exe").is_file():
            return directory.resolve()
    return None


def find_cs2():
    roots = []
    if os.name == "nt":
        import winreg
        for hive, key, name in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        ):
            try:
                with winreg.OpenKey(hive, key) as handle:
                    roots.append(pathlib.Path(winreg.QueryValueEx(handle, name)[0]))
            except OSError:
                pass
    roots.append(pathlib.Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam")
    libraries = list(roots)
    for root in roots:
        try:
            text = (root / "steamapps" / "libraryfolders.vdf").read_text(encoding="utf-8")
            libraries.extend(pathlib.Path(value.replace("\\\\", "\\"))
                             for value in re.findall(r'"path"\s*"([^"\r\n]+)"', text))
        except (OSError, UnicodeError):
            pass
    for library in dict.fromkeys(libraries):
        install_name = "Counter-Strike Global Offensive"
        try:
            text = (library / "steamapps" / "appmanifest_730.acf").read_text(encoding="utf-8")
            match = re.search(r'"installdir"\s*"([^"\r\n]+)"', text)
            if match:
                install_name = match.group(1)
        except (OSError, UnicodeError):
            pass
        directory = csgo_directory(library / "steamapps" / "common" / install_name)
        if directory:
            return directory
    return None


def demo_name(value):
    name = value.strip()
    if name.lower().endswith(".dem"):
        name = name[:-4].strip()
    if not name or len(name) > 80 or not re.fullmatch(r"[\w -]+", name):
        raise ValueError("В названии допустимы буквы, цифры, пробелы, дефис и подчёркивание (до 80 символов).")
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", name, re.I):
        raise ValueError("Это имя зарезервировано Windows. Выберите другое название.")
    return name


def install_demo(source, game_directory, name):
    name = demo_name(name)
    source = pathlib.Path(source).resolve()
    game = csgo_directory(game_directory)
    if game is None:
        raise ValueError("Не найдена папка CS2. Укажите папку Counter-Strike Global Offensive.")
    if not source.is_file() or not (source.name.lower().endswith(".dem.zst") or source.suffix.lower() == ".dem"):
        raise ValueError("Выберите файл .dem или .dem.zst.")
    destination = game / (name + ".dem")
    command = f'playdemo "{name}"'
    if source == destination.resolve():
        return {"file": str(destination), "command": command}
    if destination.exists():
        raise FileExistsError(f"Демка {name}.dem уже есть в игре. Выберите другое название.")
    destination.parent.mkdir(exist_ok=True)
    # Stage on the destination volume, so no incomplete .dem becomes visible.
    staging = pathlib.Path(tempfile.mkdtemp(prefix=".faceit-import-", dir=destination.parent))
    temporary = staging / "replay.dem"
    try:
        if source.name.lower().endswith(".zst"):
            proc = subprocess.run([str(parser_executable()), "--unpack", str(source), str(temporary)],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if proc.returncode:
                raise RuntimeError("Не удалось распаковать демку: " + proc.stderr[-600:])
        else:
            shutil.copyfile(source, temporary)
        with temporary.open("rb") as stream:
            if stream.read(8) != b"PBDEMS2\0":
                raise ValueError("Файл не является демкой CS2.")
        # Windows rename fails if a file appeared at this name in the meantime.
        temporary.rename(destination)
        return {"file": str(destination), "command": command}
    finally:
        temporary.unlink(missing_ok=True)
        staging.rmdir()
