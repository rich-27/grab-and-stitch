import sys
import os
from PIL import Image
from PIL import ImageChops
from PIL import ImageFilter

def main():
    IMAGE_NAME = 'image.png'
    WATERMARK_NAME = 'watermark.png'

    image = open_image(IMAGE_NAME)
    watermark = open_image(WATERMARK_NAME)

    palette = get_palette(watermark)
    bg_col = palette[max(palette.keys())][0] # Get most used colour

    alpha_channel = image.getchannel('A')

    # Strip background colour
    image = Image.merge('RGB', (
        tuple(image.getchannel('RGB'[bno]).point(lambda p: round((p - bg_col[bno]) * (255 / (255 - bg_col[bno])))) for bno in range(len('RGB')))
    )).convert('L')
    
    watermark = Image.merge('RGB', (
        tuple(watermark.getchannel('RGB'[bno]).point(lambda p: round((p - bg_col[bno]) * (255 / (255 - bg_col[bno])))) for bno in range(len('RGB')))
    )).convert('L')
    
    result = Image.new('RGB', image.size)
    for y in range(0, image.size[1], watermark.size[1]):
        for x in range(0, image.size[0], watermark.size[0]):
            box = (x, y, x + watermark.size[0], y + watermark.size[1])

            initial_cut = ImageChops.subtract(image.crop(box), watermark)

            filler_masked = ImageChops.multiply(initial_cut, watermark)
            
            bands = filler_masked.getbands()
            extrema = filler_masked.getextrema()
            
            point_func = lambda m : (lambda p : round((p * 255) / m if m > 0 else p))
            
            scaled_filler = (filler_masked.point(point_func(extrema[1])) if len(bands) == 1 else
                Image.merge(''.join(image.getbands()), [filler_masked.getchannel(bands[band_no]).point(point_func(extrema[band_no][1])) for band_no in range(len(bands))]))

            result.paste(ImageChops.add(initial_cut, scaled_filler), box)

    # Add background colour again
    result = Image.merge('RGB', (
        tuple(result.getchannel('RGB'[bno]).point(lambda p: round((p * (255 - bg_col[bno]) / 255) + bg_col[bno])) for bno in range(len('RGB')))
    ))
    result.putalpha(alpha_channel)

    save_image(result, ' stripped.'.join(IMAGE_NAME.split('.')))
    result.show()

def cola(c, a):
    return (c[0], c[1], c[2], a)

def open_image(name):
    filepath = os.path.join(os.path.split(__file__)[0], name)
    try:
        return Image.open(filepath)
    except FileNotFoundError:
        return None
    
def save_image(image, name):
    filepath = os.path.join(os.path.split(__file__)[0], name)
    image.save(filepath)
    print(f'Saved to {filepath}')

def get_palette(image):
    colour_counts = {}
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            pixel = image.getpixel((x, y))
            try:
                colour_counts[pixel] += 1
            except KeyError:
                colour_counts[pixel] = 1
    
    histogram = {}
    for k, v in colour_counts.items():
        try:
            histogram[v].append(k)
        except KeyError:
            histogram[v] = [k]
    
    for v in histogram.values():
        v.sort(key = lambda v : v[2], reverse = True)
        v.sort(key = lambda v : v[1], reverse = True)
        v.sort(key = lambda v : v[0], reverse = True)
        v.sort(key = lambda v : v[3], reverse = True)
    
    return histogram
    
def format_histogram(histogram):
    key_width = len(str(max(histogram.keys())))
    return '\n'.join([
        (f'{k}:').ljust(key_width + 2) +
        ',\n'.ljust(key_width + 4).join([
            ', '.join(map(lambda c : ('(%d, %d, %d, %d)' % c).rjust(20), row)) for row in [histogram[k][i : i + 8] for i in range(0, len(histogram[k]), 8)]
        ]) for k in sorted(histogram.keys(), reverse = True)
    ])

if __name__ == '__main__':
    main()