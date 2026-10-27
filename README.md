# FACEIT Voice

Программа для Windows, которая читает демки CS2 с FACEIT, создаёт команды для прослушивания игроков и сохраняет их голоса в аудиодорожки.

## Скачать и запустить

1. Открой [последний релиз](https://github.com/Imagisty/faceit-voice/releases/latest).
2. В разделе **Assets** скачай **FACEIT-Voice.exe**.
3. Запусти **FACEIT-Voice.exe**. Поддерживаются Windows 10/11 x64.
4. Перетащи демку `.dem.zst` или `.dem` из Проводника в окно программы — она разберётся автоматически. Также можно нажать **Выбрать файл** или вставить путь и нажать **Разобрать демку**.

## Что умеет

- Показывает игроков, ники и составы двух команд.
- Создаёт консольную команду для прослушивания одной команды или любых выбранных игроков.
- Позволяет выбрать всех игроков, сбросить выбор и включать голоса по одному.
- Извлекает голосовые записи в отдельные аудиодорожки `.opus` с никами игроков в названиях файлов.
- Позволяет выбрать папку для сохранения аудио.
- Читает как обычные `.dem`, так и сжатые `.dem.zst`.
- Принимает демки перетаскиванием из Проводника.
- Добавляет демку в папку CS2 под выбранным названием и копирует команду запуска.

## Слушать голоса в CS2

Нажми **Копировать команду** под нужным составом. Для произвольного набора включи переключатели рядом с никами и нажми **Копировать команду** справа.

Открой эту демку в CS2 и вставь скопированную строку в консоль. Она задаёт оба параметра: `tv_listen_voice_indices` и `tv_listen_voice_indices_h`. Значение второго параметра `0` нормально для игроков со слотами 0–31.

## Добавить демку в игру

1. Выбери или перетащи демку в окно.
2. Нажми **Добавить в CS2** и введи название.
3. Программа найдёт установленную CS2 и сохранит файл `.dem` в `game\csgo`. Архив `.dem.zst` распакуется автоматически. Если папка игры не найдена, программа предложит указать её.
4. Команда `playdemo "название"` скопируется в буфер. Вставь её в консоль CS2.

Исходный файл сохраняется. Если название уже занято, программа предложит другое и не перезапишет существующую демку.

Папка и способ запуска соответствуют [инструкции FACEIT](https://support.faceit.com/hc/en-us/articles/10622392832412-How-to-download-and-watch-a-CS2-demo).

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
4. Drag a `.dem.zst` or `.dem` file from File Explorer into the app to parse it automatically. You can also click **Выбрать файл** (Choose file), or paste a path and click **Разобрать демку** (Parse demo).

### Features

- Two team rosters with player names and individual voice switches.
- Console commands for an entire team or any selection of players.
- Select all and clear selection controls.
- Voice extraction to separate `.opus` tracks named after each player.
- An audio output folder picker.
- Support for both `.dem` and compressed `.dem.zst` files.
- Drag-and-drop demo loading from File Explorer.
- Copy demos into CS2 with a custom name and get the playback command.

### Listen in CS2

Click **Копировать команду** (Copy command) under a team roster, or select individual players and use the copy button on the right. Play the same demo in CS2 and paste the command into the developer console.

Each command sets both `tv_listen_voice_indices` and `tv_listen_voice_indices_h`. The second value being `0` is normal when the selected voice slots are below 32.

### Add a demo to CS2

1. Select or drop a demo into the app.
2. Click **Добавить в CS2** (Add to CS2) and enter a name.
3. The app locates CS2 and saves the `.dem` file under `game\csgo`, automatically unpacking `.dem.zst` files. If CS2 cannot be found, choose the game folder manually.
4. The command `playdemo "name"` is copied to your clipboard. Paste it into the CS2 console.

The original file is preserved. Existing demos are not overwritten; choose a different name if it is already in use.

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
