# 🎯 Elite Watermark Remover Pro

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](.github/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Professional-grade watermark removal tool with multiple inpainting algorithms, intelligent batch processing, and a polished desktop GUI.

---

## ✨ Features

- **4 Inpainting Algorithms**: Telea, Navier-Stokes, Shift-Map (Content Aware), FSR (Frequency Selective)
- **3 Selection Tools**: Rectangle, Brush, and Magic Wand with configurable parameters
- **Intelligent Batch Processing**: Process entire folders with optional template matching
- **Post-Processing**: Auto film grain restoration, edge feathering, mask dilation
- **Mask Management**: Undo/redo (50 states), save/load (PNG/NPY), smoothing
- **Professional UI**: Catppuccin Mocha dark theme, menu bar, keyboard shortcuts, drag & drop
- **Settings Persistence**: Remembers your preferences across sessions
- **Production-Grade Code**: Full type hints, logging, structured error handling, comprehensive tests

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/elite-watermark-remover/watermark-remover.git
cd watermark-remover

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the application
pip install -e .
```

### Run

```bash
# Using the entry point
watermark-remover

# Or directly
python run.py
```

---

## 🎮 Usage

### Single Image Workflow

1. **Load** an image via `File → Open` or drag & drop
2. **Select** the watermark using Rectangle (1), Brush (2), or Magic Wand (3)
3. **Configure** the algorithm and settings in the left panel
4. **Remove** the watermark with `Ctrl+R` or click "Remove Watermark"
5. **Save** the result with `Ctrl+S`

### Batch Processing

1. Select the watermark on a reference image (steps 1-2 above)
2. Click **"Select Target Folder"** to choose a folder of images
3. Enable **Smart Template Matching** to dynamically locate the watermark
4. Click **"Start Batch Process"**

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open Image |
| `Ctrl+S` | Save Result |
| `Ctrl+R` | Remove Watermark |
| `Ctrl+Z` | Undo Image |
| `Ctrl+Shift+Z` | Undo Mask |
| `Ctrl+Y` | Redo Mask |
| `Escape` | Clear Selection |
| `1` | Rectangle Tool |
| `2` | Brush Tool |
| `3` | Magic Wand Tool |
| `Scroll Wheel` | Zoom In/Out |
| `Middle Click` | Pan |
| `Shift+Click` | Pan (alt) |

---

## 🏗️ Architecture

```
src/
├── main.py                    # Application entry point
├── config.py                  # QSettings-based configuration persistence
├── constants.py               # Centralized constants and magic numbers
├── core/
│   ├── inpainter.py           # Core inpainting engine (4 algorithms)
│   ├── models.py              # Typed dataclasses (InpaintSettings, etc.)
│   └── worker.py              # Thread-safe batch processing worker
├── ui/
│   ├── main_window.py         # Main window with menus, shortcuts, panels
│   └── components/
│       ├── image_viewer.py    # Interactive image editor (zoom, pan, tools)
│       └── style.py           # Catppuccin Mocha dark theme stylesheet
└── utils/
    ├── image_utils.py         # OpenCV ↔ Qt image conversion
    └── logging_config.py      # Structured logging setup
```

### Key Design Decisions

- **Dataclasses** for type-safe settings (`InpaintSettings`, `BatchSettings`)
- **Off-thread processing** for both single inpainting and batch operations
- **Bounded history** to prevent memory exhaustion (20 image undo, 50 mask states)
- **Thread-safe cancellation** using `threading.Event`
- **Memory-safe Qt/numpy bridge** with explicit QImage copying

---

## 🧪 Development

### Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### Commands

```bash
make test          # Run tests with coverage
make lint          # Run flake8 + mypy
make format        # Format with black + isort
make type-check    # Strict type checking
make clean         # Clean build artifacts
make run           # Run the application
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_inpainter.py -v
```

---

## 📦 Tech Stack

| Component | Technology |
|-----------|-----------|
| **UI Framework** | PyQt5 5.15+ |
| **Image Processing** | OpenCV (opencv-python-headless) |
| **Array Operations** | NumPy |
| **Packaging** | setuptools + pyproject.toml |
| **Testing** | pytest + pytest-qt + pytest-cov |
| **Linting** | flake8 + mypy + black + isort |
| **CI/CD** | GitHub Actions |

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
