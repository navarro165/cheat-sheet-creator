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

class ImageFrame(ttk.Frame):
    def __init__(self, parent, image_path, app):
        super().__init__(parent, borderwidth=1, relief=tk.SOLID)
        self.app = app
        self.image_path = image_path
        self.original_image = Image.open(image_path)
        self.photo = None
        self.image_label = ttk.Label(self, anchor='nw')
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Create delete button
        self.delete_button = ttk.Button(self, text="×", width=3, 
                                      command=self.on_delete)
        self.delete_button.place(relx=1.0, rely=0.0, anchor="ne")
        self.delete_button.place_forget()
        
        # Bind hover events
        self.bind("<Enter>", self.show_delete)
        self.bind("<Leave>", self.hide_delete)
        self.image_label.bind("<Enter>", self.show_delete)
        self.image_label.bind("<Leave>", self.hide_delete)
        
    def on_delete(self):
        self.app.remove_image(self)
        self.destroy()
        
    def show_delete(self, event=None):
        self.delete_button.place(relx=1.0, rely=0.0, anchor="ne")
        
    def hide_delete(self, event=None):
        self.delete_button.place_forget()
        
    def update_size(self, width, height):
        if width <= 0 or height <= 0:
            return
            
        # Calculate aspect ratio
        orig_width, orig_height = self.original_image.size
        aspect_ratio = orig_width / orig_height
        
        # Calculate new dimensions while maintaining aspect ratio
        if width / height > aspect_ratio:
            new_width = int(height * aspect_ratio)
            new_height = height
        else:
            new_width = width
            new_height = int(width / aspect_ratio)
        
        # Resize image
        resized_image = self.original_image.resize((new_width, new_height), 
                                                 Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized_image)
        self.image_label.configure(image=self.photo)

