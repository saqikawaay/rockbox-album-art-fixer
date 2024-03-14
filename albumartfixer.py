import tkinter
from tkinter import filedialog
import os
from PIL import Image
import struct
import mutagen
from mutagen.id3 import ID3, APIC, error
from mutagen.flac import Picture, FLAC
import io



def is_image_progressive(file_obj):
    # Note: Adjusted to work with file objects instead of filenames
    while True:
        block_start = struct.unpack('B', file_obj.read(1))[0]
        if block_start != 0xff:
            raise ValueError('Invalid char code - not a JPEG file')
            return False

        block_type = struct.unpack('B', file_obj.read(1))[0]
        if block_type == 0xd8:   # Start Of Image
            continue
        elif block_type == 0xc0: # Start of baseline frame
            return False
        elif block_type == 0xc2: # Start of progressive frame
            return True
        elif 0xd0 <= block_type <= 0xd7: # Restart
            continue
        elif block_type == 0xd9: # End Of Image
            break
        else: # Variable-size block, just skip it
            block_size = struct.unpack('2B', file_obj.read(2))
            block_size = block_size[0] * 256 + block_size[1] - 2
            file_obj.seek(block_size, 1)
    return False





def process_mp3_file(file_path):
    audio = MP3(file_path, ID3=ID3)

    try:
        album_art = None
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                album_art = tag.data
                break

        if not album_art:
            print(f"No album art found in {file_path}.")
            return

        image_data = io.BytesIO(album_art)
        # Check if the image is progressive
        if is_image_progressive(image_data):
            image_data.seek(0)  # Reset pointer after check
            image = Image.open(image_data)
            image = image.resize((500, 500), Image.ANTIALIAS)
            byte_arr = io.BytesIO()
            image.save(byte_arr, format='JPEG', quality=85, progressive=False)
            processed_art = byte_arr.getvalue()

            # Re-embed the processed album art
            audio.tags.delall('APIC')
            audio.tags.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=processed_art
            ))

            audio.save()
            print(f"Processed album art for {file_path}.")
        
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")


def process_flac_file(file_path):
    audio = FLAC(file_path)

    try:
        # FLAC files can have multiple pictures. We'll process the first one found.
        if not audio.pictures:
            print(f"No album art found in {file_path}.")
            return

        album_art = audio.pictures[0].data

        image_data = io.BytesIO(album_art)
        # Check if the image is progressive
        if is_image_progressive(image_data):
            image_data.seek(0)  # Reset pointer after check
            image = Image.open(image_data)
            image = image.resize((500, 500), Image.ANTIALIAS)
            byte_arr = io.BytesIO()
            image.save(byte_arr, format='JPEG', quality=85, progressive=False)
            processed_art = byte_arr.getvalue()

            # Prepare the new Picture
            pic = Picture()
            pic.mime = u"image/jpeg"
            pic.type = 3
            pic.desc = u"Cover (front)"
            pic.width = 500
            pic.height = 500
            pic.depth = 24  # Assuming 24-bit depth; adjust as necessary
            pic.data = processed_art

            # Remove existing pictures and add the new one
            audio.clear_pictures()
            audio.add_picture(pic)

            audio.save()
            print(f"Processed album art for {file_path}.")

    except Exception as e:
        print(f"Failed to process {file_path}: {e}")


def process_directory(directory):
    # Walk through the directory, find MP3 and FLAC files, and process them
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".mp3"):
                process_mp3_file(os.path.join(root, file))
            elif file.endswith(".flac"):
                process_flac_file(os.path.join(root, file))

def choose_directory():
    directory = filedialog.askdirectory()
    if directory:
        process_directory(directory)

def setup_gui():
    root = tk.Tk()
    root.title("Music File Album Art Processor")
    tk.Button(root, text="Choose Directory", command=choose_directory).pack()
    tk.Button(root, text="Exit", command=root.quit).pack()
    root.mainloop()

if __name__ == "__main__":
    setup_gui()
