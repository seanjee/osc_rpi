# RPi5 Digital Oscilloscope (rpiosc)

## Dev setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

## Run tests

```bash
PYTHONPATH=src pytest
```

## Run app (MVP)

```bash
PYTHONPATH=src python -m rpiosc.app
```

Notes:
- If GPIO access fails, run with `sudo`.
