# Contributing

## Code Quality and Development Tools

This project uses modern Python development tools to maintain code quality and consistency. All tool configurations are centralized in `pyproject.toml` following Python best practices.

### Development Environment Setup

1. **Install the package in development mode:**
   ```bash
   pip install -e .
   ```

2. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Set up pre-commit hooks (recommended):**
   ```bash
   pre-commit install
   ```
   This will automatically run code quality checks before each commit.

### Code Quality Tools

We use the following tools to ensure consistent code style and catch common errors:

#### Ruff - Linting and Formatting
[Ruff](https://github.com/astral-sh/ruff) is a fast Python linter and formatter that combines the functionality of multiple tools (flake8, pylint, isort, etc.).

**Run the linter:**
```bash
ruff check .
```

**Auto-fix issues:**
```bash
ruff check --fix .
```

**Format code:**
```bash
ruff format .
```

#### isort - Import Sorting
Automatically sorts and organizes imports according to PEP 8 and black-compatible style.

**Check imports:**
```bash
isort --check-only .
```

**Auto-fix imports:**
```bash
isort .
```

#### mypy - Type Checking
Static type checker for Python (optional but recommended for new code).

**Run type checking:**
```bash
mypy gimpopenvino
```

#### black - Code Formatting
Alternative code formatter (ruff format can replace this).

**Format code:**
```bash
black .
```

#### Pre-commit Hooks
Pre-commit runs all configured checks automatically before each commit.

**Run all hooks manually:**
```bash
pre-commit run --all-files
```

**Update hook versions:**
```bash
pre-commit autoupdate
```

### Configuration Files

- **`pyproject.toml`** - Central configuration for all tools (ruff, isort, mypy, black, pytest)
- **`.pre-commit-config.yaml`** - Pre-commit hook configuration
- **`.editorconfig`** - Cross-editor settings (indentation, line endings, encoding)

### Code Style Guidelines

- **Line length:** 88 characters (black/ruff default)
- **Indentation:** 4 spaces for Python files
- **String quotes:** Double quotes preferred
- **Import sorting:** Organized by standard library, third-party, and first-party modules
- **Type hints:** Encouraged for new code and public APIs

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gimpopenvino

# Run specific test markers
pytest -m unit
pytest -m integration
```

### Workflow for Contributors

1. **Before starting work:**
   ```bash
   git checkout -b feature/your-feature-name
   pip install -r requirements-dev.txt
   pre-commit install
   ```

2. **During development:**
   - Write code following the style guidelines
   - Add tests for new functionality
   - Let pre-commit hooks run automatically on commit, or run manually:
     ```bash
     pre-commit run --all-files
     ```

3. **Before submitting a PR:**
   ```bash
   # Run all quality checks
   ruff check --fix .
   ruff format .
   isort .
   
   # Run tests
   pytest
   
   # Verify pre-commit hooks pass
   pre-commit run --all-files
   ```

### Gradual Adoption

We recognize that applying strict linting rules to an existing codebase can be overwhelming. Our approach:

- **New code:** Should pass all configured checks
- **Modified code:** Fix issues in the lines you change
- **Existing code:** Can be improved incrementally
- **Type hints:** Not required for existing code, but encouraged for new code

#### Current Configuration

The ruff configuration has been tuned for gradual adoption:

- **Basic rules enabled:** `E` (pycodestyle errors), `F` (pyflakes), `W` (warnings), `I` (import sorting)
- **Ignored for now:** Complex refactoring rules (N, UP, B, C4, SIM) - these will be enabled gradually
- **Auto-fixed:** Whitespace, trailing whitespace, import ordering
- **Per-file ignores:** Specific patterns ignored in ML model code, GUI code, and existing plugins

#### When to Fix vs. Ignore

**Fix immediately:**
- Import errors (F401 - unused imports)
- Undefined variables (F821 - critical bugs)
- Syntax errors (E)

**Fix when touching the code:**
- Unused variables (F841)
- Comparison issues (E711)
- Bare except clauses (E722)

**Can be ignored for now:**
- Import ordering at file top (E402) - GIMP plugins require `gi.require_version` first
- Mutable default arguments (B006) - common pattern in ML frameworks
- Complex simplifications (SIM*) - subjective improvements

You can disable specific rules for legitimate reasons using inline comments:
```python
# ruff: noqa: E501  - This line intentionally exceeds line length
long_url = "https://..."

# type: ignore  - Third-party library without type stubs
import some_untyped_library  # type: ignore
```

#### Running Checks

The linter is configured to report issues but allow gradual fixes:
```bash
# Check for issues (many will be ignored per configuration)
ruff check .

# Auto-fix safe issues
ruff check --fix .

# Format code (whitespace, quotes, etc.)
ruff format .
```

## Dependency Management

This project follows modern Python packaging best practices:

### Runtime Dependencies
All runtime dependencies are managed in `setup.py` under the `install_requires` section. This is the single source of truth for dependencies needed to run the GIMP OpenVINO AI Plugins.

**To install the package with all runtime dependencies:**
```bash
pip install -e .
```

### Development Dependencies
Development and testing dependencies are managed in `requirements-dev.txt`. These include:
- Testing frameworks (pytest, pytest-cov, etc.)
- Code quality tools (black, flake8, isort, mypy)
- Additional testing utilities

**To install development dependencies:**
```bash
pip install -r requirements-dev.txt
```

### Key Dependency Versions
- **Python**: Requires Python 3.10 or later (Python 3.7-3.9 are EOL)
- **OpenVINO**: Pinned to version 2025.4.0 for stability and compatibility
- **transformers**: Version range 4.37.0 to 4.56.2 for compatibility with OpenVINO
- **openvino-genai**: Pinned to 2025.4.0.0 to match OpenVINO version

### Adding New Dependencies
When adding new dependencies:
1. Add runtime dependencies to `setup.py` under `install_requires`
2. Add development/test dependencies to `requirements-dev.txt`
3. Specify version constraints when compatibility matters
4. Test installation in a clean virtual environment

## License

openvino-ai-plugins-gimp is licensed under the terms in [Apache 2.0] https://github.com/intel/openvino-ai-plugins-gimp/LICENSE.md. By contributing to the project, you agree to the license and copyright terms therein and release your contribution under these terms.

### Sign your work

Please use the sign-off line at the end of the patch. Your signature certifies that you wrote the patch or otherwise have the right to pass it on as an open-source patch. The rules are pretty simple: if you can certify
the below (from [developercertificate.org](http://developercertificate.org/)):

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
660 York Street, Suite 102,
San Francisco, CA 94110 USA

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

Then you just add a line to every git commit message:

    Signed-off-by: Joe Smith <joe.smith@email.com>

Use your real name (sorry, no pseudonyms or anonymous contributions.)

If you set your `user.name` and `user.email` git configs, you can sign your
commit automatically with `git commit -s`.
