import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from math import ceil, sqrt
import tempfile
import subprocess
import platform
import threading
import time
import argparse
import re
import logging
import webbrowser

class ImageFrame:
    def __init__(self, image_path, timestamp):
        self.image_path = image_path
        self.timestamp = timestamp
        self.original_image = Image.open(image_path)
        self.thumbnail = None
        self.thumbnail_photo = None
        self.frame = None
        self.label = None
        self.delete_button = None

class CheatSheetCreator:
    # Constants
    DEFAULT_COLUMNS = 3
    DEFAULT_MAX_PAGES = 2
    DEFAULT_MARGIN_PTS = 10
    DEFAULT_PADDING_PTS = 10
    DEFAULT_THUMBNAIL_ASPECT_RATIO = 0.75
    DEFAULT_CANVAS_WIDTH = 800
    PREVIEW_FILENAME = "preview.pdf"
    FILENAME_FONT_SIZE = 6
    FILENAME_MAX_LEN = 20

    def __init__(self, root):
        self.root = root
        self.root.title("Cheat Sheet Creator")
        self.root.geometry("1200x800")
        
        # Variables
        self.image_frames = []
        self.current_directory = os.getcwd()
        self.images_dir = os.path.join(self.current_directory, "reference_images")
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create control frame
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Directory selection
        self.dir_frame = ttk.Frame(self.control_frame)
        self.dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.dir_frame, text="Images Directory:").pack(side=tk.LEFT)
        self.dir_entry = ttk.Entry(self.dir_frame, width=50)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        self.dir_entry.insert(0, self.images_dir)
        
        self.browse_button = ttk.Button(self.dir_frame, text="Browse...", command=self.browse_directory)
        self.browse_button.pack(side=tk.LEFT)
        
        # Layout settings
        self.settings_frame = ttk.Frame(self.control_frame)
        self.settings_frame.pack(fill=tk.X, pady=5)
        
        # Margin setting
        ttk.Label(self.settings_frame, text="Margin (pts):").pack(side=tk.LEFT)
        self.margin_var = tk.IntVar(value=self.DEFAULT_MARGIN_PTS)
        self.margin_entry = ttk.Entry(self.settings_frame, width=5, textvariable=self.margin_var)
        self.margin_entry.pack(side=tk.LEFT, padx=5)
        
        # Column setting
        ttk.Label(self.settings_frame, text="Columns:").pack(side=tk.LEFT, padx=(20, 5))
        self.column_var = tk.IntVar(value=self.DEFAULT_COLUMNS)
        self.column_combo = ttk.Combobox(self.settings_frame, textvariable=self.column_var,
                                       values=[str(i) for i in range(1, 7)], width=5)
        self.column_combo.pack(side=tk.LEFT)
        
        # Page setting
        ttk.Label(self.settings_frame, text="Max Pages:").pack(side=tk.LEFT, padx=(20, 5))
        self.page_var = tk.IntVar(value=self.DEFAULT_MAX_PAGES)
        self.page_combo = ttk.Combobox(self.settings_frame, textvariable=self.page_var,
                                     values=[str(i) for i in range(1, 11)], width=5)
        self.page_combo.pack(side=tk.LEFT)
        
        # Buttons
        self.button_frame = ttk.Frame(self.control_frame)
        self.button_frame.pack(fill=tk.X, pady=5)
        
        self.load_button = ttk.Button(self.button_frame, text="Load Images", command=self.load_images)
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        self.preview_button = ttk.Button(self.button_frame, text="Preview PDF", command=self.preview_pdf)
        self.preview_button.pack(side=tk.LEFT, padx=5)
        
        self.export_button = ttk.Button(self.button_frame, text="Export PDF", command=self.export_pdf)
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # Create canvas for image grid
        self.canvas_frame = ttk.Frame(self.main_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.image_container = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.image_container, anchor="nw")
        
        self.image_container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Initialize with default directory
        if os.path.exists(self.images_dir):
            self.load_images()
    
    def _parse_timestamp(self, image_path):
        """Parses timestamp from filename or uses fallbacks."""
        filename = os.path.basename(image_path)
        logging.debug(f"\nParsing timestamp for: {filename}")
        timestamp = None
        try:
            # Try to extract timestamp from filename (macOS format)
            # Example: Screenshot 2025-04-05 at 9.25.49 PM.png
            match = re.search(r'(\d{4}-\d{2}-\d{2}) at (\d{1,2}\.\d{2}\.\d{2})\s*(AM|PM)?', filename, re.IGNORECASE)
            if match:
                date_str, time_str, period = match.groups()
                # Handle potential missing period (common in some locales/versions)
                if period is None:
                    try:
                        # Try parsing as 24-hour first
                        dt_obj = datetime.strptime(f"{date_str} {time_str.replace('.', ':')}", "%Y-%m-%d %H:%M:%S")
                        timestamp = dt_obj
                        logging.debug(f"Parsed as 24-hour format: {timestamp}")
                    except ValueError:
                        # Fallback or make an assumption - here we'll assume PM for hours > 12 if period is missing
                        hours, minutes, seconds = map(int, time_str.split('.'))
                        if hours > 12: period = 'PM'
                        else: period = 'AM'

                if timestamp is None: # If not parsed as 24h or if period was present
                    hours, minutes, seconds = map(int, time_str.split('.'))
                    if period and period.upper() == 'PM' and hours != 12:
                        hours += 12
                    elif period and period.upper() == 'AM' and hours == 12:
                        hours = 0 # Midnight case
                    timestamp = datetime.strptime(f"{date_str} {hours:02d}:{minutes:02d}:{seconds:02d}",
                                                "%Y-%m-%d %H:%M:%S")
                    logging.debug(f"Successfully parsed timestamp from filename: {timestamp}")

        except Exception as e:
            logging.warning(f"Could not parse timestamp from filename '{filename}': {str(e)}")

        # Fallback 1: Use file modification time
        if timestamp is None:
            try:
                mtime = os.path.getmtime(image_path)
                timestamp = datetime.fromtimestamp(mtime)
                logging.debug(f"Using file modification time: {timestamp}")
            except Exception as e:
                logging.error(f"Error getting file modification time for {filename}: {str(e)}")

        # Fallback 2: Use current time as the last resort
        if timestamp is None:
            timestamp = datetime.now()
            logging.warning(f"Using current time as fallback for {filename}: {timestamp}")

        # Ensure timestamp is always a datetime object before returning
        if not isinstance(timestamp, datetime):
             logging.error(f"Timestamp assignment failed unexpectedly for {filename}, using current time.")
             timestamp = datetime.now() # Final safety net

        return timestamp

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.current_directory)
        if directory:
            self.images_dir = directory
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.load_images()
    
    def load_images(self):
        # Clear existing images
        for frame in self.image_frames:
            if frame.frame:
                frame.frame.destroy()
        self.image_frames.clear()
        
        # Load new images
        if not os.path.exists(self.images_dir):
            messagebox.showerror("Error", f"Directory not found: {self.images_dir}")
            return
        
        print(f"\nLoading images from: {self.images_dir}")
        
        image_files = []
        for filename in os.listdir(self.images_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(self.images_dir, filename))
        
        if not image_files:
            messagebox.showwarning("No Images", "No images found in the selected directory.")
            return
        
        # First, create all image frames
        temp_frames = [] # Create temp list first
        for image_path in image_files:
            try:
                timestamp = self._parse_timestamp(image_path)
                frame = ImageFrame(image_path, timestamp)
                temp_frames.append(frame)
            except FileNotFoundError:
                 logging.error(f"Image file not found during ImageFrame creation: {image_path}")
            except Exception as e:
                 logging.exception(f"Error creating ImageFrame for {image_path}: {e}")

        # Assign to instance variable and sort
        self.image_frames = temp_frames
        self.image_frames.sort(key=lambda x: x.timestamp)
        
        # Update layout
        self.update_layout()
    
    def update_layout(self):
        if not self.image_frames:
            logging.info("No images to layout")
            return
        
        # Clear existing frames
        for frame in self.image_frames:
            if frame.frame:
                frame.frame.destroy()
        
        # Calculate grid dimensions
        num_columns = self.column_var.get()
        num_rows = (len(self.image_frames) + num_columns - 1) // num_columns
        
        # Calculate thumbnail size
        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 1:  # If canvas hasn't been drawn yet
            canvas_width = self.DEFAULT_CANVAS_WIDTH  # Use constant
        
        thumbnail_width = (canvas_width - 20) // num_columns  # 20 for padding
        thumbnail_height = int(thumbnail_width * self.DEFAULT_THUMBNAIL_ASPECT_RATIO) # Use constant
        
        # Create image grid
        for i, frame in enumerate(self.image_frames):
            row = i // num_columns
            col = i % num_columns
            
            # Create frame for image
            frame.frame = ttk.Frame(self.image_container)
            frame.frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Create thumbnail
            frame.thumbnail = frame.original_image.copy()
            frame.thumbnail.thumbnail((thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS)
            frame.thumbnail_photo = ImageTk.PhotoImage(frame.thumbnail)
            
            # Create label for image
            frame.label = ttk.Label(frame.frame, image=frame.thumbnail_photo)
            frame.label.pack()
            
            # Add filename label
            filename = os.path.basename(frame.image_path)
            ttk.Label(frame.frame, text=filename, wraplength=thumbnail_width).pack()
        
        # Configure grid weights
        for i in range(num_rows):
            self.image_container.grid_rowconfigure(i, weight=1)
        for i in range(num_columns):
            self.image_container.grid_columnconfigure(i, weight=1)
    
    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        # Update canvas width
        canvas_width = event.width
        self.canvas.itemconfig("all", width=canvas_width)
        # Update layout if images are loaded
        if self.image_frames:
            self.update_layout()
    
    def preview_pdf(self):
        # Create temporary PDF file
        temp_file = self.PREVIEW_FILENAME # Use constant
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError as e:
                 logging.error(f"Error removing existing preview file {temp_file}: {e}")
                 messagebox.showerror("Preview Error", f"Could not remove existing preview file: {temp_file}\n{e}")
                 return
        
        # Export to temporary file
        pdf_path = self.export_pdf(temp_file)
        if pdf_path:
             try:
                 # Open PDF viewer using webbrowser
                 webbrowser.open(f"file://{os.path.abspath(pdf_path)}") # Use webbrowser and absolute path
             except Exception as e:
                 logging.error(f"Error opening preview PDF {pdf_path}: {e}")
                 messagebox.showerror("Preview Error", f"Could not open preview PDF: {pdf_path}\n{e}")
    
    def export_pdf(self, file_path=None):
        if not self.image_frames:
            logging.warning("No images to export")
            messagebox.showwarning("No Images", "There are no images to export.")
            return None

        # Ask for file path only if not provided (for actual export)
        is_temp_file = file_path is not None
        if not is_temp_file:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")]
            )
            if not file_path:
                return None

        try:
            # Create PDF
            c = canvas.Canvas(file_path, pagesize=letter)
            page_width, page_height = letter
            
            # Get settings from GUI
            margin = self.margin_var.get()
            num_columns = self.column_var.get()
            max_pages = self.page_var.get()
            padding = self.DEFAULT_PADDING_PTS # Use constant for padding
            
            usable_width = page_width - 2 * margin
            usable_height = page_height - 2 * margin
            
            logging.info("\nPage dimensions:")
            logging.info(f"  Total width: {page_width}pt, height: {page_height}pt")
            logging.info(f"  Usable width: {usable_width}pt, height: {usable_height}pt")
            
            if usable_width <= 0 or usable_height <= 0:
                messagebox.showerror("Export Error", f"Margins ({margin} pts) are too large for the page size.")
                if is_temp_file and os.path.exists(file_path):
                    os.unlink(file_path)
                return None

            # Calculate cell width (fixed for all columns)
            cell_width = usable_width / num_columns
            
            logging.info(f"\nColumn layout:")
            logging.info(f"  Number of columns: {num_columns}")
            logging.info(f"  Cell width: {cell_width}pt")
            logging.info(f"  Padding between images: {padding}pt")
            
            # Group images by column
            columns = [[] for _ in range(num_columns)]
            for i, frame in enumerate(self.image_frames):
                col_idx = i % num_columns
                columns[col_idx].append(frame)
            
            logging.info(f"\nImage distribution:")
            for i, col in enumerate(columns):
                logging.info(f"  Column {i+1}: {len(col)} images")
            
            # Process each page
            current_page = 0
            while current_page < max_pages and any(columns):
                if current_page > 0:
                    c.showPage()
                
                logging.info(f"\nProcessing page {current_page + 1}")
                
                # Process each column
                for col_idx, column in enumerate(columns):
                    # Start from top of page
                    y = page_height - margin
                    
                    logging.info(f"\n  Processing column {col_idx + 1}")
                    logging.info(f"    Starting y position: {y}pt")
                    
                    # Process images in column until we run out of space
                    while column and y > margin:
                        frame = column[0]
                        img_width, img_height = frame.original_image.size
                        aspect_ratio = img_height / img_width
                        scaled_width = cell_width * 0.90
                        scaled_height = scaled_width * aspect_ratio
                        
                        # Check if image fits (considering padding below image)
                        if y - scaled_height < margin:
                            # If even the first image doesn't fit, break column processing
                            if y == page_height - margin:
                                logging.warning(f"      Image {os.path.basename(frame.image_path)} is too tall to fit on page {current_page + 1}, column {col_idx + 1}.")
                            break
                        
                        # Calculate x position (centered in column)
                        x = margin + (col_idx * cell_width) + (cell_width - scaled_width) / 2
                        
                        filename = os.path.basename(frame.image_path)
                        logging.info(f"\n    Placing {filename}:")
                        logging.info(f"      Original size: {img_width}x{img_height}")
                        logging.info(f"      Scaled size: {scaled_width:.2f}x{scaled_height:.2f}")
                        logging.info(f"      Position: x={x:.2f}, y={y:.2f}")
                        
                        # Draw border
                        c.setLineWidth(0.5)
                        c.setStrokeColorRGB(0, 0, 0)
                        c.rect(x, y - scaled_height, scaled_width, scaled_height, stroke=1, fill=0)
                        
                        # Draw image using ImageReader for performance
                        try:
                            img_reader = ImageReader(frame.original_image)
                            c.drawImage(img_reader, x, y - scaled_height, width=scaled_width, height=scaled_height)
                        except Exception as img_err:
                             logging.error(f"      Error drawing image {filename}: {img_err}")
                             # Optionally draw a placeholder or skip
                             c.setFillColorRGB(0.8, 0.8, 0.8) # Gray fill
                             c.rect(x, y - scaled_height, scaled_width, scaled_height, stroke=0, fill=1)
                             c.setFillColorRGB(0, 0, 0) # Black text
                             c.setFont("Helvetica", 8)
                             c.drawCentredString(x + scaled_width / 2, y - scaled_height / 2, f"Error loading {filename}")
                        
                        # Draw filename if not preview
                        if not is_temp_file:
                            c.setFont("Helvetica", self.FILENAME_FONT_SIZE)
                            # Truncate filename if it's too long
                            max_len = self.FILENAME_MAX_LEN
                            short_name = (filename[:max_len] + '...') if len(filename) > max_len else filename
                            # Draw filename at the bottom-left inside the border
                            c.drawString(x + 2, y - scaled_height + 2, short_name)
                        
                        # Update y position for next image
                        y -= (scaled_height + padding)
                        logging.info(f"      Next y position: {y:.2f}pt")
                        
                        # Remove the placed image
                        column.pop(0)
                
                current_page += 1
            
            c.save()
            if not is_temp_file:
                logging.info(f"PDF exported to: {file_path}")
                messagebox.showinfo("Export Successful", f"PDF exported successfully to: {file_path}")
            return file_path
            
        except Exception as e:
            logging.exception(f"Error exporting PDF: {str(e)}") # Use logging.exception to include traceback
            messagebox.showerror("Export Error", f"An error occurred while exporting the PDF: {str(e)}")
            # Clean up temporary file on error
            if is_temp_file and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except OSError as unlink_err:
                    logging.error(f"Error removing temporary PDF file {file_path} after export error: {unlink_err}")
            return None

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    setup_logging() # Setup logging configuration
    parser = argparse.ArgumentParser(description='Cheat Sheet Creator')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode (enables preview)')
    parser.add_argument('--images', type=str, help='Path to images directory')
    args = parser.parse_args()
    
    root = tk.Tk()
    app = CheatSheetCreator(root)
    
    if args.debug:
        logging.info("Debug mode enabled - will run preview process automatically")
        # Set logging level to DEBUG if debug flag is set
        logging.getLogger().setLevel(logging.DEBUG)
        if args.images:
            # Validate image path provided via args
            if not os.path.isdir(args.images):
                 logging.error(f"Invalid image directory specified via --images: {args.images}")
                 messagebox.showerror("Startup Error", f"Invalid image directory specified:\n{args.images}")
                 root.quit() # Exit if dir is bad
                 return
            app.images_dir = args.images
            app.dir_entry.delete(0, tk.END)
            app.dir_entry.insert(0, args.images)
            app.load_images()
            if app.image_frames: # Only preview if images were loaded
                app.preview_pdf()
        else:
             logging.warning("Debug mode enabled, but no --images directory specified.")
             messagebox.showwarning("Debug Mode", "Debug mode enabled, but no image directory specified via --images argument.")
    
    root.mainloop()

if __name__ == "__main__":
    main() 