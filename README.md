# DMEDoc (PREVIEW)

English | [Français](README.fr.md)

**Read-only** diagnostic tool for BMW **MS42** (Siemens) engine ECUs, built to answer one question: *why doesn't this ECU work?*

> ⚠️ **Preview, never tested on a real ECU.** The DS2 frames are written from community documentation and unit tests, not validated on hardware. Test feedback is welcome (open an issue with the output of `check`).

## What it does

| Feature | Purpose | Hardware |
|---|---|---|
| **Diagnose the ECU** (`dmedoc check --port COM3`) | Queries the ECU over DS2 (identification + fault memory) and explains the likely causes if it doesn't answer | USB K-line cable, powered ECU |
| **Analyse a .bin** (`dmedoc bin file.bin`) | Checks a dump: size, erased areas (0xFF), possible part numbers, fingerprints | None |
| **Compare two .bin** (`dmedoc diff a.bin b.bin`) | Compares two dumps (e.g. dead ECU vs a known-good file) | None |

## What it does NOT do

- No flashing, no writing, no erasing. To read/write the ECU use **MS4x Flasher**.
- **No Siemens checksum verification** (not implemented): `bin` only detects obviously incomplete dumps.
- Fault codes are not decoded yet: raw bytes are shown.

## Windows install

Download from the **Releases** page:

- `DMEDoc-Setup-0.2.0.exe`: installer (NSIS), with Start menu / desktop shortcuts and an uninstaller. English or French.
- `DMEDoc.exe`: portable version, no installation.

Both open a graphical interface and ask for administrator rights. On first launch the program asks for your language (English or French); the *Language* button changes it later. Windows SmartScreen / Defender may warn about unsigned executables.

Wiring: ECU K-line ↔ 12 V-compatible interface, DS2 at 9600 baud 8E1, ECU powered with 12 V and ignition (+15).

## From source

```
pip install pyserial
python -m dmedoc gui
python -m dmedoc bin my_dump.bin
python -m dmedoc --lang fr check --port COM3
```

Build the executables:

```
pip install pyinstaller pyserial
pyinstaller --onefile --windowed --uac-admin --name DMEDoc run_gui.py
makensis installer.nsi
```

## Tests

```
python -m unittest discover tests
```

## Roadmap

- Fault code decoding and live values
- Checksum verification (after validation on real dumps)
- Car simulation bench (60-2 crank signal, cam, sensors, EWS)

## License

MIT