class CheatSheetCreator:
    def __init__(self, root):
        self.root = root
        self.root.title("Cheat Sheet Creator")
        
        # Set timeout for debugging
        self.timeout_thread = threading.Thread(target=self._timeout_check)
        self.timeout_thread.daemon = True
        self.timeout_thread.start()
        
        # Set window size to match letter size (8.5x11 inches) plus some padding for controls
        # Convert inches to pixels (assuming 96 DPI)
        self.page_width = int(8.5 * 96)
        self.page_height = int(11 * 96)
        self.window_width = self.page_width + 40  # Add padding for scrollbar and margins
        self.window_height = self.page_height + 100  # Add space for controls
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        
        # Create main frame
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Column control
        ttk.Label(controls_frame, text="Columns:").pack(side=tk.LEFT, padx=5)
        self.column_var = tk.StringVar(value="3")  # Default to 3 columns
        self.column_var.trace_add("write", lambda *args: self.update_layout())
        column_combo = ttk.Combobox(controls_frame, 
                                  values=["Auto", "1", "2", "3", "4"],
                                  width=5,
                                  textvariable=self.column_var,
                                  state="readonly")
        column_combo.pack(side=tk.LEFT, padx=5)
        
        # Page control
        ttk.Label(controls_frame, text="Pages:").pack(side=tk.LEFT, padx=5)
        self.page_var = tk.IntVar(value=2)  # Default to 2 pages
        self.page_var.trace_add("write", lambda *args: self.update_layout())
        page_spin = ttk.Spinbox(controls_frame, from_=1, to=10, 
                              width=5, textvariable=self.page_var)
        page_spin.pack(side=tk.LEFT, padx=5)
        
        # Page navigation
        self.current_page = tk.IntVar(value=1)
        ttk.Label(controls_frame, text="Current Page:").pack(side=tk.LEFT, padx=5)
        self.page_label = ttk.Label(controls_frame, textvariable=self.current_page)
        self.page_label.pack(side=tk.LEFT)
        
        prev_button = ttk.Button(controls_frame, text="←", width=3,
                               command=self.prev_page)
        prev_button.pack(side=tk.LEFT, padx=2)
        
        next_button = ttk.Button(controls_frame, text="→", width=3,
                               command=self.next_page)
        next_button.pack(side=tk.LEFT, padx=2)

        # Margin control
        ttk.Label(controls_frame, text="Margin (pts):", ).pack(side=tk.LEFT, padx=(15, 5))
        self.margin_var = tk.IntVar(value=10)  # Default to 10 points margin
        margin_spin = ttk.Spinbox(controls_frame, from_=0, to=144, 
                                width=5, textvariable=self.margin_var)
        margin_spin.pack(side=tk.LEFT, padx=5)
        # Note: Margin changes don't dynamically update the Tkinter layout preview,
        # only the PDF output/preview.

        # Export button
        preview_button = ttk.Button(controls_frame, text="Preview PDF",
                                 command=self.preview_pdf)
        preview_button.pack(side=tk.RIGHT, padx=5)
        
        # Add Export PDF button
        export_button = ttk.Button(controls_frame, text="Export PDF",
                                 command=self.export_pdf)
        export_button.pack(side=tk.RIGHT, padx=5)
        
        # Create page frame (fixed size to match actual page)
        self.page_frame = ttk.Frame(main_frame, width=self.page_width, height=self.page_height)
        self.page_frame.pack_propagate(False)  # Prevent frame from shrinking
        self.page_frame.pack(pady=10)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(self.page_frame, bg='white', 
                              width=self.page_width, height=self.page_height)
        self.scrollbar = ttk.Scrollbar(self.page_frame, orient=tk.VERTICAL, 
                                     command=self.canvas.yview)
        
        # Image container frame
        self.image_frame = ttk.Frame(self.canvas)
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_window = self.canvas.create_window(
            (0, 0), 
            window=self.image_frame, 
            anchor=tk.NW,
            tags='self.image_frame'
        )
        
        # Pack scrollable components
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure weights
        self.page_frame.grid_columnconfigure(0, weight=1)
        self.page_frame.grid_rowconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(0, weight=1)
        self.image_frame.grid_rowconfigure(0, weight=1)
        
        # Bind events
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.image_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Load images
        self.image_frames = []
        self.after_id = None
        self.load_images()
        
    def _on_canvas_configure(self, event):
        # Update the scroll region to encompass the inner frame
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # Resize the inner frame to match canvas width
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.after_id = self.root.after(100, self.update_layout)
        
    def _on_frame_configure(self, event=None):
        # Reset the scroll region to encompass the inner frame
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def calculate_optimal_columns(self, num_images, num_pages):
        if num_images == 0:
            return 1
            
        # Calculate total cells needed
        total_cells = num_images
        
        # Calculate cells per page
        cells_per_page = ceil(total_cells / num_pages)
        
        # Calculate optimal grid dimensions
        # We want a grid that's as close to square as possible
        # but with more columns than rows for better readability
        optimal_columns = ceil(sqrt(cells_per_page * 1.5))
        
        # Limit to reasonable number of columns
        return min(max(1, optimal_columns), 4)

    def update_layout(self):
        if not self.image_frames:
            print("No images to layout")
            return
            
        print(f"Updating layout with {len(self.image_frames)} total images")
        print(f"Current page: {self.current_page.get()}, Total pages: {self.page_var.get()}")
            
        # Hide all frames first
        for frame in self.image_frames:
            frame.grid_remove()
            
        # Calculate images per page
        total_pages = max(1, self.page_var.get())
        images_per_page = ceil(len(self.image_frames) / total_pages)
        current_page = min(self.current_page.get(), total_pages)
        
        # Get images for current page
        start_idx = (current_page - 1) * images_per_page
        end_idx = min(start_idx + images_per_page, len(self.image_frames))
        current_frames = self.image_frames[start_idx:end_idx]
        
        print(f"\nDebug - Grid Order:")
        # Print the filenames in the order they're stored in the list
        for i, frame in enumerate(current_frames):
            filename = os.path.basename(frame.image_path)
            print(f"  Position {i+1}: {filename}")
        
        # Calculate number of columns
        if self.column_var.get() == "Auto":
            num_columns = self.calculate_optimal_columns(len(current_frames), total_pages)
        else:
            num_columns = int(self.column_var.get())
            
        print(f"Using {num_columns} columns")
        
        # Calculate number of rows
        num_rows = (len(current_frames) + num_columns - 1) // num_columns
        
        print(f"Grid: {num_rows} rows x {num_columns} columns")
        
        # Calculate cell dimensions (maximum available space)
        cell_width = max(1, self.page_width // num_columns)
        cell_height = max(1, self.page_height // num_rows)
        
        print(f"Max Cell size: {cell_width}x{cell_height}")
        
        # Update grid configuration - only configure columns to expand
        for i in range(num_columns):
            self.image_frame.columnconfigure(i, weight=1)
        # Remove row weight configuration to prevent vertical expansion
        # for i in range(num_rows):
        #     self.image_frame.rowconfigure(i, weight=1)
        
        # Place frames in grid and update their sizes
        for i, frame in enumerate(current_frames):
            row = i // num_columns
            col = i % num_columns
            print(f"  Placing {os.path.basename(frame.image_path)} at row {row}, col {col} (grid position {row*num_columns+col+1})")
            # Use minimal padding in auto mode
            padx = 1 if self.column_var.get() == "Auto" else 2
            pady = 1 if self.column_var.get() == "Auto" else 2
            frame.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")
            # Update size based on calculated cell dimensions, image will fit itself
            frame.update_size(cell_width - (padx * 2), cell_height - (pady * 2))
        
        # Update scroll region
        self.canvas.update_idletasks()
        self._on_frame_configure()
        
    def remove_image(self, frame):
        if frame in self.image_frames:
            self.image_frames.remove(frame)
        self.update_layout()
        
    def prev_page(self):
        if self.current_page.get() > 1:
            self.current_page.set(self.current_page.get() - 1)
            self.update_layout()
            
    def next_page(self):
        if self.current_page.get() < self.page_var.get():
            self.current_page.set(self.current_page.get() + 1)
            self.update_layout()
        
    def _timeout_check(self):
        """Force exit after 30 seconds for debugging purposes"""
        time.sleep(30)
        print("\nTimeout reached - forcing exit for debugging")
        os._exit(1)

    def load_images(self):
        """Load images from the reference_images directory"""
        self.images = []
        self.reference_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference_images")
        
        if not os.path.exists(self.reference_images_dir):
            os.makedirs(self.reference_images_dir)
            return
        
        for filename in os.listdir(self.reference_images_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                path = os.path.join(self.reference_images_dir, filename)
                try:
                    # Parse timestamp from filename format: "Screenshot YYYY-MM-DD at H.MM.SS [AM/PM].png"
                    print(f"\nParsing filename: {filename}")
                    parts = filename.split()
                    if len(parts) >= 5 and parts[0] == "Screenshot":
                        date_str = parts[1]  # YYYY-MM-DD
                        time_str = parts[3]  # H.MM.SS
                        ampm = parts[4].split('.')[0]  # AM/PM
                        
                        # Parse date
                        year, month, day = map(int, date_str.split('-'))
                        
                        # Parse time
                        hour, minute, second = map(int, time_str.split('.'))
                        
                        # Convert to 24-hour format
                        if ampm.upper() == "PM" and hour < 12:
                            hour += 12
                        elif ampm.upper() == "AM" and hour == 12:
                            hour = 0
                        
                        # Create datetime object
                        timestamp = datetime(year, month, day, hour, minute, second)
                        print(f"Successfully parsed timestamp: {timestamp}")
                    else:
                        # Fallback to file creation time if parsing fails
                        timestamp = datetime.fromtimestamp(os.path.getctime(path))
                        print(f"Using file creation time instead: {timestamp}")
                    
                    self.images.append((path, timestamp))
                except Exception as e:
                    print(f"Error parsing timestamp from {filename}: {str(e)}")
                    # Fallback to file creation time
                    timestamp = datetime.fromtimestamp(os.path.getctime(path))
                    print(f"Using file creation time instead: {timestamp}")
                    self.images.append((path, timestamp))
        
        # Sort images by timestamp (oldest first)
        self.images.sort(key=lambda x: x[1])  # Show oldest first
        
        # Print sorted order for debugging
        print("\nImages sorted by timestamp (oldest first):")
        for i, (path, timestamp) in enumerate(self.images, 1):
            print(f"{i}. {os.path.basename(path)} - {timestamp}")
        
        # Create image frames in the sorted order
        for path, _ in self.images:
            frame = ImageFrame(self.image_frame, path, self)
            self.image_frames.append(frame)
            
        self.update_layout()
        
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
            
            # Calculate margins (use variable)
            margin = self.margin_var.get()
            if margin < 0: margin = 0 # Ensure non-negative margin
            usable_width = page_width - 2 * margin
            usable_height = page_height - 2 * margin
            
            # Ensure usable dimensions are positive
            if usable_width <= 0 or usable_height <= 0:
                messagebox.showerror("Export Error", f"Margins ({margin} pts) are too large for the page size.")
                if is_temp_file and os.path.exists(file_path):
                     os.unlink(file_path) # Clean up temp file on error
                return None

            total_pages = self.page_var.get()
            
            # Debug: Print the order of all images before PDF generation
            print("\nPDF Debug - All images in order:")
            for i, frame in enumerate(self.image_frames):
                print(f"  {i+1}. {os.path.basename(frame.image_path)}")
            
            # For multi-page PDFs, use a sequential approach to assign images to pages
            # Calculate images per page
            images_per_page = ceil(len(self.image_frames) / total_pages)
            
            # Calculate number of columns
            if self.column_var.get() == "Auto":
                num_columns = self.calculate_optimal_columns(len(self.image_frames), total_pages)
            else:
                num_columns = int(self.column_var.get())
                
            print(f"\nPDF Layout: {total_pages} pages, {num_columns} columns, {images_per_page} images per page")
            
            # Process each page
            for page in range(total_pages):
                if page > 0:
                    c.showPage()
                
                # Get images for this page (sequential slicing)
                start_idx = page * images_per_page
                end_idx = min(start_idx + images_per_page, len(self.image_frames))
                page_frames = self.image_frames[start_idx:end_idx]
                
                print(f"\nPDF Page {page+1} - Images:")
                for i, frame in enumerate(page_frames):
                    print(f"  {start_idx+i+1}. {os.path.basename(frame.image_path)}")
                
                # Calculate number of rows needed for this page
                num_rows = ceil(len(page_frames) / num_columns)
                
                # Calculate cell dimensions
                cell_width = usable_width / num_columns
                cell_height = usable_height / num_rows
                
                # Place images in grid (left-to-right, top-to-bottom)
                for i, frame in enumerate(page_frames):
                    # Calculate grid position
                    row = i // num_columns
                    col = i % num_columns
                    
                    print(f"  Placing {os.path.basename(frame.image_path)} at row {row}, col {col}")
                    
                    # Draw border rectangle
                    border_x = margin + (col * cell_width)
                    border_y = page_height - margin - ((row + 1) * cell_height)
                    c.setLineWidth(0.5) # Thin line
                    c.setStrokeColorRGB(0, 0, 0) # Black
                    c.rect(border_x, border_y, cell_width, cell_height, stroke=1, fill=0)
                    
                    # Calculate image size while maintaining aspect ratio
                    img_width, img_height = frame.original_image.size
                    aspect_ratio = img_width / img_height
                    
                    if cell_width / cell_height > aspect_ratio:
                        img_height = cell_height
                        img_width = cell_height * aspect_ratio
                    else:
                        img_width = cell_width
                        img_height = cell_width / aspect_ratio
                    
                    # Align image top-left within the cell
                    x = margin + (col * cell_width)
                    y = page_height - margin - (row * cell_height) - img_height
                    
                    # Draw image
                    c.drawImage(frame.image_path, x, y, width=img_width, height=img_height)
                    
                    # Draw filename for debugging (small text at bottom of cell)
                    if not is_temp_file:  # Only in final export
                        c.setFont("Helvetica", 6)
                        filename = os.path.basename(frame.image_path)
                        short_name = filename[:20] + "..." if len(filename) > 20 else filename
                        c.drawString(border_x + 2, border_y + 2, short_name)
            
            c.save()
            if not is_temp_file:
                print(f"PDF exported to: {file_path}")
                messagebox.showinfo("Export Successful", f"PDF exported successfully to: {file_path}")
            return file_path
        except Exception as e:
            print(f"Error exporting PDF: {str(e)}")
            messagebox.showerror("Export Error", f"An error occurred while exporting the PDF: {str(e)}")
            return None

    def preview_pdf(self):
        if not self.image_frames:
            messagebox.showwarning("No Images", "There are no images to preview.")
            return

        # Create a temporary file
        try:
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_pdf_path = temp_pdf.name
            temp_pdf.close() # Close the file handle immediately

            # Export to the temporary file path
            exported_path = self.export_pdf(file_path=temp_pdf_path)

            if exported_path:
                # Open the temporary PDF file using the default system viewer
                try:
                    current_platform = platform.system()
                    if current_platform == "Windows":
                        os.startfile(exported_path)
                    elif current_platform == "Darwin": # macOS
                        subprocess.run(["open", exported_path], check=True)
                    else: # Linux and other Unix-like systems
                        subprocess.run(["xdg-open", exported_path], check=True)
                except FileNotFoundError:
                    messagebox.showerror("Preview Error", f"Could not find a PDF viewer. Please open the file manually: {exported_path}")
                except Exception as e:
                    messagebox.showerror("Preview Error", f"Could not open PDF viewer: {str(e)} Please open the file manually: {exported_path}")
            else:
                # Export failed, try to clean up temp file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not create temporary file for preview: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CheatSheetCreator(root)
    root.mainloop() 