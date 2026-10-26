# FACEIT Voice

Программа для Windows, которая читает демки CS2 с FACEIT, создаёт команды для прослушивания игроков и сохраняет их голоса в аудиодорожки.

## Скачать и запустить

1. Открой [последний релиз](https://github.com/Imagisty/faceit-voice/releases/latest).
2. В разделе **Assets** скачай **FACEIT-Voice.exe**.
3. Запусти **FACEIT-Voice.exe**. Поддерживаются Windows 10/11 x64.
4. Нажми **Выбрать файл** и укажи демку `.dem.zst` или `.dem`. После выбора она разберётся автоматически. Также можно вставить путь и нажать **Разобрать демку**.

## Что умеет

- Показывает игроков, ники и составы двух команд.
- Создаёт консольную команду для прослушивания одной команды или любых выбранных игроков.
- Позволяет выбрать всех игроков, сбросить выбор и включать голоса по одному.
- Извлекает голосовые записи в отдельные аудиодорожки `.opus` с никами игроков в названиях файлов.
- Позволяет выбрать папку для сохранения аудио.
- Читает как обычные `.dem`, так и сжатые `.dem.zst`.

## Слушать голоса в CS2

Нажми **Копировать команду** под нужным составом. Для произвольного набора включи переключатели рядом с никами и нажми **Копировать команду** справа.

Открой эту демку в CS2 и вставь скопированную строку в консоль. Она задаёт оба параметра: `tv_listen_voice_indices` и `tv_listen_voice_indices_h`. Значение второго параметра `0` нормально для игроков со слотами 0–31.

Для `playdemo` в CS2 нужен распакованный `.dem`. Приложение может прочитать `.dem.zst` напрямую.

## Сохранить аудиодорожки

1. Разбери демку и выбери игроков переключателями. Для целой команды нажми **Выбрать** над её списком.
2. В блоке **Аудиодорожки** нажми **Выбрать папку**.
3. Нажми **Сохранить аудио**.
4. В выбранной папке появится новая подпапка `FACEIT-Voice-…` с файлами `ник_SteamID.opus`.

Каждый файл содержит голос одного игрока. Реплики склеены подряд без пауз между ними: это компактная запись речи, без привязки ко времени демки. Дорожки разных игроков не смешиваются; звуки игры в них не входят. Формат — Ogg/Opus, без повторного кодирования. Для прослушивания подойдёт плеер с поддержкой Opus, например VLC.

Экспорт работает, только если голосовые записи есть в самой демке. Если игрок молчал или его голос не записан, приложение сообщит об этом. Каждый экспорт создаёт новую подпапку и не перезаписывает предыдущие записи.

## Запуск из исходников и сборка

Нужны Python 3.12+ и Rust с инструментами сборки для Windows.

```powershell
cargo build --release --manifest-path parser\Cargo.toml
python faceit_voice_gui.pyw
```

Сборка единого EXE:

```powershell
.\build.ps1
```

Результат: `dist\FACEIT-Voice.exe`.

---

## English

FACEIT Voice is a Windows application that reads FACEIT CS2 demos, generates voice playback commands, and exports players' voice recordings to audio tracks.

### Download and run

1. Open the [latest release](https://github.com/Imagisty/faceit-voice/releases/latest).
2. Download **FACEIT-Voice.exe** from **Assets**.
3. Run **FACEIT-Voice.exe**. Windows 10/11 x64 is supported.
4. Click **Выбрать файл** (Choose file) and select a `.dem.zst` or `.dem` demo. It will be parsed automatically. You can also paste a path and click **Разобрать демку** (Parse demo).

### Features

- Two team rosters with player names and individual voice switches.
- Console commands for an entire team or any selection of players.
- Select all and clear selection controls.
- Voice extraction to separate `.opus` tracks named after each player.
- An audio output folder picker.
- Support for both `.dem` and compressed `.dem.zst` files.

### Listen in CS2

Click **Копировать команду** (Copy command) under a team roster, or select individual players and use the copy button on the right. Play the same demo in CS2 and paste the command into the developer console.

Each command sets both `tv_listen_voice_indices` and `tv_listen_voice_indices_h`. The second value being `0` is normal when the selected voice slots are below 32. CS2's `playdemo` requires an unpacked `.dem`; the app itself can read `.dem.zst` directly.

### Export voice tracks

1. Parse a demo and select players. Use **Выбрать** (Select) above a roster to select a whole team.
2. Click **Выбрать папку** (Choose folder) in the audio section.
3. Click **Сохранить аудио** (Save audio).
4. Open the new `FACEIT-Voice-…` subfolder inside your selected folder. Files are named `nickname_SteamID.opus`.

Each file contains one player's speech, concatenated without gaps between transmissions. Demo timing is not preserved. Players are not mixed together, and game sounds are not included. Tracks use the Ogg/Opus format without re-encoding; open them with an Opus-compatible player such as VLC.

The demo must contain voice recordings. Players without recorded speech are reported. Every export creates a new subfolder and preserves previous exports.

### Run from source and build

Install Python 3.12+ and Rust with Windows build tools:

```powershell
cargo build --release --manifest-path parser\Cargo.toml
python faceit_voice_gui.pyw
```

Run `build.ps1` to create `dist\FACEIT-Voice.exe`.

---

MIT License. Неофициальный проект, не связан с FACEIT или Valve. Unofficial project, not affiliated with FACEIT or Valve. See [third-party notices](THIRD_PARTY_NOTICES.md).
