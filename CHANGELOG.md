# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-06-03

### Added
- Full type annotations across entire codebase
- Google-style docstrings on all public APIs
- Structured logging with Python `logging` module
- Configuration persistence via QSettings
- Keyboard shortcuts (Ctrl+Z, Ctrl+Y, Ctrl+S, Ctrl+O, 1/2/3 tools, Esc, +/-)
- Menu bar with File, Edit, Tools, Help menus
- Proper status bar with image info and zoom level
- Confirmation dialogs for batch processing and unsaved changes
- Drag-and-drop image loading
- InpaintSettings dataclass for type-safe settings
- Constants module for magic numbers
- pyproject.toml for modern Python packaging
- Comprehensive pytest test suite (~80% coverage)
- GitHub Actions CI/CD pipeline
- Makefile for common dev commands
- Pre-commit hook configuration

### Fixed
- **SECURITY**: np.load() now uses allow_pickle=False to prevent arbitrary code execution
- **BUG**: Magic wand no longer corrupts the source image during flood fill
- **CRASH**: QImage memory safety — numpy buffers now properly copied
- **BUG**: Rectangle tool no longer creates double mask history entries
- **MEMORY**: Undo stacks now bounded (max 20 image states, 50 mask states)
- **UX**: Inpainting now runs off UI thread — no more UI freezes
- **UX**: Algorithm fallback now shows warning instead of silent substitution
- **THREAD**: Batch cancellation now uses thread-safe threading.Event
- **SECURITY**: Batch filenames now sanitized against path traversal
- Zoom now clamped between 0.1x and 20x
- Brush drawing now bounds-checked against image dimensions

### Changed
- Refactored setup_ui() into focused builder methods
- Cross-platform font stack (Inter, SF Pro, Segoe UI)
- Tests migrated from raw asserts to pytest framework

### Removed
- Unused Pillow dependency
- Committed temp_mask.npy/png artifacts

## [1.0.0] - 2026-01-01

### Added
- Initial release with PyQt5 GUI
- Rectangle, brush, and magic wand selection tools
- Telea, Navier-Stokes, Shift-Map, FSR inpainting algorithms
- Mask undo/redo, save/load, smoothing
- Batch processing with template matching
- Grain restoration and edge feathering
- Catppuccin Mocha dark theme
