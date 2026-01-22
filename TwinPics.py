import os
import hashlib
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------- IMAGE HASH ----------
def get_image_hash(image_path):
    with Image.open(image_path) as img:
        img = img.convert("L").resize((8, 8))
        pixels = list(img.getdata())
        avg_pixel = sum(pixels) / len(pixels)
        diff = "".join("1" if p > avg_pixel else "0" for p in pixels)
        return hashlib.md5(diff.encode()).hexdigest()

# ---------- IMAGE QUALITY ----------
def image_quality_key(path):
    with Image.open(path) as img:
        w, h = img.size
    return (w * h, os.path.getsize(path))

# ---------- FIND DUPLICATES ----------
def find_duplicates_grouped(image_folder, progress_callback):
    image_files = [
        f for f in os.listdir(image_folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    hashes = {}
    total = len(image_files)

    for i, file in enumerate(image_files, start=1):
        progress_callback(i, total)
        path = os.path.join(image_folder, file)
        try:
            h = get_image_hash(path)
        except:
            continue
        hashes.setdefault(h, []).append(file)

    return {h: files for h, files in hashes.items() if len(files) > 1}

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

        self.title("Image Duplicate Finder")
        self.geometry("950x650")
        self.folder = ""
        self.thumbnails = []
        self.duplicate_frames = []  # store frames for delete all duplicates
        self.dark_mode = False
        self.duplicate_files = []

        # ---- TOP BAR ----
        top = tk.Frame(self)
        top.pack(fill="x", pady=10)

        tk.Button(top, text="Select Folder", command=self.select_folder).pack(side="left", padx=5)

        self.progress = ttk.Progressbar(top)
        self.progress.pack(side="left", fill="x", expand=True, padx=10)
        self.duplicate_files.clear()

        # Delete All Duplicates button (initially hidden)
        self.delete_all_btn = tk.Button(top, text="Delete All Duplicates", command=self.delete_all_duplicates)
        self.delete_all_btn.pack(side="left", padx=5)
        self.delete_all_btn.pack_forget()  # hide initially

        # Dark mode toggle
        self.dark_mode_btn = tk.Button(top, text="Dark Mode", command=self.toggle_dark_mode)
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
        self.progress["value"] = 0
        self.update()

        groups = find_duplicates_grouped(self.folder, self.update_progress)
        if not groups:
            messagebox.showinfo("Result", "No duplicates found.")
            self.delete_all_btn.pack_forget()  # hide button
            return

        # Show delete all duplicates button
        self.delete_all_btn.pack(side="left", padx=5)

        self.display_groups(groups)

    def update_progress(self, current, total):
        self.progress["maximum"] = total
        self.progress["value"] = current
        self.update_idletasks()

    # ---------- DISPLAY GROUPS ----------
    def display_groups(self, groups):
        for files in groups.values():
            paths = [os.path.join(self.folder, f) for f in files]
            best_path = max(paths, key=image_quality_key)
            best_file = os.path.basename(best_path)

            group = tk.LabelFrame(self.scroll_frame, text=f"Best One: {best_file}", padx=5, pady=5)
            group.pack(fill="x", padx=10, pady=10)

            for f in files:
                if f != best_file:
                    dup_path = os.path.join(self.folder, f)
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
        frame.columnconfigure(2, weight=1)

        # ---- Paths ----
        orig_path = os.path.join(self.folder, orig)
        dup_path = os.path.join(self.folder, dup)

        img1 = self.load_thumbnail(orig_path)
        img2 = self.load_thumbnail(dup_path)

        # ---- Original column ----
        orig_col = tk.Frame(frame)
        orig_col.grid(row=0, column=0, sticky="nsew", padx=5)
        tk.Label(orig_col, image=img1).pack(side="left", padx=5, pady=5)
        meta1 = tk.Frame(orig_col)
        meta1.pack(side="left", fill="y")
        tk.Label(meta1, text=orig, font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w")
        tk.Label(meta1, text=get_image_info(orig_path), anchor="w").pack(anchor="w")
        tk.Button(meta1, text="Delete", command=lambda: self.delete_file(orig, frame)).pack(anchor="w", pady=2)

        # ---- Duplicate column ----
        dup_col = tk.Frame(frame)
        dup_col.grid(row=0, column=1, sticky="nsew", padx=5)
        tk.Label(dup_col, image=img2).pack(side="left", padx=5, pady=5)
        meta2 = tk.Frame(dup_col)
        meta2.pack(side="left", fill="y")
        tk.Label(meta2, text=dup, font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w")
        tk.Label(meta2, text=get_image_info(dup_path), anchor="w").pack(anchor="w")
        tk.Button(meta2, text="Delete", command=lambda: self.delete_file(dup, frame)).pack(anchor="w", pady=2)

        # ---- Preview column ----
        preview_col = tk.Frame(frame)
        preview_col.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        tk.Button(preview_col, text="Preview", command=lambda: self.open_preview(orig_path, dup_path)).pack(expand=True)

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
            widget.configure(bg=bg, fg=fg)
        except:
            try:
                widget.configure(bg=bg)
            except:
                pass
        for child in widget.winfo_children():
            self.apply_dark_mode_recursive(child)

    def delete_all_duplicates(self):
        if not self.duplicate_files:
            messagebox.showinfo("Info", "No duplicates to delete.")
            return

        if not messagebox.askyesno(
            "Confirm",
            f"Delete ALL {len(self.duplicate_files)} duplicate images?"
        ):
            return

        for path in self.duplicate_files:
            if os.path.exists(path):
                os.remove(path)

        messagebox.showinfo("Done", "All duplicates deleted.")
        self.select_folder()  # refresh UI


    # ---------- THUMBNAILS ----------
    def load_thumbnail(self, path):
        img = Image.open(path)
        img.thumbnail((80, 80))
        photo = ImageTk.PhotoImage(img)
        self.thumbnails.append(photo)
        return photo

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
    def delete_file(self, filename, frame):
        path = os.path.join(self.folder, filename)
        if messagebox.askyesno("Confirm", f"Delete {filename}?"):
            os.remove(path)
            frame.destroy()


if __name__ == "__main__":
    app = DuplicateFinderApp()
    app.mainloop()
