# Cheat Sheet Creator

A Python application that helps create cheat sheets by arranging multiple images into a grid layout and exporting them to PDF format.

## Features

- Drag and drop images into the reference_images folder
- Select custom directory for images
- Automatically arranges images in a grid layout
- Adjustable number of columns (Auto, 1-4)
- Multiple page support
- Preview before export
- Export to PDF with customizable layout
- Delete individual images with hover button
- Maintains aspect ratio of images

## Requirements

- Python 3.9+
- tkinter (usually comes with Python)
- Pillow (PIL)
- reportlab

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cheat-sheet-creator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install pillow reportlab
```

## Usage

1. Run the application:
```bash
python main.py
```

2. Place your images in the `reference_images` directory or select a custom directory using the "Browse..." button
3. Adjust columns and pages as needed
4. Click "Preview PDF" to see how the final PDF will look
5. Export to PDF when satisfied with the layout

### Debug Mode

To run the application in debug mode (with a 30-second timeout for testing):
```bash
python main.py --debug
```

## Directory Structure

- `main.py`: Main application code
- `reference_images/`: Default directory for storing input images (optional)
- `venv/`: Python virtual environment (created during installation)

## License

MIT License 