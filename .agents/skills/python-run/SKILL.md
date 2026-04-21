---
name: python-run
description: "Workflow: execution priority and practical usage for running Python scripts in different Python environments (including uv, conda, and system Python), with common helper commands."
argument-hint: "The script path to run or a task description"
disable-model-invocation: true
---

# Python Execution Flow (Priority Order)

This skill provides a unified way to run Python scripts and follows a fixed execution priority:

1. `uv run script.py` (uv Python)
2. `conda activate <env> && python3 script.py` (conda Python)
3. `python3 script.py` (system/brew Python, DO NOT INSTALL PACKAGES IN THIS PYTHON INTERPRETER)

- Common package management commands are included: `uv add`, `uv pip install`, `conda install`.

Follow these rules strictly:

- Do not perform any action that installs or overwrites system Python, or installs a new Python version.
- Do not use: `uv python install ...`, `uv pip install --system ...`, `brew install python`, or manual installation through the official Python installer.
- If a different Python version is required but not available locally, stop and report it. Do not install it automatically.

## Step 0: Prerequisite Check

```bash
command -v uv >/dev/null 2>&1 && echo "uv:ok" || echo "uv:missing"
command -v conda >/dev/null 2>&1 && echo "conda:ok" || echo "conda:missing"
command -v python3 >/dev/null 2>&1 && echo "python3:ok" || echo "python3:missing"
```

## Path A (Highest Priority): uv

Applicable when

- `uv` is available.

Run scripts

```bash
uv run script.py
uv run script.py -- arg1 arg2
uv run -m package.module
```

Script dependencies (PEP 723 script metadata)

```bash
uv add --script script.py requests rich
uv lock --script script.py
uv run script.py
```

One-off dependencies

```bash
uv run --with rich script.py
```

Project dependencies (pyproject.toml)

```bash
uv add httpx
uv add --dev pytest
uv add -r requirements.txt
uv run script.py
```

pip-compatible interface (use only inside a virtual environment / Conda environment)

```bash
uv venv
uv pip install -r requirements.txt
uv pip install "ruff>=0.2.0"
uv pip uninstall ruff
```

Notes

- According to the official documentation, `uv pip` searches for an activated venv / Conda / `.venv` by default and will prompt to create an environment if none is found.
- Do not use `--system` to modify the system Python environment.

## Path B (Second Priority): conda

Applicable when

- `uv` is unavailable, and `conda` is available.

Run scripts

```bash
conda run -n myenv python3 script.py
conda activate myenv && python3 script.py
```

Install dependencies

```bash
conda install -n myenv numpy pandas
conda install -n myenv -c conda-forge pydantic
mamba install -n myenv ruff
```

Additional note

- Prefer `conda install` whenever possible, and use `python -m pip install ...` inside that environment only when necessary.

## Path C (Lowest Priority): python3

Applicable when

- Neither `uv` nor `conda` is available, and `python3` exists.

Run scripts and isolated environments

```bash
python3 script.py
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python script.py
```

Restrictions

- Do not use `sudo pip`.
- Do not modify the system Python site-packages directory.

## Decision Flow

1. If `uv` is available, use Path A.
2. Otherwise, if `conda` is available, use Path B.
3. Otherwise, use Path C.
4. If none of the three are available, report the environment as missing and do not install Python.

## Example Prompts

- "Please run script.py in priority order: try uv first, then conda, and finally python3."
- "Use uv to add the requests dependency to script.py and run it."
- "Switch to the conda flow and use conda install to add the missing dependencies."

# End of SKILL
