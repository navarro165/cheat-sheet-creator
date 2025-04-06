import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from math import ceil, sqrt
import tempfile
import subprocess
import platform
import threading
import time
import argparse
import re

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
        self.margin_var = tk.IntVar(value=10)
        self.margin_entry = ttk.Entry(self.settings_frame, width=5, textvariable=self.margin_var)
        self.margin_entry.pack(side=tk.LEFT, padx=5)
        
        # Column setting
        ttk.Label(self.settings_frame, text="Columns:").pack(side=tk.LEFT, padx=(20, 5))
        self.column_var = tk.StringVar(value="3")
        self.column_combo = ttk.Combobox(self.settings_frame, textvariable=self.column_var, 
                                       values=["3"], state="readonly", width=5)
        self.column_combo.pack(side=tk.LEFT)
        
        # Page setting
        ttk.Label(self.settings_frame, text="Max Pages:").pack(side=tk.LEFT, padx=(20, 5))
        self.page_var = tk.StringVar(value="2")
        self.page_combo = ttk.Combobox(self.settings_frame, textvariable=self.page_var, 
                                     values=["2"], state="readonly", width=5)
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
        for image_path in image_files:
            filename = os.path.basename(image_path)
            print(f"\nParsing filename: {filename}")
            
            timestamp = None
            try:
                # Try to extract timestamp from filename (macOS format)
                # Example: Screenshot 2025-04-05 at 9.25.49 PM.png
                match = re.search(r'(\d{4}-\d{2}-\d{2}) at (\d{1,2}\.\d{2}\.\d{2})\s*(AM|PM)?', filename, re.IGNORECASE)
                if match:
                    date_str, time_str, period = match.groups()
                     # Handle potential missing period (common in some locales/versions)
                    if period is None:
                        # Attempt to determine AM/PM based on hour, assuming 24h format if ambiguous
                         try:
                            # Try parsing as 24-hour first
                             dt_obj = datetime.strptime(f"{date_str} {time_str.replace('.', ':')}", "%Y-%m-%d %H:%M:%S")
                             timestamp = dt_obj
                             print(f"Parsed as 24-hour format: {timestamp}")
                         except ValueError:
                             # Fallback or make an assumption - here we'll assume PM for hours > 12 if period is missing
                             # This part might need refinement based on actual filename patterns
                             hours, minutes, seconds = map(int, time_str.split('.'))
                             if hours > 12: # Basic assumption
                                 period = 'PM'
                             else:
                                 period = 'AM' # Default assumption

                    if timestamp is None: # If not parsed as 24h or if period was present
                        hours, minutes, seconds = map(int, time_str.split('.'))
                        if period and period.upper() == 'PM' and hours != 12:
                            hours += 12
                        elif period and period.upper() == 'AM' and hours == 12:
                            hours = 0 # Midnight case
                        timestamp = datetime.strptime(f"{date_str} {hours:02d}:{minutes:02d}:{seconds:02d}",
                                                    "%Y-%m-%d %H:%M:%S")
                        print(f"Successfully parsed timestamp from filename: {timestamp}")

            except Exception as e:
                print(f"Could not parse timestamp from filename '{filename}': {str(e)}")

            # Fallback 1: Use file modification time
            if timestamp is None:
                try:
                    mtime = os.path.getmtime(image_path)
                    timestamp = datetime.fromtimestamp(mtime)
                    print(f"Using file modification time: {timestamp}")
                except Exception as e:
                    print(f"Error getting file modification time: {str(e)}")

            # Fallback 2: Use current time as the last resort
            if timestamp is None:
                timestamp = datetime.now()
                print(f"Using current time as fallback: {timestamp}")
            
            # Ensure timestamp is always a datetime object before creating ImageFrame
            if not isinstance(timestamp, datetime):
                 print(f"Timestamp assignment failed for {filename}, using current time.")
                 timestamp = datetime.now() # Final safety net

            self.image_frames.append(ImageFrame(image_path, timestamp))
        
        # Now sort all frames by timestamp
        self.image_frames.sort(key=lambda x: x.timestamp)
        
        # Update layout
        self.update_layout()
    
    def update_layout(self):
        if not self.image_frames:
            print("No images to layout")
            return
        
        # Clear existing frames
        for frame in self.image_frames:
            if frame.frame:
                frame.frame.destroy()
        
        # Calculate grid dimensions
        num_columns = 3  # Fixed at 3 columns
        num_rows = (len(self.image_frames) + num_columns - 1) // num_columns
        
        # Calculate thumbnail size
        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 1:  # If canvas hasn't been drawn yet
            canvas_width = 800  # Default width
        
        thumbnail_width = (canvas_width - 20) // num_columns  # 20 for padding
        thumbnail_height = int(thumbnail_width * 0.75)  # 4:3 aspect ratio
        
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
        temp_file = "preview.pdf"
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Export to temporary file
        pdf_path = self.export_pdf(temp_file)
        if pdf_path:
            # Open PDF viewer
            if os.name == 'nt':  # Windows
                os.startfile(pdf_path)
            else:  # macOS and Linux
                os.system(f'open "{pdf_path}"')
    
    def export_pdf(self, file_path=None):
        if not self.image_frames:
            print("No images to export")
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
            
            # Use fixed settings
            margin = 10  # Fixed 10pt margin
            num_columns = 3  # Fixed 3 columns
            max_pages = 2  # Fixed 2 pages
            
            usable_width = page_width - 2 * margin
            usable_height = page_height - 2 * margin
            
            print(f"\nPage dimensions:")
            print(f"  Total width: {page_width}pt, height: {page_height}pt")
            print(f"  Usable width: {usable_width}pt, height: {usable_height}pt")
            
            if usable_width <= 0 or usable_height <= 0:
                messagebox.showerror("Export Error", f"Margins ({margin} pts) are too large for the page size.")
                if is_temp_file and os.path.exists(file_path):
                    os.unlink(file_path)
                return None

            # Calculate cell width (fixed for all columns)
            cell_width = usable_width / num_columns
            padding = 10  # Padding between images
            
            print(f"\nColumn layout:")
            print(f"  Number of columns: {num_columns}")
            print(f"  Cell width: {cell_width}pt")
            print(f"  Padding between images: {padding}pt")
            
            # Group images by column
            columns = [[] for _ in range(num_columns)]
            for i, frame in enumerate(self.image_frames):
                col_idx = i % num_columns
                columns[col_idx].append(frame)
            
            print(f"\nImage distribution:")
            for i, col in enumerate(columns):
                print(f"  Column {i+1}: {len(col)} images")
            
            # Process each page
            current_page = 0
            while current_page < max_pages and any(columns):
                if current_page > 0:
                    c.showPage()
                
                print(f"\nProcessing page {current_page + 1}")
                
                # Process each column
                for col_idx, column in enumerate(columns):
                    # Start from top of page
                    y = page_height - margin
                    
                    print(f"\n  Processing column {col_idx + 1}")
                    print(f"    Starting y position: {y}pt")
                    
                    # Process images in column until we run out of space
                    while column and y > margin:
                        frame = column[0]
                        img_width, img_height = frame.original_image.size
                        aspect_ratio = img_height / img_width
                        scaled_width = cell_width * 0.95  # Leave some padding
                        scaled_height = scaled_width * aspect_ratio
                        
                        # Check if image fits
                        if y - scaled_height < margin:
                            break
                        
                        # Calculate x position (centered in column)
                        x = margin + (col_idx * cell_width) + (cell_width - scaled_width) / 2
                        
                        filename = os.path.basename(frame.image_path)
                        print(f"\n    Placing {filename}:")
                        print(f"      Original size: {img_width}x{img_height}")
                        print(f"      Scaled size: {scaled_width:.2f}x{scaled_height:.2f}")
                        print(f"      Position: x={x:.2f}, y={y:.2f}")
                        
                        # Draw border
                        c.setLineWidth(0.5)
                        c.setStrokeColorRGB(0, 0, 0)
                        c.rect(x, y - scaled_height, scaled_width, scaled_height, stroke=1, fill=0)
                        
                        # Draw image
                        c.drawImage(frame.image_path, x, y - scaled_height, width=scaled_width, height=scaled_height)
                        
                        # Draw filename if not preview
                        if not is_temp_file:
                            c.setFont("Helvetica", 6)
                            short_name = filename[:20] + "..." if len(filename) > 20 else filename
                            c.drawString(x + 2, y - scaled_height + 2, short_name)
                        
                        # Update y position for next image
                        y -= (scaled_height + padding)
                        print(f"      Next y position: {y:.2f}pt")
                        
                        # Remove the placed image
                        column.pop(0)
                
                current_page += 1
            
            c.save()
            if not is_temp_file:
                print(f"PDF exported to: {file_path}")
                messagebox.showinfo("Export Successful", f"PDF exported successfully to: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"Error exporting PDF: {str(e)}")
            messagebox.showerror("Export Error", f"An error occurred while exporting the PDF: {str(e)}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Cheat Sheet Creator')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--images', type=str, help='Path to images directory')
    args = parser.parse_args()
    
    root = tk.Tk()
    app = CheatSheetCreator(root)
    
    if args.debug:
        print("Debug mode enabled - will run preview process automatically")
        if args.images:
            app.images_dir = args.images
            app.dir_entry.delete(0, tk.END)
            app.dir_entry.insert(0, args.images)
            app.load_images()
            app.preview_pdf()
    
    root.mainloop()

if __name__ == "__main__":
    main() 