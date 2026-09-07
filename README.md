# Digital Watch Project (ELEN20006)

This repository provides the starter code, automated testing infrastructure including formal verification tools, and the development environment (via a VS Code dev container) for the Digital Watch Project.

The next public release will have the following text suitably modified, and project documentation placed in the `docs/` directory:
- Project documentation is in `docs/`.
  - Assignment #1 Version 1.5
  - Assignment #2 Version 1.2
- Project Version 1.4
- Release Date: 7 September 2026

## Quick Start Checklist

1. Install VS Code, Docker Desktop, Git, and the VS Code `Dev Containers` extension.
2. Git clone this repository.
3. Ensure Docker Desktop is running.
4. Open this folder in VS Code.
5. Select `Reopen in Container` when prompted.

If you do not see the prompt, ensure that the `.devcontainer` folder is at the top level of your project. Open the root directory in VS Code (not a parent folder). Then, run `Dev Containers: Reopen in Container` from the Command Palette.

## Important Notes

1. You are responsible for maintaining regular backups of your work. Git is strongly recommended, although it is not essential.
2. During the project, you may be asked to update to a newer version of this repository. This is a common scenario in real-world, team-based development. You can either run `git pull` or download the new version to a separate folder and copy your current `rtl/` directory into it. (This is why you should only modify files within the `rtl/` directory.)
3. If you encounter unexpected behavior, first try running `Dev Containers: Rebuild Container`.

## Why Use VS Code for This Project?

- Quartus is not a true development environment; it lacks many standard features, making coding and iteration much slower than necessary.
- VS Code provides efficient editing, continuous linting, and straightforward access to automated tests.
- Using the dev container ensures a consistent toolchain across all platforms.
- VS Code is an industry-standard IDE, so proficiency with it is a transferable professional skill.

## New to VS Code?

Use the following steps to install the required extension:

1. Open VS Code.
2. Select `File > Open Folder...` and choose this project folder.
3. Open Extensions using the left sidebar icon, or press `Ctrl+Shift+X`.
4. Search for `Dev Containers`.
5. Install the extension published by Microsoft.

Tip: You can also install extensions via the Command Palette (`Ctrl+Shift+P`) using `Extensions: Install Extensions`.

## Useful VS Code Features

- Split editor: Right-click a tab and select `Split Right` to view design files and testbench files side by side.
- Multi-cursor editing: Hold `Alt` and click in multiple locations (or use `Ctrl+Alt+Down/Up`) to edit repeated text efficiently.
- Integrated terminal: Use `Ctrl+backtick` to run compile and test commands without leaving the editor.
- Search across files: Press `Ctrl+Shift+F` to locate modules, signals, and TODO items across the project.
- Command Palette: Press `Ctrl+Shift+P` to run commands such as reopening or rebuilding the dev container.

## Included Tools

The dev container includes:

- `iverilog`
- `verilator`
- `pytest`
- `yosys`
- `sby`

These tools support compilation, simulation, linting, synthesis and formal verification.

## Included VS Code Extensions

- `chipsalliance.verible`: Provides SystemVerilog formatting and basic linting.
- `eirikpre.systemverilog`: Provides SystemVerilog language support, including syntax highlighting and code navigation.
- `lramseyer.vaporview`: Provides in-editor waveform viewing for formats such as VCD and FST.
- `ms-python.python`: Provides Python support for testing scripts.
- `charliermarsh.ruff`: Provides Python linting and formatting.

## Project Structure

- `rtl/` --- SystemVerilog source files (place your assessed work here)
- `tb/` --- manual testbenches for debugging your design
- `sby/` --- formal verification tests
- `tests/` --- automated pytest/cocotb tests
- `templates/` --- starter templates for your project
- `demos/` --- small example designs to familiarise yourself with the tools
- `.devcontainer/` --- container configuration for the development environment

## Troubleshooting

- Ensure the container is activated (check the bottom left corner of VS Code for the container status).
- If the container does not start, confirm Docker Desktop is running.
- If expected extensions do not appear, or if the environment is misbehaving, run `Dev Containers: Rebuild Container`.
