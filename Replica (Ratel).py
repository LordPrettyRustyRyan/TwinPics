import os
import hashlib
import tkinter as tk
import pillow_heif
from PIL import Image, ImageTk
from tkinter import ttk, filedialog, messagebox
from send2trash import send2trash

pillow_heif.register_heif_opener()

# ---------- IMAGE HASH ----------
def get_image_hash(image_path):
    try:
        with Image.open(image_path) as img:
            img = img.convert("L").resize((8, 8))
            pixels = list(img.get_flattened_data())
            avg_pixel = sum(pixels) / len(pixels)
            diff = "".join("1" if p > avg_pixel else "0" for p in pixels)
            return hashlib.md5(diff.encode()).hexdigest()
    except Exception:
        return None

# ---------- IMAGE QUALITY ----------
def image_quality_key(path):
    with Image.open(path) as img:
        w, h = img.size
    return (w * h, os.path.getsize(path))

# ---------- FIND DUPLICATES ----------
def find_duplicates_grouped(image_folder, progress_callback, recursive=False):
    SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")

    image_files = []

    if recursive:

        for root, dirs, files in os.walk(image_folder):

            for file in files:

                if file.lower().endswith(
                    SUPPORTED_EXTENSIONS
                ):

                    image_files.append(
                        os.path.join(root, file)
                    )

    else:

        image_files = [

            os.path.join(image_folder, f)

            for f in os.listdir(image_folder)

            if f.lower().endswith(
                SUPPORTED_EXTENSIONS
            )
        ]

    hashes = {}
    total = len(image_files)

    for i, path in enumerate(
        image_files,
        start=1
    ):

        progress_callback(i, total)

        try:
            h = get_image_hash(path)

        except:
            continue

        hashes.setdefault(h, []).append(path)

    return {
        h: files
        for h, files in hashes.items()
        if len(files) > 1
    }

# ---------- FIXED PATH TRASHING ----------
def move_to_trash(path):
    path = os.path.abspath(path)
    path = os.path.normpath(path)

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    send2trash(path)

# ---------- IMAGE INFO ----------
def get_image_info(path):
    with Image.open(path) as img:
        w, h = img.size
    size = os.path.getsize(path)
    size = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.2f} MB"
    return f"{w}×{h}px | {size}"

