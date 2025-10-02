import os
from PIL import Image
import hashlib

def get_image_hash(image_path):
    with Image.open(image_path) as img:
        img = img.convert('L').resize((8, 8))  # Grayscale & Resize
        pixels = list(img.getdata())
        avg_pixel = sum(pixels) / len(pixels)
        diff = ''.join('1' if pixel > avg_pixel else '0' for pixel in pixels)
        return hashlib.md5(diff.encode('utf-8')).hexdigest()

# Your image folder path
image_folder = r'C:\Users\imagine\Documents\Bulk Image Downloader\Vinnegal\Raiden Shogun Kimono + Tattoos'
image_files = [f for f in os.listdir(image_folder) if f.lower().endswith('.jpg')]

# Dictionary to map hash -> first image
image_hashes = {}
duplicate_pairs = []

for file_org in image_files:
    file_path = os.path.join(image_folder, file_org)
    img_hash = get_image_hash(file_path)

    if img_hash in image_hashes:
        # Found a duplicate
        original_file = image_hashes[img_hash]
        duplicate_pairs.append((original_file, file_org))
    else:
        image_hashes[img_hash] = file_org

# Print results: two per row
for original, duplicate in duplicate_pairs:
    print(original, duplicate)
