"""Print CS2 voice commands for a FACEIT .dem or .dem.zst replay.

Usage: python faceit_voice.py "G:\\match.dem.zst"
With no path, the script prompts for one.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys


def parser_executable() -> pathlib.Path:
    if getattr(sys, "frozen", False):
        path = pathlib.Path(sys._MEIPASS) / "faceit_voice_parser.exe"
    else:
        base = pathlib.Path(__file__).resolve().parent
        path = base / "faceit_voice_parser.exe"
        if not path.is_file():
            path = base / "parser" / "target" / "release" / "faceit_voice_parser.exe"
    if not path.is_file():
        raise RuntimeError("Нативный парсер не найден. Запустите build.ps1 для сборки.")
    return path


def signed_32(value: int) -> int:
    return value if value < 2**31 else value - 2**32


def commands(players: list[dict]) -> tuple[int, int]:
    low = high = 0
    for player in players:
        slot = int(player["user_id"])
        if not 0 <= slot < 64:
            raise ValueError(f"Некорректный слот {slot}")
        if slot < 32:
            low |= 1 << slot
        else:
            high |= 1 << (slot - 32)
    return signed_32(low), signed_32(high)


def analyze_demo(raw_path: str, status=lambda message: None) -> dict:
    demo = pathlib.Path(raw_path.strip().strip('"').strip("'"))
    if not demo.is_file():
        raise ValueError(f"Файл не найден: {demo}")
    if not (demo.name.lower().endswith(".dem.zst") or demo.suffix.lower() == ".dem"):
        raise ValueError("Нужен файл .dem либо .dem.zst")

    status("Читаю игроков и слоты...")
    proc = subprocess.run(
        [str(parser_executable()), str(demo)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode:
        raise RuntimeError("Не удалось прочитать демку: " + proc.stderr[-1000:])
    data = json.loads(proc.stdout)
    roster = data["players"]
    if not roster:
        raise ValueError("В демке не удалось прочитать игроков и их слоты")
    groups = []
    for number, team in enumerate((2, 3), start=1):
        group = [p for p in roster if p["team"] == team]
        if group:
            low, high = commands(group)
            groups.append({
                "number": number,
                "players": group,
                "command": f"tv_listen_voice_indices {low}; tv_listen_voice_indices_h {high}",
            })
    return {"map": data.get("map") or "?", "tick": data["tick"],
            "found": len(roster), "expected": max(10, len(roster)), "groups": groups}


def main() -> int:
    ap = argparse.ArgumentParser(description="Готовые команды для голосов в FACEIT-демке CS2")
    ap.add_argument("demo", nargs="?", help="путь к .dem или .dem.zst")
    args = ap.parse_args()
    raw_path = args.demo or input("Путь к демке (.dem.zst или .dem): ")
    result = analyze_demo(raw_path, status=print)
    if result["found"] < result["expected"]:
        print(f"Внимание: найдены {result['found']} из {result['expected']} игроков.")
    print(f"Карта: {result['map']}; игроков: {result['found']}; тик: {result['tick']}")
    for group in result["groups"]:
        names = ", ".join(f"{p['name']} (spec_player {p['user_id'] + 1})" for p in group["players"])
        print(f"\nКоманда {group['number']}: {names}")
        print(group["command"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        sys.exit(1)
