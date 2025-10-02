import os
import hashlib
from tkinter import Tk, filedialog, messagebox
from PIL import Image

def get_image_hash(image_path):
    with Image.open(image_path) as img:
        img = img.convert('L').resize((8, 8))
        pixels = list(img.getdata())
        avg_pixel = sum(pixels) / len(pixels)
        diff = ''.join('1' if pixel > avg_pixel else '0' for pixel in pixels)
        return hashlib.md5(diff.encode('utf-8')).hexdigest()

def find_duplicates(image_folder):
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.jpg','.png','.jpeg'))]
    image_hashes = {}
    duplicate_pairs = []

    for file_org in image_files:
        file_path = os.path.join(image_folder, file_org)
        try:
            img_hash = get_image_hash(file_path)
        except:
            continue

        if img_hash in image_hashes:
            duplicate_pairs.append((image_hashes[img_hash], file_org))
        else:
            image_hashes[img_hash] = file_org

    return duplicate_pairs

if __name__ == "__main__":
    root = Tk()
    root.withdraw()  # Hide main window
    folder = filedialog.askdirectory(title="Select Image Folder")

    if folder:
        duplicates = find_duplicates(folder)
        if duplicates:
            result = "\n".join([f"{o} <--> {d}" for o,d in duplicates])
            messagebox.showinfo("Duplicates Found", result)
        else:
            messagebox.showinfo("Result", "No duplicates found.")
