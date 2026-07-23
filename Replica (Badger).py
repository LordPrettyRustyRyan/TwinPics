# UI Improvement - BROKEN

import os
import hashlib
import customtkinter as ctk
import pillow_heif
import tkinter as tk

from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
from send2trash import send2trash

pillow_heif.register_heif_opener()

# ---------- CUSTOMTKINTER SETUP ----------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- Image Hashing (Perceptual Hash) ---
def get_image_hash(image_path):
    try:
        with Image.open(image_path) as img:
            img = img.convert("L").resize((8, 8))
            pixels = list(img.get_flattened_data())
            avg = sum(pixels) / len(pixels)
            diff = "".join("1" if p > avg else "0" for p in pixels)
            return hashlib.md5(diff.encode()).hexdigest()
    except Exception:
        return None

# --- Image Metadata & Sorting ---
def image_quality_key(path):
    with Image.open(path) as img:
        w, h = img.size
    return (w * h, os.path.getsize(path))

def get_image_info(path):
    with Image.open(path) as img:
        w, h = img.size
    
    size_bytes = os.path.getsize(path)
    if size_bytes < 1024 * 1024:
        size = f"{size_bytes / 1024:.1f} KB"
    else:
        size = f"{size_bytes / (1024 * 1024):.2f} MB"
    
    return f"{w}×{h}px | {size}"

# --- Duplicate Discovery ---
def find_duplicates_grouped(image_folder, progress_callback, recursive=False):
    SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")
    image_files = []

    if recursive:
        for root, _, files in os.walk(image_folder):
            for file in files:
                if file.lower().endswith(SUPPORTED_EXTENSIONS):
                    image_files.append(os.path.join(root, file))
    else:
        image_files = [os.path.join(image_folder, f) for f in os.listdir(image_folder) 
                       if f.lower().endswith(SUPPORTED_EXTENSIONS)]

    hashes = {}
    total = len(image_files)

    for i, path in enumerate(image_files, start=1):
        progress_callback(i, total)
        h = get_image_hash(path)
        if h:
            hashes.setdefault(h, []).append(path)

    return {h: files for h, files in hashes.items() if len(files) > 1}

# --- File Operations ---
def move_to_trash(path):
    path = os.path.normpath(os.path.abspath(path))
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    send2trash(path)


