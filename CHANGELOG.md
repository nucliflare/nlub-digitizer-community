# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-06-30

Initial open-source release of the Nuclear Lab Digitizer Community Edition.

### Added

- **Main application window** with tabbed layout: Scope, MCA, Power Supply, External
  devices, and System Log views
- **Scope view** — real-time waveform display with trigger/timing/acquisition controls,
  persistence mode, DMA streaming to binary and HDF5 files
- **MCA view** — pulse-height histogram with ROI selection and statistics, list-mode
  DMA streaming, configurable acquisition parameters
- **Power Supply view** — SiPM bias and HV bias control with temperature compensation,
  real-time voltage/current monitoring with live trend plot
- **External Modbus devices** — auto-discovery of SiPM bias board, Geiger-Mueller probe
  and PMT HV supply over ser2net TCP bridge; generic register table view with live
  telemetry polling and per-register trend plotting (`nlab-modbus` integration)
- **Undockable channels** — each digitizer channel's Scope/MCA/PSU view floats
  independently onto a second monitor and re-docks freely
- **HDF5 support** — convert binary DMA recordings to HDF5 via File menu
- **Settings persistence** — save/load hardware register settings to YAML; dock layout
  state persisted across sessions via QSettings
- **ROI statistics** — configurable region-of-interest overlay on MCA histograms
- **Log console** — in-app system log with colour-coded levels (System Log tab)
- **Documentation** — `docs/` folder with Quarto examples for data analysis workflows
- **Gitea Actions CI** — automated Windows and Linux builds via Nuitka standalone,
  plus lint (ruff), type-check (mypy), and headless Qt test (pytest) steps

### Fixed

- DMA thread not closing cleanly on MCA stop
- Time-limited measurement stopping prematurely
- Pulse polarity detection and start/stop button state indicators
- ZMQ socket `LINGER` default causing process to hang after close when DMA was active
- Taskbar icon not updating correctly for the main window on Windows (deferred
  `WM_SETICON` to post-`show()` to survive `QMainWindow`'s native HWND replacement)
- Windows process identity for taskbar grouping (`SetCurrentProcessExplicitAppUserModelID`)

### Build

- Nuitka standalone packaging with workarounds for:
  - `PySide6.QtOpenGL` / `QtOpenGLWidgets` not auto-discovered by static analysis
  - protoc-generated `*_pb2.py` flat-import style (pre-3.20 codegen) requiring
    explicit data-file shipping alongside the compiled binary
  - Linux executable name conflict with the `nlab/` package directory
- Cross-platform output: `nlab.exe` (Windows), `nlab-app` (Linux), both as
  `dist/main.dist/` standalone folder artifacts

---

[Unreleased]: https://github.com/nucliflare/nlub-digitizer-community/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nucliflare/nlub-digitizer-community/releases/tag/v0.1.0