# ---------- GUI APP ----------
class DuplicateFinderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Replica - Duplicate Image Hunter")
        self.geometry("950x650")
        self.folder = ""
        self.thumbnails = []
        self.duplicate_frames = []  # store frames for delete all duplicates
        self.dark_mode = False
        self.duplicate_files = []
        self.selected_files = {}     # path -> BooleanVar
        self.original_vars = []      # all original image checkboxes
        self.duplicate_vars = []     # all duplicate image checkboxes
        self.file_frames = {}
        
        self.minsize(750, 650)       # Minimum window size

        # ---- TOP BAR ----
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)

        # Row 1
        top_row1 = tk.Frame(top)
        top_row1.pack(fill="x")

        # Row 2
        top_row2 = tk.Frame(top)
        top_row2.pack(fill="x", pady=(6, 0))

        tk.Button(
            top_row1,
            text="Select Folder",
            command=self.select_folder
        ).pack(side="left", padx=5)

        self.scan_subfolders = tk.BooleanVar(value=False)
        tk.Checkbutton(
            top_row1,
            text="Subfolder Scan",
            variable=self.scan_subfolders
        ).pack(side="left", padx=5)

        self.progress = ttk.Progressbar(top_row1)
        self.progress.pack(side="left", fill="x", expand=True, padx=10)
        self.duplicate_files.clear()

        # Delete All Duplicates button (initially hidden)
        self.delete_all_btn = tk.Button(top_row2, text="Delete All Duplicates", command=self.delete_all_duplicates)
        self.delete_all_btn.pack(side="left", padx=5)
        self.delete_all_btn.pack_forget()  # hide initially

        # Re-Scan
        self.rescan_btn = tk.Button(
            top_row2,
            text="Rescan",
            command=self.rescan_folder
        )
        self.rescan_btn.pack(side="left", padx=5)
        self.rescan_btn.pack_forget()

        # Clear Batch
        self.clear_batch_btn = tk.Button(
            top_row2,
            text="Clear This Batch",
            command=self.clear_batch
        )
        self.clear_batch_btn.pack(side="left", padx=5)
        self.clear_batch_btn.pack_forget()

        # Delete Selected
        self.delete_selected_btn = tk.Button(
            top_row2,
            text="Delete Selected",
            command=self.delete_selected
        )
        self.delete_selected_btn.pack(side="left", padx=5)
        self.delete_selected_btn.pack_forget()  # hide initially

        # Select Originals
        self.select_originals_btn = tk.Button(
            top_row2,
            text="Select All Originals",
            command=self.select_all_originals
        )
        self.select_originals_btn.pack(side="left", padx=5)
        self.select_originals_btn.pack_forget()  # hide initially

        # Select Duplicates
        self.select_duplicates_btn = tk.Button(
            top_row2,
            text="Select All Duplicates",
            command=self.select_all_duplicates
        )
        self.select_duplicates_btn.pack(side="left", padx=5)
        self.select_duplicates_btn.pack_forget()  # hide initially

        # Clear Selection
        self.clear_selection_btn = tk.Button(
            top_row2,
            text="Clear Selection",
            command=self.clear_selection
        )
        self.clear_selection_btn.pack(side="left", padx=5)
        self.clear_selection_btn.pack_forget()  # hide initially

        # Dark mode toggle
        self.dark_mode_btn = tk.Button(top_row1, text="Dark Mode", command=self.toggle_dark_mode)
        self.dark_mode_btn.pack(side="left", padx=5)

        # ---- SCROLLABLE AREA ----
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_scroll_frame)

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # ---- MOUSE WHEEL SCROLLING ----
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    # ---------- SCROLL METHODS ----------
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _update_scroll_region(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_scroll_frame(self, event):
        self.canvas.itemconfig(1, width=event.width)

    # ---------- FOLDER SELECTION ----------
    def select_folder(self):
        self.folder = filedialog.askdirectory(title="Select Image Folder")
        if not self.folder:
            return

        # Clear previous content
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        self.duplicate_frames.clear()
        self.duplicate_files.clear()
        self.selected_files.clear()
        self.original_vars.clear()
        self.duplicate_vars.clear()
        self.progress["value"] = 0
        self.update()

        groups = find_duplicates_grouped(
            self.folder,
            self.update_progress,
            recursive=self.scan_subfolders.get()
        )
        if not groups:
            messagebox.showinfo("Result", "No duplicates found.")
            self.rescan_btn.pack(side="left", padx=5) # hide button
            self.delete_all_btn.pack_forget()
            self.delete_selected_btn.pack_forget()
            self.select_originals_btn.pack_forget()
            self.select_duplicates_btn.pack_forget()
            self.clear_selection_btn.pack_forget()
            self.clear_batch_btn.pack_forget()
            return

        # Show delete all duplicates button
        self.rescan_btn.pack(side="left", padx=5)
        self.delete_all_btn.pack(side="left", padx=5)
        self.delete_selected_btn.pack(side="left", padx=5)
        self.select_originals_btn.pack(side="left", padx=5)
        self.select_duplicates_btn.pack(side="left", padx=5)
        self.clear_selection_btn.pack(side="left", padx=5)
        self.clear_batch_btn.pack(side="left", padx=5)
        self.display_groups(groups)

    def update_progress(self, current, total):
        self.progress["maximum"] = total
        self.progress["value"] = current
        self.update_idletasks()

    # ---------- RESCAN ----------
    def rescan_folder(self):
        if not self.folder:
            return

        # Clear UI
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.thumbnails.clear()
        self.duplicate_frames.clear()
        self.duplicate_files.clear()
        self.selected_files.clear()
        self.original_vars.clear()
        self.duplicate_vars.clear()
        self.file_frames.clear()

        self.progress["value"] = 0
        self.update()

        groups = find_duplicates_grouped(
            self.folder,
            self.update_progress,
            recursive=self.scan_subfolders.get()
        )

        if not groups:

            self.delete_all_btn.pack_forget()
            self.delete_selected_btn.pack_forget()
            self.select_originals_btn.pack_forget()
            self.select_duplicates_btn.pack_forget()
            self.clear_selection_btn.pack_forget()

            messagebox.showinfo(
                "Done",
                "No duplicates remain."
            )

            return

        self.display_groups(groups)

    def clear_batch(self):
        # Remove everything from the UI
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Reset stored data
        self.thumbnails.clear()
        self.duplicate_frames.clear()
        self.duplicate_files.clear()
        self.selected_files.clear()
        self.original_vars.clear()
        self.duplicate_vars.clear()
        self.file_frames.clear()

        # Reset progress bar
        self.progress["value"] = 0

        # Hide action buttons
        self.delete_all_btn.pack_forget()
        self.delete_selected_btn.pack_forget()
        self.select_originals_btn.pack_forget()
        self.select_duplicates_btn.pack_forget()
        self.clear_selection_btn.pack_forget()
        self.rescan_btn.pack_forget()
        self.clear_batch_btn.pack_forget()

        # Keep the folder path so Rescan can still work if desired.
        # If you want to force choosing a new folder next time,
        # uncomment the next line.
        # self.folder = ""

        self.update_idletasks()

    # ---------- DISPLAY GROUPS ----------
    def display_groups(self, groups):
        for files in groups.values():
            paths = files
            best_path = max(paths, key=image_quality_key)
            best_file = best_path

            group = tk.LabelFrame(
                self.scroll_frame,
                text=f"Best One: {os.path.relpath(best_file, self.folder)}",
                padx=5,
                pady=5
            )
            group.pack(fill="x", padx=10, pady=10)

            # for f in files:
            #     if f != best_file:
            #         frame = self.add_duplicate_row(group, best_file, f)
            #         self.duplicate_frames.append(frame)

            for f in files:
                if f != best_file:
                    dup_path = f
                    self.duplicate_files.append(dup_path)
                    self.add_duplicate_row(group, best_file, f)


        # Apply dark mode to newly created rows
        if self.dark_mode:
            self.apply_dark_mode_recursive(self.scroll_frame)

    # ---------- DUPLICATE ROW ----------
    def add_duplicate_row(self, parent, orig, dup):
        frame = tk.Frame(parent, bd=1, relief="solid")
        frame.pack(fill="x", pady=5, padx=5)

        # ---- Configure columns with 2:2:1 ratio ----
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=2)
        frame.columnconfigure(2, weight=1, minsize=120)

        # ---- Paths ----
        orig_path = orig
        dup_path = dup

        img1 = self.load_thumbnail(orig_path)
        img2 = self.load_thumbnail(dup_path)

        orig_var = tk.BooleanVar(value=False)
        dup_var = tk.BooleanVar(value=False)

        self.selected_files[orig_path] = orig_var
        self.selected_files[dup_path] = dup_var

        self.file_frames[orig_path] = frame
        self.file_frames[dup_path] = frame

        self.original_vars.append(orig_var)
        self.duplicate_vars.append(dup_var)

        # ---- Original column ----
        orig_col = tk.Frame(frame)
        orig_col.grid(row=0, column=0, sticky="nsew", padx=5)
        tk.Label(orig_col, image=img1).pack(side="left", padx=5, pady=5)
        meta1 = tk.Frame(orig_col)
        meta1.pack(side="left", fill="y")
        tk.Label(meta1, text=os.path.relpath(orig_path, self.folder), font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w")
        tk.Label(meta1, text=get_image_info(orig_path), anchor="w").pack(anchor="w")

        # Row for Select + Delete
        action_row = tk.Frame(meta1)
        action_row.pack(anchor="w", pady=2)

        tk.Checkbutton(
            action_row,
            text="Select",
            variable=orig_var
        ).pack(side="left")

        tk.Button(
            action_row,
            text="Delete",
            command=lambda: self.delete_file(orig_path, frame)
        ).pack(side="left", padx=(8, 0))

        # ---- Duplicate column ----
        dup_col = tk.Frame(frame)
        dup_col.grid(row=0, column=1, sticky="nsew", padx=5)
        tk.Label(dup_col, image=img2).pack(side="left", padx=5, pady=5)
        meta2 = tk.Frame(dup_col)
        meta2.pack(side="left", fill="y")
        tk.Label(meta2, text=os.path.relpath(dup_path, self.folder), font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w")
        tk.Label(meta2, text=get_image_info(dup_path), anchor="w").pack(anchor="w")

        # Row for Select + Delete
        action_row = tk.Frame(meta2)
        action_row.pack(anchor="w", pady=2)

        tk.Checkbutton(
            action_row,
            text="Select",
            variable=dup_var
        ).pack(side="left")

        tk.Button(
            action_row,
            text="Delete",
            command=lambda: self.delete_file(dup_path, frame)
        ).pack(side="left", padx=(8, 0))

        # ---- Preview column ----
        preview_col = tk.Frame(frame)
        preview_col.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        tk.Button(
            preview_col,
            text="Preview",
            command=lambda: self.open_preview(orig_path, dup_path)
        ).pack(fill="x", pady=2)

        tk.Button(
            preview_col,
            text="Skip",
            command=lambda: self.skip_pair(frame, dup_path)
        ).pack(fill="x", pady=2)

        return frame


    # ---------- DARK MODE ----------
    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        bg = "#2e2e2e" if self.dark_mode else "SystemButtonFace"
        fg = "white" if self.dark_mode else "black"

        self.configure(bg=bg)
        self.apply_dark_mode_recursive(self)

    def apply_dark_mode_recursive(self, widget):
        bg = "#2e2e2e" if self.dark_mode else "SystemButtonFace"
        fg = "white" if self.dark_mode else "black"

        try:
            if isinstance(widget, tk.Checkbutton):
                widget.configure(
                    bg=bg,
                    fg=fg,
                    activebackground=bg,
                    activeforeground=fg,
                    selectcolor="#000000" if self.dark_mode else "white",
                )
            else:
                widget.configure(bg=bg, fg=fg)
        except:
            try:
                widget.configure(bg=bg)
            except:
                pass

        for child in widget.winfo_children():
            self.apply_dark_mode_recursive(child)

    def delete_selected(self):
        paths_to_delete = [
            path
            for path, var in self.selected_files.items()
            if var.get()
        ]

        if not paths_to_delete:
            messagebox.showinfo(
                "Info",
                "No files selected."
            )
            return

        if not messagebox.askyesno(
            "Confirm",
            f"Move {len(paths_to_delete)} selected images to Recycle Bin?"
        ):
            return

        deleted = 0

        for path in paths_to_delete:

            try:
                move_to_trash(path)

                if path in self.duplicate_files:
                    self.duplicate_files.remove(path)

                if path in self.selected_files:
                    del self.selected_files[path]

                deleted += 1

            except Exception as e:
                print(e)

        # frames_to_destroy = set()
        # for path in paths_to_delete:

        #     frame = self.file_frames.get(path)

        #     if frame:
        #         frames_to_destroy.add(frame)

        # for frame in frames_to_destroy:
        #     try:
        #         frame.destroy()
        #     except:
        #         pass

        messagebox.showinfo(
            "Done",
            f"{deleted} image(s) moved to Recycle Bin."
        )

        self.rescan_folder()

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

    def delete_all_duplicates(self):
        if not self.duplicate_files:
            messagebox.showinfo("Info", "No duplicates to delete.")
            return

        if not messagebox.askyesno(
            "Confirm",
            f"Move ALL {len(self.duplicate_files)} duplicate images to Recycle Bin?"
        ):
            return

        for path in list(self.duplicate_files):
            path = os.path.abspath(path)
            path = os.path.normpath(path)
            if os.path.exists(path):
                try:
                    move_to_trash(path)
                except Exception as e:
                    messagebox.showerror(
                        "Error",
                        f"Couldn't move file to Recycle Bin:\n{e}"
                    )

        # for widget in self.scroll_frame.winfo_children():
        #     widget.destroy()

        # self.duplicate_files.clear()
        # self.selected_files.clear()
        # self.original_vars.clear()
        # self.duplicate_vars.clear()
        # self.file_frames.clear()

        # self.delete_all_btn.pack_forget()
        # self.delete_selected_btn.pack_forget()
        # self.select_originals_btn.pack_forget()
        # self.select_duplicates_btn.pack_forget()
        # self.clear_selection_btn.pack_forget()

        messagebox.showinfo(
            "Done",
            "All duplicates moved to Recycle Bin."
        )

        self.rescan_folder()

    # ---------- THUMBNAILS ----------
    def load_thumbnail(self, path):
        img = Image.open(path)
        img.thumbnail((80, 80))
        photo = ImageTk.PhotoImage(img)
        self.thumbnails.append(photo)
        return photo
    
    # ---------- SKIP WINDOW ----------
    def skip_pair(self, frame, dup_path):
        if dup_path in self.duplicate_files:
            self.duplicate_files.remove(dup_path)

        frame.destroy()

    # ---------- PREVIEW WINDOW ----------
    def open_preview(self, img1_path, img2_path):
        win = tk.Toplevel(self)
        win.title("Image Preview")
        try:
            win.state("zoomed")
        except:
            win.attributes("-fullscreen", True)

        container = tk.Frame(win, bg="black")
        container.pack(fill="both", expand=True)

        canvases = []
        images = []

        for path in (img1_path, img2_path):
            canvas = tk.Canvas(container, bg="black", highlightthickness=0)
            canvas.pack(side="left", fill="both", expand=True)
            canvases.append(canvas)
            images.append(Image.open(path))

        zoom = tk.DoubleVar(value=0.75)
        offset = {"x": 0, "y": 0}

        def redraw():
            for canvas, img in zip(canvases, images):
                canvas.delete("all")
                w, h = img.size
                z = zoom.get()
                resized = img.resize((int(w * z), int(h * z)))
                photo = ImageTk.PhotoImage(resized)
                canvas.image = photo
                canvas.create_image(
                    canvas.winfo_width() // 2 + offset["x"],
                    canvas.winfo_height() // 2 + offset["y"],
                    image=photo
                )

        def drag_start(event):
            canvas.drag_x = event.x
            canvas.drag_y = event.y

        def drag_move(event):
            dx = event.x - canvas.drag_x
            dy = event.y - canvas.drag_y
            offset["x"] += dx
            offset["y"] += dy
            redraw()
            canvas.drag_x = event.x
            canvas.drag_y = event.y

        # ---- Zoom with mouse wheel ----
        def zoom_with_wheel(event):
            factor = 1.1 if event.delta > 0 else 0.9  # Windows/macOS
            new_zoom = zoom.get() * factor
            zoom.set(max(0.2, min(2.0, new_zoom)))
            redraw()

        for canvas in canvases:
            canvas.bind("<ButtonPress-1>", drag_start)
            canvas.bind("<B1-Motion>", drag_move)
            # Mouse wheel zoom
            canvas.bind("<MouseWheel>", zoom_with_wheel)  # Windows/macOS
            canvas.bind("<Button-4>", lambda e: zoom.set(max(0.2, zoom.get()*0.9)) or redraw())  # Linux scroll up
            canvas.bind("<Button-5>", lambda e: zoom.set(min(2.0, zoom.get()*1.1)) or redraw())  # Linux scroll down

        slider = ttk.Scale(
            win, from_=0.2, to=2.0, variable=zoom,
            orient="horizontal", command=lambda e: redraw()
        )
        slider.pack(fill="x", padx=20, pady=10)
        win.bind("<Configure>", lambda e: redraw())
        redraw()


    # ---------- FILE ACTIONS ----------
    # Fixed the issue where if we delete manually then list updates so that delete all duplicates won't throw error
    def delete_file(self, filename, frame):
        path = os.path.abspath(filename)
        path = os.path.normpath(path)

        if messagebox.askyesno("Confirm", f"Delete {filename}?"):
            try:
                move_to_trash(path)
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Couldn't move file to Recycle Bin:\n{e}"
                )

            if path in self.duplicate_files:
                self.duplicate_files.remove(path)

            # remove checkbox tracking
            if path in self.selected_files:
                del self.selected_files[path]

            self.rescan_folder()


if __name__ == "__main__":
    app = DuplicateFinderApp()
    app.mainloop()
