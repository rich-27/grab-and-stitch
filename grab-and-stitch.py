import sys
import os
from PIL import Image
from PIL import UnidentifiedImageError
import requests
from io import BytesIO
import tkinter
from tkinter import messagebox
import time
import random

def main():
    IMAGE_NAME = 'image.png'
    URL = 'https://example.com'
    PARAMS_SPEC = {
        'artworkid': 0,
        'x': range(3500, 9900, 100),
        'y': range(900, 3700, 100),
        'widthmedium': 13201,
        'heightmedium': 8800
    }
    AUTO_RETRY_FLAG = True

    (x_count, y_count) = (len(PARAMS_SPEC['x']), len(PARAMS_SPEC['y']))
    
    params = {k: (v[0] if v is range else v) for k, v in PARAMS_SPEC.items()}

    (patch_width, patch_height) = request_image(URL, params).size
    gap = 11

    filepath = os.path.join(os.path.split(__file__)[0], IMAGE_NAME)
    (image, valid_patch_mask) = get_image(filepath, x_count, y_count, patch_width, patch_height, gap)

    try:
        for y in range(y_count):
            params['y'] = PARAMS_SPEC['y'][y]
            for x in range(x_count):
                params['x'] = PARAMS_SPEC['x'][x]
                if valid_patch_mask[y][x]:
                    continue
                offset = (x * (patch_width + gap), y * (patch_height + gap))
                while True:
                    try:
                        image.paste(request_image(URL, params), offset)
                    except RuntimeError as e:
                        print(e)
                        save_image(image, filepath)
                        if AUTO_RETRY_FLAG:
                            delay_awhile()
                        elif TKChief.retry_dialog('Image Stitcher: Download Failure',
                            f'Image {(x, y)} of {(x_count, y_count)} failed. ' +
                            'Do you want to retry?'):
                                raise CancelFromLoopException from e
                    else:
                        print(f'Retrieved image {(x, y)} of {(x_count, y_count)}')
                        break
                    print(f'Image {(x, y)} of {(x_count, y_count)} failed, retrying...')
    except CancelFromLoopException:
        pass

    save_image(image, filepath)
    os.startfile(filepath)

def request_image(URL, params):
    r = requests.get(URL, params = params)
    try:
        patch = Image.open(BytesIO(r.content))
    except UnidentifiedImageError as e:
        raise RuntimeError(f'Request did not return valid image: {r.text}') from None
    return patch

def save_image(image, filepath):
    image.save(filepath)
    print(f'Saved to {filepath}')

def delay_awhile():
    delay_time = random.randint(8 * 60, 15 * 60)
    print(f'Slacking off for ~{delay_time // 60} minutes...')
    while delay_time >= 5 * 60:
        time.sleep(5 * 60)
        delay_time -= 5 * 60
        print(f'{delay_time // 60}ish minutes left')
    time.sleep(delay_time)
    return

class TKChief:
    tkroot = tkinter.Tk()
    tkroot.overrideredirect(1)
    tkroot.withdraw()

    @staticmethod
    def retry_dialog(title, message):
        return messagebox.askretrycancel(title, message, parent=TKChief.tkroot)

class CancelFromLoopException(RuntimeError):
    pass

def get_image(filepath, x_count, y_count, patch_width, patch_height, gap):
    dimensions = (x_count * (patch_width + gap), y_count * (patch_height + gap))
    valid_patch_mask = [[False for x in range(x_count)]for y in range(y_count)]
    image = try_restore_image(filepath, dimensions, x_count, y_count, patch_width, patch_height, gap, valid_patch_mask)
    
    if image is not None:
        return (image, valid_patch_mask)
    else:
        return (Image.new('RGBA', dimensions), valid_patch_mask)

def try_restore_image(filepath, dimensions, x_count, y_count, patch_width, patch_height, gap, valid_patch_mask):
    try:
        image = Image.open(filepath)
    except FileNotFoundError:
        return None
    
    if image.size != dimensions:
        return None
    
    valid_patch_count = 0
    # If image is empty, no point scanning it
    if image.getbbox() != None:
        for y in range(y_count):
            for x in range(x_count):
                coords = (x * (patch_width + gap), y * (patch_height + gap))
                get_box(coords, (patch_width, patch_height))
                patch = image.crop(get_box(coords, (patch_width + gap, patch_height + gap)))

                bbox = patch.getbbox()
                # Patch is empty, found stopping point
                if bbox == None:
                    continue
                # Patch size incorrect
                elif bbox != (0, 0, patch_width, patch_height):
                    return None
                else:
                    valid_patch_count += 1
                    valid_patch_mask[y][x] = True
            else:
                continue
            break

    print(f'Successfully restored {os.path.split(filepath)[1]} with {valid_patch_count}/{x_count * y_count} completed image sections')
    return image

def get_box(coords, size):
    return (coords[0], coords[1], coords[0] + size[0], coords[1] + size[0])

if __name__ == '__main__':
    main()