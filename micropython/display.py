# display.py - ST7789 wrapper with PNG load & scale for MicroPython

import time
try:
    from machine import Pin, SPI
    from micropython import const
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    Pin = SPI = const = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ST7789 Commands
_SWRESET = const(0x01) if MICROPYTHON else 0x01
_SLPOUT = const(0x11) if MICROPYTHON else 0x11
_COLMOD = const(0x3A) if MICROPYTHON else 0x3A
_MADCTL = const(0x36) if MICROPYTHON else 0x36
_CASET = const(0x2A) if MICROPYTHON else 0x2A
_RASET = const(0x2B) if MICROPYTHON else 0x2B
_RAMWR = const(0x2C) if MICROPYTHON else 0x2C
_DISPON = const(0x29) if MICROPYTHON else 0x29

class ST7789:
    def __init__(self, spi, width, height, reset=None, cs=None, dc=None, rotation=0):
        self.spi = spi
        self.width = width
        self.height = height
        self.reset = reset
        self.cs = cs
        self.dc = dc
        self.rotation = rotation
        
    def init(self):
        """Initialize the display"""
        if self.reset:
            self.reset.value(0)
            time.sleep_ms(50) if MICROPYTHON else time.sleep(0.05)
            self.reset.value(1)
            time.sleep_ms(50) if MICROPYTHON else time.sleep(0.05)
            
        # Wake up display
        self._write_cmd(_SWRESET)
        time.sleep_ms(150) if MICROPYTHON else time.sleep(0.15)
        
        self._write_cmd(_SLPOUT)
        time.sleep_ms(10) if MICROPYTHON else time.sleep(0.01)
        
        # Set color mode to 16-bit
        self._write_cmd(_COLMOD)
        self._write_data(bytearray([0x05]))
        
        # Set memory access control (rotation)
        self._write_cmd(_MADCTL)
        self._write_data(bytearray([0x00]))
        
        # Display on
        self._write_cmd(_DISPON)
        time.sleep_ms(10) if MICROPYTHON else time.sleep(0.01)
        
    def _write_cmd(self, cmd):
        """Send command to display"""
        if self.cs:
            self.cs.value(0)
        if self.dc:
            self.dc.value(0)  # Command mode
        self.spi.write(bytearray([cmd]))
        if self.cs:
            self.cs.value(1)
            
    def _write_data(self, data):
        """Send data to display"""
        if self.cs:
            self.cs.value(0)
        if self.dc:
            self.dc.value(1)  # Data mode
        self.spi.write(data)
        if self.cs:
            self.cs.value(1)
            
    def _set_window(self, x0, y0, x1, y1):
        """Set the drawing window"""
        self._write_cmd(_CASET)  # Column address set
        self._write_data(bytearray([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        
        self._write_cmd(_RASET)  # Row address set
        self._write_data(bytearray([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        
        self._write_cmd(_RAMWR)  # Write to RAM

    def _fill_rect(self, x, y, w, h, color):
        """Fill a rectangle area with a solid RGB565 color."""
        # Clip to display bounds
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0
        if x + w > self.width:
            w = self.width - x
        if y + h > self.height:
            h = self.height - y
        if w <= 0 or h <= 0:
            return

        self._set_window(x, y, x + w - 1, y + h - 1)
        color_hi = (color >> 8) & 0xFF
        color_lo = color & 0xFF
        # Line buffer for one scanline
        line_buf = bytearray([color_hi, color_lo] * w)

        if self.cs:
            self.cs.value(0)
        if self.dc:
            self.dc.value(1)

        for _ in range(h):
            self.spi.write(line_buf)

        if self.cs:
            self.cs.value(1)
        
    def fill(self, color):
        """Fill entire screen with color (16-bit RGB565)"""
        self._set_window(0, 0, self.width - 1, self.height - 1)
        
        # Convert color to bytes
        color_hi = (color >> 8) & 0xFF
        color_lo = color & 0xFF
        
        # Create buffer for efficient writing
        line_buf = bytearray([color_hi, color_lo] * self.width)
        
        if self.cs:
            self.cs.value(0)
        if self.dc:
            self.dc.value(1)  # Data mode
            
        # Write all pixels
        for _ in range(self.height):
            self.spi.write(line_buf)
            
        if self.cs:
            self.cs.value(1)
            
    def text(self, string, x, y, color, scale=1):
        """Render text. Backwards-compatible: scale=1 retains prior block behavior.

        When scale > 1, render using a tiny 5x7 bitmap font (uppercase) scaled up
        so short messages can occupy most of the screen. Lowercase letters are
        converted to uppercase for the simple font.
        """
        if scale <= 1:
            # Preserve previous behavior
            char_width = 8
            char_height = 8
            for i, char in enumerate(string):
                char_x = x + i * char_width
                if char_x + char_width > self.width:
                    break
                # Draw a small rectangle for each character
                self._set_window(char_x, y, char_x + char_width - 1, y + char_height - 1)
                color_hi = (color >> 8) & 0xFF
                color_lo = color & 0xFF
                char_buf = bytearray([color_hi, color_lo] * char_width)
                if self.cs:
                    self.cs.value(0)
                if self.dc:
                    self.dc.value(1)
                for _ in range(char_height):
                    self.spi.write(char_buf)
                if self.cs:
                    self.cs.value(1)
            return

        # Scaled text using 5x7 font
        FONT_5x7 = {
            ' ': [0x00,0x00,0x00,0x00,0x00],
            '0': [0x3E,0x51,0x49,0x45,0x3E],
            '1': [0x00,0x42,0x7F,0x40,0x00],
            '2': [0x42,0x61,0x51,0x49,0x46],
            '3': [0x21,0x41,0x45,0x4B,0x31],
            '4': [0x18,0x14,0x12,0x7F,0x10],
            '5': [0x27,0x45,0x45,0x45,0x39],
            '6': [0x3C,0x4A,0x49,0x49,0x30],
            '7': [0x01,0x71,0x09,0x05,0x03],
            '8': [0x36,0x49,0x49,0x49,0x36],
            '9': [0x06,0x49,0x49,0x29,0x1E],
            'A': [0x7E,0x11,0x11,0x11,0x7E],
            'B': [0x7F,0x49,0x49,0x49,0x36],
            'C': [0x3E,0x41,0x41,0x41,0x22],
            'D': [0x7F,0x41,0x41,0x22,0x1C],
            'E': [0x7F,0x49,0x49,0x49,0x41],
            'F': [0x7F,0x09,0x09,0x09,0x01],
            'G': [0x3E,0x41,0x49,0x49,0x7A],
            'H': [0x7F,0x08,0x08,0x08,0x7F],
            'I': [0x00,0x41,0x7F,0x41,0x00],
            'J': [0x20,0x40,0x41,0x3F,0x01],
            'K': [0x7F,0x08,0x14,0x22,0x41],
            'L': [0x7F,0x40,0x40,0x40,0x40],
            'M': [0x7F,0x02,0x0C,0x02,0x7F],
            'N': [0x7F,0x04,0x08,0x10,0x7F],
            'O': [0x3E,0x41,0x41,0x41,0x3E],
            'P': [0x7F,0x09,0x09,0x09,0x06],
            'Q': [0x3E,0x41,0x51,0x21,0x5E],
            'R': [0x7F,0x09,0x19,0x29,0x46],
            'S': [0x46,0x49,0x49,0x49,0x31],
            'T': [0x01,0x01,0x7F,0x01,0x01],
            'U': [0x3F,0x40,0x40,0x40,0x3F],
            'V': [0x1F,0x20,0x40,0x20,0x1F],
            'W': [0x3F,0x40,0x38,0x40,0x3F],
            'X': [0x63,0x14,0x08,0x14,0x63],
            'Y': [0x07,0x08,0x70,0x08,0x07],
            'Z': [0x61,0x51,0x49,0x45,0x43],
            '-': [0x08,0x08,0x08,0x08,0x08],
            ':': [0x00,0x36,0x36,0x00,0x00],
            '.': [0x00,0x40,0x60,0x00,0x00],
            '!': [0x00,0x00,0x5F,0x00,0x00],
            '?': [0x02,0x01,0x51,0x09,0x06],
            "'": [0x00,0x07,0x00,0x00,0x00]
        }

        # Render linearly left-to-right. Convert to uppercase for our limited font.
        s = str(string).upper()
        cursor_x = x
        for ch in s:
            glyph = FONT_5x7.get(ch, FONT_5x7[' '])
            # glyph: list of 5 column bytes, LSB at top of column
            for col_idx, col_val in enumerate(glyph):
                for bit in range(7):
                    if (col_val >> bit) & 1:
                        px = cursor_x + col_idx * scale
                        py = y + bit * scale
                        # draw scaled pixel block
                        self._fill_rect(px, py, scale, scale, color)
            # one column spacing after glyph
            cursor_x += (5 * scale) + scale
            # stop if we run out of horizontal space
            if cursor_x >= self.width:
                break


class Display:
    def __init__(self, cfg):
        self.cfg = cfg or {}
        self.width = self.cfg.get('width', 240)
        self.height = self.cfg.get('height', 240)
        self.driver = None
        
        if not MICROPYTHON:
            # Host testing mode - create a mock PIL display for testing
            if PIL_AVAILABLE:
                try:
                    self.image = Image.new('RGB', (self.width, self.height), 'black')
                    self.draw = None
                except Exception:
                    self.image = None
            else:
                self.image = None

    def init(self):
        """Initialize the display hardware or host fallback"""
        if MICROPYTHON:
            # Real hardware initialization
            try:
                # Initialize SPI and pins for ST7789
                spi = SPI(1, baudrate=62500000, polarity=1, phase=1, sck=Pin(10), mosi=Pin(11))
                
                # Waveshare Pico LCD 1.3 pin assignments
                reset_pin = Pin(12, Pin.OUT)
                dc_pin = Pin(8, Pin.OUT) 
                cs_pin = Pin(9, Pin.OUT)
                
                self.driver = ST7789(spi, self.width, self.height, reset=reset_pin, cs=cs_pin, dc=dc_pin)
                self.driver.init()
                print(f"ST7789 driver initialized: {self.width}x{self.height}")
            except Exception as e:
                print(f"Hardware display init failed: {e}")
                self.driver = None
        else:
            # Host mode - PIL display window
            if PIL_AVAILABLE and self.image:
                try:
                    from PIL import ImageDraw
                    self.draw = ImageDraw.Draw(self.image)
                    print(f"PIL display initialized: {self.width}x{self.height}")
                except Exception as e:
                    print(f"PIL display init failed: {e}")

    # Helper: convert (r,g,b) 0-255 tuple to RGB565 16-bit int
    def _rgb_tuple_to_565(self, rgb):
        try:
            r, g, b = rgb
            r5 = (int(r) & 0xF8) >> 3
            g6 = (int(g) & 0xFC) >> 2
            b5 = (int(b) & 0xF8) >> 3
            return (r5 << 11) | (g6 << 5) | b5
        except Exception:
            # If input isn't a tuple, assume it's already an int (RGB565)
            try:
                return int(rgb)
            except Exception:
                return 0

    def _ensure_color(self, color):
        # Accept either (r,g,b) tuples or already-packed 16-bit ints
        if color is None:
            return 0x0000
        if isinstance(color, tuple) and len(color) == 3:
            return self._rgb_tuple_to_565(color)
        return int(color)

    def show_boot_phase(self, text, bg_color=(0, 0, 0), fg_color=(255, 255, 255), scale=2):
        """
        Show a large, centered boot-phase message using fg/bg colors.
        bg_color and fg_color can be (r,g,b) tuples (0-255) or a 16-bit RGB565 int.
        scale selects text scaling (device-dependent).
        """
        bg = self._ensure_color(bg_color)
        fg = self._ensure_color(fg_color)

        # Fill background using the driver if available
        if self.driver:
            try:
                self.driver.fill(bg)
            except Exception as e:
                print(f"Boot phase fill failed: {e}")
        elif not MICROPYTHON and PIL_AVAILABLE and self.image and self.draw:
            # Host testing with PIL
            try:
                # Convert RGB565 back to RGB for PIL
                r = ((bg >> 11) & 0x1F) << 3
                g = ((bg >> 5) & 0x3F) << 2 
                b = (bg & 0x1F) << 3
                from PIL import ImageDraw
                self.draw.rectangle([0, 0, self.width, self.height], fill=(r, g, b))
                print(f"BOOT (PIL): {text}")
            except Exception as e:
                print(f"BOOT (PIL fill failed): {text} - {e}")
        else:
            print(f"BOOT (console): {text}")

        # Simple positioning: left margin and vertical center-ish
        x = 8
        approx_font_height = 7 * scale  # Use 7 since that's the actual font height
        y = max((self.height // 2) - (approx_font_height // 2), 0)

        # Draw the text using the driver if available
        if self.driver:
            try:
                self.driver.text(text, x, y, fg, scale=scale)
            except TypeError:
                # text signature might not accept scale; try fallback without scale
                try:
                    self.driver.text(text, x, y, fg)
                except Exception as e:
                    print(f"Boot phase text failed: {e}")
            except Exception as e:
                print(f"Boot phase text failed: {e}")
        elif not MICROPYTHON and PIL_AVAILABLE and self.draw:
            # Host testing with PIL - just print since PIL text is complex
            print(f"BOOT (PIL text): {text}")
        # Console fallback is already handled above

    def show_placeholder(self):
        """Show placeholder - fill screen with a color for now"""
        # Attempt to show the packaged unknown portrait from /assets first.
        # If the on-device PNG renderer fails (missing deflate or unsupported PNG),
        # fall back to a clear red startup screen so the device doesn't show the
        # older yellow/blue placeholder.
        if self.driver:
            try:
                try:
                    # prefer the shipped asset when present
                    self.draw_scaled_png('/assets/unknown_portrait.png')
                    return
                except Exception as e:
                    # draw_scaled_png will print its own error; continue to fallback
                    print('placeholder: draw_scaled_png failed, falling back:', e)

                # Fallback: red screen with simple texts
                self.driver.fill(0xF800)  # Red
                self.driver.text("PERSON CLICKER", 10, 50, 0xFFFF)  # White text
                self.driver.text("Device Ready!", 10, 70, 0xFFFF)
                self.driver.text("Press buttons", 10, 90, 0xFFFF)
            except Exception as e:
                print('show_placeholder failed', e)
        else:
            print('PLACEHOLDER: Person Clicker - Loading...')

    def show_text(self, text, bg_color=None, fg_color=(255, 255, 255)):
        """Display text on screen"""
        if self.driver:
            try:
                # Clear screen with specified background color
                bg = self._ensure_color(bg_color)
                self.driver.fill(bg)

                fg = self._ensure_color(fg_color)

                # Split into lines and pick a scale so text fills most of the screen.
                # Our scaled font is 5x7 pixels per glyph plus 1 column spacing.
                lines = str(text).split('\n')
                # Determine the longest line length in characters
                max_chars = max((len(l) for l in lines), default=0)
                if max_chars == 0:
                    return

                # Choose scale so that text width fits within 90% of display width
                # width_per_char = (5 + 1) * scale = 6 * scale
                # So scale_max_w = floor((width * 0.9) / (6 * max_chars))
                scale_w = max(1, int((self.width * 0.9) // (6 * max_chars)))
                # Choose scale so that total height fits within 90% of display height
                # height_per_line = 7 * scale
                scale_h = max(1, int((self.height * 0.9) // (7 * len(lines))))
                scale = min(scale_w, scale_h)

                # Center the block of text
                text_block_width = max_chars * (5 * scale + scale)
                text_block_height = len(lines) * (7 * scale)
                start_x = max(0, (self.width - text_block_width) // 2)
                start_y = max(0, (self.height - text_block_height) // 2)

                # Draw each line
                y = start_y
                for line in lines:
                    # center each line horizontally within the block
                    line_len = len(line)
                    line_width = line_len * (5 * scale + scale)
                    x = start_x + max(0, (text_block_width - line_width) // 2)
                    # Use driver.text with scale to render
                    self.driver.text(line, x, y, fg, scale=scale)
                    y += 7 * scale
            except Exception as e:
                print('show_text failed', e)
        else:
            print('TEXT:', text)

    def draw_scaled_png(self, path):
        """Draw a PNG image scaled to display size"""
        if self.driver:
            # Minimal PNG decoder for non-interlaced truecolor 8-bit images (color type 2 or 6)
            try:
                import deflate
                import struct

                with open(path, 'rb') as f:
                    data = f.read()

                # simple PNG signature check
                if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                    print('Not a PNG:', path)
                    return

                # Parse chunks to find IHDR and concatenated IDAT (avoid struct.unpack)
                offset = 8
                width = height = None
                bitdepth = None
                colortype = None
                idat_data = b''
                while offset < len(data):
                    if offset + 8 > len(data):
                        break
                    # Parse length manually (big-endian)
                    length = (data[offset] << 24) | (data[offset+1] << 16) | (data[offset+2] << 8) | data[offset+3]
                    ctype = data[offset+4:offset+8]
                    cdata = data[offset+8:offset+8+length]
                    # skip CRC
                    offset = offset + 8 + length + 4
                    if ctype == b'IHDR' and len(cdata) >= 13:
                        # Parse IHDR manually
                        width = (cdata[0] << 24) | (cdata[1] << 16) | (cdata[2] << 8) | cdata[3]
                        height = (cdata[4] << 24) | (cdata[5] << 16) | (cdata[6] << 8) | cdata[7]
                        bitdepth = cdata[8]
                        colortype = cdata[9]
                    elif ctype == b'IDAT':
                        idat_data += cdata
                    elif ctype == b'IEND':
                        break

                if not idat_data or width is None:
                    print('PNG missing IDAT or IHDR')
                    return

                # Memory-efficient decompression: read in chunks to reduce peak memory
                try:
                    import io
                    
                    # Create a stream from the IDAT data
                    idat_stream = io.BytesIO(idat_data)
                    
                    # Use DeflateIO with ZLIB format to handle the headers automatically
                    deflate_stream = deflate.DeflateIO(idat_stream, deflate.ZLIB)
                    
                    # Read decompressed data in chunks to reduce memory pressure
                    decomp_chunks = []
                    while True:
                        chunk = deflate_stream.read(4096)  # Read 4KB at a time
                        if not chunk:
                            break
                        decomp_chunks.append(chunk)
                    
                    deflate_stream.close()
                    
                    # Force garbage collection before joining chunks
                    import gc
                    gc.collect()
                    
                    # Join chunks into final decompressed data
                    decomp = b''.join(decomp_chunks)
                    del decomp_chunks  # Free chunk list immediately
                    gc.collect()
                    
                    print(f'PNG decompressed: {len(decomp)} bytes')
                    
                except Exception as e:
                    print('PNG decompress failed:', e)
                    return

                # Determine bytes per pixel and extract palette if needed
                palette = None
                if colortype == 2:
                    bpp = 3  # RGB
                elif colortype == 3:
                    bpp = 1  # Palette-indexed
                    print('Palette-indexed PNG detected, extracting palette...')
                    # Extract palette from PLTE chunk
                    offset = 8
                    while offset < len(data) - 8:
                        length = (data[offset] << 24) | (data[offset+1] << 16) | (data[offset+2] << 8) | data[offset+3]
                        chunk_type = data[offset+4:offset+8]
                        if chunk_type == b'PLTE':
                            palette_data = data[offset+8:offset+8+length]
                            palette = []
                            for i in range(0, len(palette_data), 3):
                                if i + 2 < len(palette_data):
                                    r, g, b = palette_data[i], palette_data[i+1], palette_data[i+2]
                                    palette.append((r, g, b))
                            print(f'Extracted palette with {len(palette)} colors')
                            break
                        offset += 8 + length + 4
                        if chunk_type == b'IEND':
                            break
                    if not palette:
                        print('Palette-indexed PNG missing PLTE chunk')
                        return
                elif colortype == 6:
                    bpp = 4  # RGBA
                else:
                    print('Unsupported PNG color type', colortype)
                    return

                # Memory-efficient streaming: process one display line at a time
                row_bytes = width * bpp + 1  # +1 for filter byte
                out_w = self.width
                out_h = self.height
                
                print(f'Streaming PNG: {width}x{height} -> {out_w}x{out_h}, bpp={bpp}')
                
                # Process each output display line
                for out_y in range(out_h):
                    # Map output line to source line
                    src_y = int(out_y * height / out_h)
                    if src_y >= height:
                        src_y = height - 1
                    
                    # Find source row in decompressed data
                    row_start = src_y * row_bytes
                    if row_start >= len(decomp):
                        break
                        
                    filter_type = decomp[row_start]
                    # For simplicity, only support filter type 0 (None)
                    if filter_type != 0:
                        print(f'Unsupported PNG filter type {filter_type} at line {src_y}')
                        continue
                    
                    # Extract pixel data for this source row (skip filter byte)
                    row_data_start = row_start + 1
                    row_data_end = row_data_start + width * bpp
                    
                    # Build RGB565 line for display
                    line_buf = bytearray(out_w * 2)  # 2 bytes per RGB565 pixel
                    buf_idx = 0
                    
                    for out_x in range(out_w):
                        # Map output x to source x
                        src_x = int(out_x * width / out_w)
                        if src_x >= width:
                            src_x = width - 1
                            
                        # Get source pixel
                        pixel_base = row_data_start + src_x * bpp
                        if pixel_base + bpp <= row_data_end:
                            if colortype == 3:  # Palette-indexed
                                palette_index = decomp[pixel_base]
                                if palette_index < len(palette):
                                    r, g, b = palette[palette_index]
                                else:
                                    r = g = b = 0  # Invalid palette index
                            elif bpp == 3:  # RGB
                                r = decomp[pixel_base]
                                g = decomp[pixel_base + 1]
                                b = decomp[pixel_base + 2]
                            else:  # RGBA
                                r = decomp[pixel_base]
                                g = decomp[pixel_base + 1]
                                b = decomp[pixel_base + 2]
                        else:
                            # Fallback for edge cases
                            r = g = b = 0
                        
                        # Convert RGB888 to RGB565
                        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                        line_buf[buf_idx] = (rgb565 >> 8) & 0xFF      # High byte
                        line_buf[buf_idx + 1] = rgb565 & 0xFF         # Low byte
                        buf_idx += 2
                    
                    # Write line directly to display in smaller chunks to avoid buffer issues
                    self.driver._set_window(0, out_y, out_w-1, out_y)
                    if self.driver.cs:
                        self.driver.cs.value(0)
                    if self.driver.dc:
                        self.driver.dc.value(1)
                    
                    # Write in 64-pixel chunks (128 bytes) to avoid buffer overflow
                    chunk_size = 128  # 64 pixels * 2 bytes per pixel
                    for chunk_start in range(0, len(line_buf), chunk_size):
                        chunk_end = min(chunk_start + chunk_size, len(line_buf))
                        chunk = line_buf[chunk_start:chunk_end]
                        self.driver.spi.write(chunk)
                    
                    if self.driver.cs:
                        self.driver.cs.value(1)
                        
                    # Garbage collect periodically to manage memory
                    if out_y % 50 == 0:
                        import gc
                        gc.collect()
                
                print('Streaming PNG display completed')
                return
            except Exception as e:
                print('On-device PNG display failed:', e)
                return
        elif PIL_AVAILABLE:
            # Host fallback using PIL
            try:
                img = Image.open(path)
                img = img.convert('RGB')
                img = img.resize((self.width, self.height))
                print('Would draw image to display (host):', path)
            except Exception as e:
                print('PIL image processing failed:', e)
        else:
            print('PNG display not available in this environment:', path)

    def draw_rgb565_raw(self, path):
        """Display raw RGB565 binary file directly to screen.
        
        Expects exactly width*height*2 bytes of RGB565 data.
        This is the most efficient format - no decompression needed.
        """
        try:
            # Check file size
            import uos
            stat = uos.stat(path)
            expected_size = self.width * self.height * 2
            file_size = stat[6]  # st_size
            
            print(f"RGB565 file: {file_size} bytes, expected: {expected_size} bytes")
            
            if file_size != expected_size:
                print(f"Warning: File size mismatch. Expected {expected_size}, got {file_size}")
                # Continue anyway in case of metadata differences
            
            # Set display window to full screen
            self.driver._set_window(0, 0, self.width - 1, self.height - 1)
            
            # Read and write in chunks to avoid large memory allocation
            chunk_size = 4096  # 4KB chunks
            print(f"Reading RGB565 data in {chunk_size} byte chunks...")
            
            with open(path, 'rb') as f:
                total_written = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Write chunk directly to SPI
                    self.driver.dc.value(1)  # Data mode
                    self.driver.cs.value(0)  # Select display
                    self.driver.spi.write(chunk)
                    self.driver.cs.value(1)  # Deselect
                    
                    total_written += len(chunk)
                    if total_written % (chunk_size * 4) == 0:  # Progress every 16KB
                        print(f"Written: {total_written} bytes ({total_written*100//expected_size}%)")
                
                print(f"RGB565 display complete: {total_written} bytes written")
                return True
                
        except Exception as e:
            print('RGB565 display failed:', e)
            try:
                import sys
                sys.print_exception(e)
            except:
                pass
            return False
