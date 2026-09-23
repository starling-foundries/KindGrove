# Pre-Commit Hooks Setup Guide

This project uses [pre-commit](https://pre-commit.com/) to automatically check code quality, format code, and prevent common mistakes before committing.

## Quick Start

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Done! Hooks will run automatically on git commit
```

## What Gets Checked

### 🐍 Python Code Quality
- **Black** - Auto-formats Python code to consistent style
- **isort** - Sorts and organizes imports
- **Ruff** - Fast linting (catches bugs, style issues)
- **Bandit** - Security vulnerability scanning

### 📓 Jupyter Notebooks
- **nbstripout** - Strips output cells (keeps notebooks clean, prevents data leaks)
- **nbqa** - Applies black/isort to notebook code cells

### 📁 File Hygiene
- Removes trailing whitespace
- Ensures files end with newline
- Blocks large files (>500KB)
- Detects private keys and credentials
- Checks JSON/YAML syntax

### 🔬 Project-Specific
- **CWL Validation** - Validates workflow syntax with `cwltool`
- **Data File Protection** - Blocks *.tif, *.nc, *.hdf files
- **Output Protection** - Blocks CSV output files
- **Requirements Check** - Validates requirements.txt

## Manual Usage

Run hooks on all files (useful after initial setup):
```bash
pre-commit run --all-files
```

Run specific hook:
```bash
pre-commit run black --all-files
pre-commit run nbstripout --all-files
```

Run hooks on specific files:
```bash
pre-commit run --files src/biomass_models.py
```

## Skip Hooks (Emergency Only)

If you need to bypass hooks (not recommended):
```bash
git commit --no-verify
```

## Excluded Files

Hooks automatically skip:
- `debug_*.py` - Debug scripts
- `fix_*.py` - Fix/patch scripts
- `test_*.py` - Some test files (varies by hook)

## Hook Details

### Black (Python Formatter)
- Line length: 88 characters
- Target: Python 3.12
- Config: `pyproject.toml`

### Ruff (Linter)
- Checks: pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade
- Ignores: E501 (line too long - black handles this)
- Config: `pyproject.toml`

### nbstripout (Notebook Cleaner)
Removes:
- Output cells
- Execution counts
- Kernel metadata
- Language version info

**Why?** Keeps notebooks clean, prevents accidentally committing:
- Large outputs
- Sensitive data in outputs
- Notebook bloat (better diffs)

### CWL Validation
Requires `cwltool` to be installed:
```bash
pip install cwltool
```

If not installed, validation is skipped (won't block commits).

## Troubleshooting

### Hook fails with "command not found"
Install missing dependency:
```bash
pip install pre-commit  # If pre-commit not found
pip install cwltool     # If CWL validation fails
```

### Black and Ruff disagree
This shouldn't happen - Ruff is configured to be compatible with Black.
If it does, run:
```bash
pre-commit autoupdate
```

### Notebook has merge conflict
nbstripout can cause issues with merges. Resolve manually:
```bash
git checkout --ours path/to/notebook.ipynb
# or
git checkout --theirs path/to/notebook.ipynb

# Then re-run hooks
pre-commit run --files path/to/notebook.ipynb
```

### "File is too large"
Large files (>500KB) are blocked by default. Options:
1. Add to .gitignore (recommended for data files)
2. Use Git LFS
3. Skip the hook: `SKIP=check-added-large-files git commit`

## Updating Hooks

Keep hooks up to date:
```bash
pre-commit autoupdate
```

This updates hook versions in `.pre-commit-config.yaml`.

## Continuous Integration

These same checks can run in CI/CD:
```bash
# In CI pipeline
pip install pre-commit
pre-commit run --all-files
```

## Custom Scripts

Project-specific validation scripts in `scripts/`:
- `validate_cwl.sh` - Validates CWL workflow files
- `check_requirements.sh` - Checks requirements.txt format

## Configuration Files

- `.pre-commit-config.yaml` - Hook definitions
- `pyproject.toml` - Tool configs (black, ruff, bandit, isort)
- `.gitignore` - Excludes pre-commit cache

## Benefits

✅ Consistent code style across contributors
✅ Catch bugs before they're committed
✅ Prevent data leaks (stripped notebook outputs)
✅ Block large files and credentials
✅ Faster code reviews (no style debates)
✅ Professional, maintainable codebase

## Questions?

See [pre-commit documentation](https://pre-commit.com/) or ask in project issues.
