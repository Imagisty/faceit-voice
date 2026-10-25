# FACEIT Voice

Windows app that reads a Counter-Strike 2 FACEIT demo and generates console commands for listening to either team or any selection of players. The demo is parsed locally; there is no upload or account connection.

![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078d4) ![License](https://img.shields.io/badge/license-MIT-orange)

## Download

Get **`FACEIT-Voice.exe`** from the [latest release](https://github.com/Imagisty/faceit-voice/releases/latest). It is a standalone Windows x64 executable; Python is not required.

## Use

1. Download a match demo from the FACEIT matchroom (`.dem.zst`) or use an unpacked `.dem` file.
2. Open `FACEIT-Voice.exe`, select the demo, and click **Разобрать демку**.
3. Copy the line for **Команда 1** or **Команда 2**. To hear specific players, switch **Слушать** to **Да** for them and copy the command under **Выбранные игроки**.
4. Play the demo in CS2 and paste the copied line into the developer console.

Each copied line sets both `tv_listen_voice_indices` and `tv_listen_voice_indices_h`. The second value is normally `0` in a 5v5 match because those players use slots below 33.

The app can read `.dem.zst` directly to calculate the commands. CS2 itself needs an unpacked `.dem` file for `playdemo`. Voice must be present in the demo; FACEIT SourceTV demos normally contain it, while Valve matchmaking and Premier demos do not. The app generates playback commands; it does not export audio.

## По-русски

Скачай `FACEIT-Voice.exe` из [последнего релиза](https://github.com/Imagisty/faceit-voice/releases/latest), открой демку FACEIT (`.dem.zst` или `.dem`) и нажми **Разобрать демку**. В окне появятся две готовые команды для команд матча и список игроков. Переключай **Слушать: Да/Нет**, чтобы собрать команду для любых игроков. Скопированную строку вставь в консоль CS2 при просмотре демки.

Программа читает файл локально и не требует аккаунта FACEIT или установленного Python. Для просмотра через `playdemo` архив `.dem.zst` нужно отдельно распаковать в `.dem`.

## Run from source

Python 3.12+ is recommended:

```powershell
python faceit_voice_gui.pyw
```

On first source run, required Python packages are installed into `.faceit_voice_deps` next to the script. For a command-line version:

```powershell
python faceit_voice.py "C:\path\to\match.dem.zst"
```

## Build the executable

Run `build.ps1` on Windows with Python 3.12. It creates `dist\FACEIT-Voice.exe` with PyInstaller. Package versions are pinned in `requirements-build.txt`. The build includes PyArrow and Polars because `demoparser2` loads them at runtime.

## Privacy and attribution

All demo parsing happens on your PC. A compressed demo is unpacked into a temporary file and removed after parsing. This project is unofficial and is not affiliated with FACEIT, Valve, or Counter-Strike. Third-party packages used by the executable are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Licensed under [MIT](LICENSE).
