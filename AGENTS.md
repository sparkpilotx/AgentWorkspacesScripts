# Project Instructions

## Tooling & Execution Principles
- Use `just` as the project-level recipe facade. 
- **Discovery First**: Always run `just --list` to discover existing recipes before running project workflows or creating new scripts.
- **Trust the Tooling**: Do not perform manual pre-checks (e.g., shell loops for env vars) before executing a recipe. Trust the local recipes and tools to fail-fast and report errors themselves.
- Do not change tooling configurations unless explicitly requested by a human.

## Shell Scripting Policy
- Keep all shell scripts compatible with **Ubuntu 24.04** and **macOS Tahoe 26** only. Do not account for other platforms. Use commands, flags, and shell features that work on both target systems unless a script explicitly documents a narrower runtime.

## IDE
- VS Code is the only supported IDE. Do not generate configuration or settings for any other editor (JetBrains, Vim, etc.).

## Python Policy
- Target Python 3.12 only. Do not add compatibility code, syntax constraints, or test branches for other versions.
- Use `uv` as the package manager.
