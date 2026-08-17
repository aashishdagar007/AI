# Hyperspectral Imaging System

## Overview
This repository implements a hyperspectral imaging pipeline in Python. It provides tools for:
- Ingesting images, videos, or live camera streams (`input_handler.py`).
- Processing data into hyperspectral cubes (`processing_pipeline.py`).
- Visualising and exporting results (`output_handler.py`).
- A Flask web application for interactive use (`web_app.py`).

## Installation
```bash
# Clone the repository
git clone https://github.com/aashishdagar007/AI.git
cd AI

# Install dependencies
pip install -r requirements.txt
```

## Development Dependencies
```bash
pip install -r requirements-dev.txt
```

## Usage
### Command‑line
```bash
python -m input_handler <path_to_image_or_video>
```
### Flask Web App
```bash
python web_app.py
```
Visit `http://127.0.0.1:5000` in your browser.

## Testing
```bash
pytest -q
```
All tests should pass without `PytestReturnNotNoneWarning`.

## Contributing
1. Fork the repository.
2. Create a feature branch.
3. Ensure `pytest -q` passes.
4. Submit a pull request.

## License
MIT License. See `LICENSE` for details.
