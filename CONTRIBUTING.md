# Contributing to auto-memory

## Setup

```bash
git clone <repo>
cd auto-memory
uv pip install -e ".[dev]"
```

## Run Tests

```bash
pytest src/session_recall/tests/ -v
```

## Code Style

- Each file ≤80 lines
- One function per file (or tightly coupled group of 2-3)
- stdlib only — no external dependencies
- Use relative imports within the package

## Adding a Subcommand

1. Create `src/session_recall/commands/your_command.py` with `def run(args) -> int`
2. Add argparse subparser in `__main__.py`
3. Add dispatch `elif` in `__main__.py`
4. Add tests in `tests/test_your_command.py`

## Adding a Health Dimension

1. Create `src/session_recall/health/dim_your_dim.py` with `def check() -> dict`
2. Return `{"name", "score", "zone", "detail", "hint"}`
3. Import and add to `DIMS` list in `commands/health.py`
