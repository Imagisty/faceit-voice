# FACEIT Voice

Windows app that reads a Counter-Strike 2 FACEIT demo and generates console commands for listening to either team or any selection of players. The demo is parsed locally; there is no upload or account connection.

![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078d4) ![License](https://img.shields.io/badge/license-MIT-orange)

## Download

Get **`FACEIT-Voice.exe`** from the [latest release](https://github.com/Imagisty/faceit-voice/releases/latest). It is a standalone Windows x64 executable; Python is not required.

## Use

1. Download a match demo from the FACEIT matchroom (`.dem.zst`) or use an unpacked `.dem` file.
2. Open `FACEIT-Voice.exe`, select the demo, and click **Разобрать демку**.
3. Click **Копировать команду** below either team roster. To hear specific players, turn on their switches and click **Копировать микс** in the right panel. **Выбрать всех** selects the full match roster; **Сбросить** clears the selection.
4. Play the demo in CS2 and paste the copied line into the developer console.

Each copied line sets both `tv_listen_voice_indices` and `tv_listen_voice_indices_h`. The second value is normally `0` in a 5v5 match because those players use slots below 33.

The app can read `.dem.zst` directly to calculate the commands. CS2 itself needs an unpacked `.dem` file for `playdemo`. Voice must be present in the demo; FACEIT SourceTV demos normally contain it, while Valve matchmaking and Premier demos do not. The app generates playback commands; it does not export audio.

## По-русски

Скачай `FACEIT-Voice.exe` из [последнего релиза](https://github.com/Imagisty/faceit-voice/releases/latest), открой демку FACEIT (`.dem.zst` или `.dem`) и нажми **Разобрать демку**. Игроки появятся в двух колонках. Нажми **Копировать команду** под нужным составом или включи переключатели конкретных игроков и нажми **Копировать микс** справа. Скопированную строку вставь в консоль CS2 при просмотре демки.

Программа читает файл локально и не требует аккаунта FACEIT или установленного Python. Для просмотра через `playdemo` архив `.dem.zst` нужно отдельно распаковать в `.dem`.

## Run from source

Install Python 3.12+ and Rust, then build the parser once:

```powershell
cargo build --release --manifest-path parser\Cargo.toml
python faceit_voice_gui.pyw
```

For a command-line version:

```powershell
python faceit_voice.py "C:\path\to\match.dem.zst"
```

## Build the executable

Run `build.ps1` on Windows with Python 3.12 and Rust. It builds the small Rust demo parser and packages it with the Tkinter GUI into `dist\FACEIT-Voice.exe`. The build only needs PyInstaller from `requirements-build.txt`.

## Privacy and attribution

All demo parsing happens on your PC. A compressed demo is unpacked into a temporary file and removed after parsing. This project is unofficial and is not affiliated with FACEIT, Valve, or Counter-Strike. Third-party packages used by the executable are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Licensed under [MIT](LICENSE).