# ---------- GUI APP ----------
class DuplicateFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Replica - Duplicate Image Hunter")
        self.minsize(1200, 700)
        # Open maximized by default
        try:
            self.state("zoomed")          # Windows
        except Exception:
            self.attributes("-zoomed", True)   # Linux

        # --- Data State ---
        self.folder = ""
        self.thumbnails = []
        self.duplicate_frames = []
        self.duplicate_files = []
        self.selected_files = {}
        self.original_vars = []
        self.duplicate_vars = []
        self.file_frames = {}
        self.dark_mode = True

        # --- Top Toolbar ---
        self.topbar = ctk.CTkFrame(self)
        self.topbar.pack(fill="x", padx=12, pady=12)
        self.topbar.grid_columnconfigure(0, weight=0)  # Folder
        self.topbar.grid_columnconfigure(1, weight=0)  # Checkbox
        self.topbar.grid_columnconfigure(2, weight=1)  # Progress expands
        self.topbar.grid_columnconfigure(3, weight=0)  # Theme
        self.topbar.grid_columnconfigure(4, weight=0)
        self.topbar.grid_columnconfigure(5, weight=0)
        self.topbar.grid_columnconfigure(6, weight=0)

        self.select_folder_btn = ctk.CTkButton(self.topbar, text="📁 Select Folder", command=self.select_folder, width=150)
        self.select_folder_btn.grid(row=0, column=0, padx=6, pady=8, sticky="ew")

        self.scan_subfolders = ctk.BooleanVar(value=False)
        self.subfolder_checkbox = ctk.CTkCheckBox(self.topbar, text="Subfolder Scan", variable=self.scan_subfolders)
        self.subfolder_checkbox.grid(row=0, column=1, padx=6, sticky="ew")

        self.progress = ctk.CTkProgressBar(self.topbar)
        self.progress.grid(row=0, column=2, sticky="ew", padx=10)
        self.progress.set(0)
        self.theme_btn = ctk.CTkButton(
            self.topbar,
            text="☀ Light Mode",
            width=120,
            command=self.toggle_theme,
        )
        self.theme_btn.grid(row=0, column=3, padx=6, sticky="ew")

        self.clear_batch_btn = ctk.CTkButton(
            self.topbar,
            text="Clear This Batch",
            command=self.clear_batch
        )
        self.clear_batch_btn.grid(row=0, column=4, columnspan=2, padx=4, sticky="ew")

        # Action Buttons (Hidden by default)
        self.rescan_btn = ctk.CTkButton(self.topbar, text="🔄 Rescan", command=self.rescan_folder, width=120)
        self.delete_selected_btn = ctk.CTkButton(self.topbar, text="Delete Selected", command=self.delete_selected, fg_color="#B91C1C", hover_color="#991B1B")
        self.delete_all_btn = ctk.CTkButton(self.topbar, text="Delete All Duplicates", command=self.delete_all_duplicates, fg_color="#DC2626", hover_color="#B91C1C")
        self.select_originals_btn = ctk.CTkButton(self.topbar, text="Select Originals", command=self.select_all_originals)
        self.select_duplicates_btn = ctk.CTkButton(self.topbar, text="Select Duplicates", command=self.select_all_duplicates)
        self.clear_selection_btn = ctk.CTkButton(self.topbar, text="Clear Selection", command=self.clear_selection)

        self.rescan_btn.grid(row=1, column=0, padx=4, sticky="ew")

        self.delete_selected_btn.grid(row=1, column=1, padx=4, sticky="ew")

        self.delete_all_btn.grid(row=1, column=2, padx=4, sticky="ew")

        self.select_originals_btn.grid(row=1, column=3, padx=4, sticky="ew")

        self.select_duplicates_btn.grid(row=1, column=4, padx=4, sticky="ew")

        self.clear_selection_btn.grid(row=1, column=5, padx=4, sticky="ew")
        
        self.hide_action_buttons()

        # --- Scrollable Area ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=12)
        self.scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # --- Button Visibility Logic ---
    def show_action_buttons(self):
        buttons = [self.rescan_btn, self.delete_all_btn, self.delete_selected_btn, 
                   self.select_originals_btn, self.select_duplicates_btn, self.clear_selection_btn, self.clear_batch_btn,]
        for btn in buttons:
            if not btn.winfo_manager():
                btn.grid()

    def hide_action_buttons(self):
        buttons = [self.rescan_btn, self.delete_all_btn, self.delete_selected_btn, 
                   self.select_originals_btn, self.select_duplicates_btn, self.clear_selection_btn, self.clear_batch_btn,]
        for btn in buttons:
            btn.grid_remove()

    # --- Data Management ---
    def clear_results(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        self.duplicate_frames.clear()
        self.duplicate_files.clear()
        self.selected_files.clear()
        self.original_vars.clear()
        self.duplicate_vars.clear()
        self.file_frames.clear()
        self.progress.set(0)

    # --- Folder & Scan Operations ---
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if not folder: return
        self.folder = folder
        self.clear_results()
        self.run_scan()

    def rescan_folder(self):
        if not self.folder: return
        self.clear_results()
        self.run_scan()

    def run_scan(self):
        groups = find_duplicates_grouped(self.folder, self.update_progress, recursive=self.scan_subfolders.get())
        if not groups:
            self.hide_action_buttons()
            messagebox.showinfo("Result", "No duplicates found.")
            return
        self.show_action_buttons()
        self.display_groups(groups)

    def update_progress(self, current, total):
        if total <= 0:
            self.progress.set(0)
            return
        self.progress.set(current / total)
        self.update_idletasks()

    # --- UI Rendering ---
    def display_groups(self, groups):
        for files in groups.values():
            best_path = max(files, key=image_quality_key)
            group_card = ctk.CTkFrame(self.scroll_frame, corner_radius=12)
            group_card.pack(fill="x", 
                            # padx=10, pady=10
                            )

            title = ctk.CTkLabel(group_card, text=f"⭐ Best Image: {os.path.relpath(best_path, self.folder)}", 
                                 font=("Segoe UI", 14, "bold"), anchor="w")
            title.pack(fill="x", 
                    #    padx=12, pady=(10, 5)
                       )

            separator = ctk.CTkFrame(group_card, height=2)
            separator.pack(fill="x", 
                        #    padx=10, pady=(0, 8)
                           )

            for file_path in files:
                if file_path == best_path: continue
                self.duplicate_files.append(file_path)
                self.add_duplicate_row(group_card, best_path, file_path)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode

        if self.dark_mode:
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="☀ Light Mode")
        else:
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="🌙 Dark Mode")

