"""Print CS2 voice commands for a FACEIT .dem or .dem.zst replay.

Usage: python faceit_voice.py "G:\\match.dem.zst"
With no path, the script prompts for one.
"""
from __future__ import annotations

import argparse
import importlib
import pathlib
import subprocess
import sys
import tempfile


def load_parser(status=lambda message: None):
    frozen = getattr(sys, "frozen", False)
    if not frozen:
        deps = pathlib.Path(__file__).resolve().with_name(".faceit_voice_deps")
        sys.path.insert(0, str(deps))
    try:
        import zstandard
        from demoparser2 import DemoParser
    except ImportError:
        if frozen:
            raise RuntimeError("В сборке отсутствует библиотека для чтения демки")
        status("Первый запуск: устанавливаю библиотеки...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--target", str(deps),
             "zstandard>=0.23,<1", "demoparser2>=0.42,<1"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode:
            raise RuntimeError("Не удалось установить библиотеки: " + (result.stderr or result.stdout)[-800:])
        importlib.invalidate_caches()
        import zstandard
        from demoparser2 import DemoParser
    return zstandard, DemoParser


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

    zstandard, DemoParser = load_parser(status)
    temporary = None
    try:
        if demo.name.lower().endswith(".zst"):
            status("Распаковываю демку...")
            with tempfile.NamedTemporaryFile(suffix=".dem", delete=False) as dst, demo.open("rb") as src:
                temporary = pathlib.Path(dst.name)
                with zstandard.ZstdDecompressor().stream_reader(src) as reader:
                    while chunk := reader.read(4 * 1024 * 1024):
                        dst.write(chunk)
            parse_path = temporary
        else:
            parse_path = demo

        status("Читаю игроков и слоты...")
        parser = DemoParser(str(parse_path))
        header = parser.parse_header()
        info = parser.parse_player_info()
        expected = len(info)
        ticks = list(range(1000, 31000, 1000)) + list(range(40000, 250001, 10000))
        frame = parser.parse_ticks(["user_id", "team_num"], ticks=ticks)
        frame = frame[frame["team_num"].isin([2, 3]) & frame["user_id"].notna()]
        if frame.empty:
            raise ValueError("В демке не удалось прочитать игроков и их слоты")
        counts = frame.groupby("tick")["steamid"].nunique()
        best = int(counts[counts == counts.max()].index.min())
        rows = frame[frame["tick"] == best].drop_duplicates("steamid")
        roster = [
            {"name": str(row["name"]), "steamid": str(int(row["steamid"])),
             "user_id": int(row["user_id"]), "team": int(row["team_num"])}
            for _, row in rows.iterrows()
        ]
        roster.sort(key=lambda p: p["user_id"])
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
        return {"map": header.get("map_name", "?"), "tick": best,
                "found": len(roster), "expected": expected, "groups": groups}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


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
