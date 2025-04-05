# Cheat Sheet Creator

A Python application that helps create cheat sheets by arranging multiple images into a grid layout and exporting them to PDF format.

## Features

- Drag and drop images into the reference_images folder
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

2. Place your images in the `reference_images` directory
3. Adjust columns and pages as needed
4. Click "Preview PDF" to see how the final PDF will look
5. Export to PDF when satisfied with the layout

## Directory Structure

- `main.py`: Main application code
- `reference_images/`: Directory for storing input images
- `venv/`: Python virtual environment (created during installation)

## License

MIT License 