# --- Bulk Selection ---
    def select_all_originals(self):
        self.clear_selection()
        for var in self.original_vars:
            var.set(True)

    def select_all_duplicates(self):
        self.clear_selection()
        for var in self.duplicate_vars:
            var.set(True)

    def clear_selection(self):
        for var in self.selected_files.values():
            var.set(False)

    def clear_batch(self):
        if not self.scroll_frame.winfo_children():
            return

        if not messagebox.askyesno(
            "Clear Batch",
            "Clear the current scan results?"
        ):
            return

        self.clear_results()
        self.hide_action_buttons()

    # --- Thumbnail Management ---
    def load_thumbnail(self, path):
        img = Image.open(path)
        img.thumbnail((120, 120))
        photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.thumbnails.append(photo)
        return photo

    # --- Duplicate Row Generation ---
    def add_duplicate_row(self, parent, orig_path, dup_path):
        available = self.winfo_width()

        card_width = max(
            320,                      # minimum
            min(500, (available - 260) // 2)   # maximum
        )

        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", padx=10, pady=8)
        frame.grid_columnconfigure(0, weight=1, minsize=card_width)
        frame.grid_columnconfigure(1, weight=1, minsize=card_width)
        frame.grid_columnconfigure(2, weight=0, minsize=160)

        img1, img2 = self.load_thumbnail(orig_path), self.load_thumbnail(dup_path)
        orig_var, dup_var = tk.BooleanVar(value=False), tk.BooleanVar(value=False)

        self.selected_files.update({orig_path: orig_var, dup_path: dup_var})
        self.file_frames.update({orig_path: frame, dup_path: frame})
        self.original_vars.append(orig_var)
        self.duplicate_vars.append(dup_var)

        # Columns for Original, Duplicate, and Action Panel
        for i, (path, var, img) in enumerate([(orig_path, orig_var, img1), (dup_path, dup_var, img2)]):
            col = ctk.CTkFrame(frame, fg_color="transparent", width=card_width)
            col.grid_propagate(False)
            col.configure(height=140)      # optional
            col.grid(row=0, column=i, sticky="nsew", padx=8, pady=8)
            
            ctk.CTkLabel(col, image=img, text="").pack(side="left", padx=8)
            
            meta = ctk.CTkFrame(col, fg_color="transparent")
            meta.pack(side="left", fill="both", expand=True)
            
            # ctk.CTkCheckBox(meta, text="Select", variable=var).pack(anchor="w")
            ctk.CTkLabel(
                meta,
                text=os.path.relpath(path, self.folder),
                wraplength=card_width - 40,
                justify="left",
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(anchor="w", fill="x")
            ctk.CTkLabel(meta, text=get_image_info(path)).pack(anchor="w")
            
            # Controls Row
            controls = ctk.CTkFrame(meta, fg_color="transparent")
            controls.pack(anchor="w", pady=(0, 6))

            ctk.CTkCheckBox( controls, text="Select", variable=var ).pack(side="left")
            ctk.CTkButton(controls, text="Delete", width=90, fg_color="#d9534f", hover_color="#c9302c", command=lambda p=path, f=frame: self.delete_file(p, f)).pack(side="left", padx=(10, 0))

        # Action Column
        action_col = ctk.CTkFrame(frame, fg_color="transparent")
        action_col.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkButton(
            action_col,
            text="Preview",
            width=160,
            command=lambda: self.open_preview(orig_path, dup_path)
        ).pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            action_col,
            text="Skip",
            width=160,
            fg_color="#666666",
            hover_color="#555555",
            command=lambda: self.skip_pair(frame, dup_path)
        ).pack(fill="x")

        return frame

    # --- File Operations ---
    def delete_selected(self):
        paths_to_delete = [path for path, var in self.selected_files.items() if var.get()]
        if not paths_to_delete:
            messagebox.showinfo("Info", "No files selected.")
            return

        if not messagebox.askyesno("Confirm", f"Move {len(paths_to_delete)} selected images to Recycle Bin?"):
            return

        deleted = 0
        for path in paths_to_delete:
            try:
                move_to_trash(path)
                self.duplicate_files = [f for f in self.duplicate_files if f != path]
                if path in self.selected_files: del self.selected_files[path]
                deleted += 1
            except Exception as e:
                print(f"Error deleting {path}: {e}")

        messagebox.showinfo("Done", f"{deleted} image(s) moved to Recycle Bin.")
        self.rescan_folder()

    def delete_all_duplicates(self):
        if not self.duplicate_files:
            messagebox.showinfo("Info", "No duplicates to delete.")
            return

        if not messagebox.askyesno("Confirm", f"Move ALL {len(self.duplicate_files)} duplicate images to Recycle Bin?"):
            return

        for path in list(self.duplicate_files):
            try:
                move_to_trash(path)
            except Exception as e:
                messagebox.showerror("Error", f"Couldn't move file to Recycle Bin:\n{e}")

        messagebox.showinfo("Done", "All duplicates moved to Recycle Bin.")
        self.rescan_folder()

    def delete_file(self, filename, frame):
        path = os.path.normpath(os.path.abspath(filename))
        if not messagebox.askyesno("Confirm", f"Delete {os.path.basename(filename)}?"):
            return

        try:
            move_to_trash(path)
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't move file to Recycle Bin:\n{e}")
            return

        if path in self.duplicate_files: self.duplicate_files.remove(path)
        if path in self.selected_files: del self.selected_files[path]
        self.rescan_folder()

    def skip_pair(self, frame, dup_path):
        if dup_path in self.duplicate_files:
            self.duplicate_files.remove(dup_path)
        frame.destroy()

    # --- Preview Window ---
    def open_preview(self, img1_path, img2_path):
        win = ctk.CTkToplevel(self)
        win.transient(self)
        win.lift()
        win.focus_force()

        win.attributes("-topmost", True)
        win.after(150, lambda: win.attributes("-topmost", False))
        win.title("Image Preview")
        win.state("zoomed") if hasattr(win, "state") else win.attributes("-fullscreen", True)

        container = ctk.CTkFrame(win)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        canvases, images = [], []
        for path in (img1_path, img2_path):
            canvas = tk.Canvas(container, bg="black", highlightthickness=0)
            canvas.pack(side="left", fill="both", expand=True, padx=5)
            canvases.append(canvas)
            images.append(Image.open(path))

        zoom, offset = tk.DoubleVar(value=0.75), {"x": 0, "y": 0}

        def redraw():
            for canvas, img in zip(canvases, images):
                canvas.delete("all")
                z = zoom.get()
                resized = img.resize((int(img.width * z), int(img.height * z)))
                photo = ImageTk.PhotoImage(resized)
                canvas.image = photo
                canvas.create_image(canvas.winfo_width() // 2 + offset["x"], 
                                    canvas.winfo_height() // 2 + offset["y"], image=photo)

        # Drag & Zoom bindings
        for canvas in canvases:
            canvas.bind("<ButtonPress-1>", lambda e: (setattr(e.widget, "drag_x", e.x), setattr(e.widget, "drag_y", e.y)))
            canvas.bind("<B1-Motion>", lambda e: (offset.update({"x": offset["x"] + (e.x - e.widget.drag_x), 
                                                                "y": offset["y"] + (e.y - e.widget.drag_y)}), 
                                                redraw(), setattr(e.widget, "drag_x", e.x), setattr(e.widget, "drag_y", e.y)))
            canvas.bind("<MouseWheel>", lambda e: (zoom.set(max(0.2, min(4.0, zoom.get() * (1.1 if e.delta > 0 else 0.9)))), redraw()))

        # Controls
        slider_frame = ctk.CTkFrame(win)
        slider_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(slider_frame, text="Zoom").pack(side="left", padx=10)
        ctk.CTkSlider(slider_frame, from_=0.2, to=4.0, variable=zoom, command=lambda v: redraw()).pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(slider_frame, text="Close", width=100, command=win.destroy).pack(side="right", padx=10)
        
        win.bind("<Configure>", lambda e: redraw())
        redraw()

# --- Main Entry Point ---
if __name__ == "__main__":
    app = DuplicateFinderApp()
    app.mainloop()