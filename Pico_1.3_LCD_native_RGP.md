## Pico 1.3" ST7789VW — Image format and upload guide

This document records the *exact* image format and processing steps we discovered during development so images generated upstream can be displayed reliably on the Pico W + 1.3" ST7789 LCD.

### Summary (requirements)

- Native resolution: 240 × 240 pixels
- Display color format: 16-bit RGB565 (two bytes per pixel)
- Transfer format that proved reliable: 240×240 raw RGB565 binary, packed as big-endian (high byte first)
- Pixel packing: standard RGB565 mapping (R:5 bits, G:6 bits, B:5 bits)
- Chunked transfer: send the raw binary to the Pico in small chunks (4KB used successfully) to avoid memory spikes

Notes:
- PNG (RGB) or JPEG decoding on the Pico caused memory fragmentation and allocation failures. Avoid sending compressed RGB images directly to the device.
- Palette-indexed PNGs also work (1 byte/pixel) and are memory-efficient, but the most straightforward, reliable approach is raw RGB565.

---

### Server-side: convert source image to 240×240 RGB565 raw binary

Use Python + Pillow to resize and convert to RGB565. The exact conversion we used (which matched the display) is below.

```python
from PIL import Image
import struct

def png_to_rgb565_raw(input_path, output_path, size=(240, 240)):
	img = Image.open(input_path).convert('RGB')
	img = img.resize(size, Image.LANCZOS)

	with open(output_path, 'wb') as out:
		for y in range(size[1]):
			for x in range(size[0]):
				r, g, b = img.getpixel((x, y))
				# If you see brightness inversion; uncomment the next three lines
				# r = 255 - r
				# g = 255 - g
				# b = 255 - b
				# Convert to RGB565 (R:5,G:6,B:5)
				rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
				# Write big-endian: high byte then low byte
				out.write(struct.pack('>H', rgb565))

	print('Wrote', output_path)

```

Notes on channel order / brightness:
- If colors appear swapped (e.g., blues look brown) try swapping R/B when building the 16-bit value.
- If brightness appears inverted (image looks like a negative), invert the channels (255 - value) before packing.

### Transfer to Pico

1. Copy the raw file to the Pico's filesystem (example using mpremote):

```bash
mpremote cp /path/to/output_240x240.rgb565 :/assets/image.rgb565
```

2. On the Pico, use the provided `draw_rgb565_raw(path)` function in `micropython/display.py` to stream the raw file to the ST7789.

The device-level implementation used these practical rules:
- Read the file in small chunks (4 KB worked reliably) to avoid large memory allocations.
- Use the display driver's `spi.write()` while toggling `dc`/`cs` pins appropriately.
- Set the display window to the full screen before streaming.

Example Pico-side invocation (MicroPython):

```python
import display
disp = display.Display({})
disp.init()
disp.draw_rgb565_raw('/assets/image.rgb565')
```

### Why not PNG/JPEG on-device?

- PNG RGB/JPEG produce large decompressed buffers (3 bytes/pixel), and MicroPython's heap fragmentation/allocator caused allocation failures even for 240×240 images.
- The Pico's `deflate` API required small temporary allocations that still failed under fragmentation.
- Converting on the server avoids all of these problems and is fast for this use-case.

### Final notes

- The above approach was validated end-to-end: we converted a 512×512 portrait to 240×240 RGB565 raw, streamed it to the Pico in 4 KB chunks and the ST7789 displayed it with correct colors and brightness after minor channel-order/byte-order adjustments.
- If you need smaller file sizes, consider palette-quantization (256 colors) on the server and sending palette-indexed PNGs — those were displayable by the Pico's PNG path and much smaller in memory, but require more server-side logic to generate correctly.

