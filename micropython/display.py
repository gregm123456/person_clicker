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
            
    def text(self, string, x, y, color):
        """Basic text rendering (draws small rectangles for characters)"""
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


class Display:
    def __init__(self, cfg):
        self.cfg = cfg or {}
        self.width = self.cfg.get('width', 240)
        self.height = self.cfg.get('height', 240)
        self.driver = None

    def init(self):
        """Initialize ST7789 display with Waveshare Pico LCD 1.3 pins"""
        if not MICROPYTHON:
            print('ST7789 driver not available in host env; display calls will be no-ops')
            return
        
        # Waveshare Pico LCD 1.3 default pins
        LCD_SCLK = self.cfg.get('sclk_pin', 10)   # GP10
        LCD_MOSI = self.cfg.get('mosi_pin', 11)   # GP11
        LCD_CS   = self.cfg.get('cs_pin', 9)      # GP9
        LCD_DC   = self.cfg.get('dc_pin', 8)      # GP8
        LCD_RESET= self.cfg.get('reset_pin', 12)  # GP12
        LCD_BL   = self.cfg.get('bl_pin', 13)     # GP13
        
        try:
            # Use SPI1 with explicit pin assignments
            spi = SPI(1, baudrate=40000000, sck=Pin(LCD_SCLK), mosi=Pin(LCD_MOSI))
            dc = Pin(LCD_DC, Pin.OUT)
            cs = Pin(LCD_CS, Pin.OUT)
            rst = Pin(LCD_RESET, Pin.OUT)
            bl = Pin(LCD_BL, Pin.OUT)

            # Turn on backlight
            bl.value(1)

            self.driver = ST7789(spi, self.width, self.height, reset=rst, cs=cs, dc=dc, rotation=0)
            self.driver.init()
            print('ST7789 display initialized')
        except Exception as e:
            print('ST7789 init failed:', e)
            self.driver = None

    def show_placeholder(self):
        """Show placeholder - fill screen with a color for now"""
        # Attempt to show the packaged unknown portrait from /assets first.
        # If the on-device PNG renderer fails (missing uzlib or unsupported PNG),
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

    def show_text(self, text):
        """Display text on screen"""
        if self.driver:
            try:
                self.driver.fill(0x0000)  # Clear to black
                self.driver.text(text, 10, 10, 0xFFFF)  # White text
            except Exception as e:
                print('show_text failed', e)
        else:
            print('TEXT:', text)

    def draw_scaled_png(self, path):
        """Draw a PNG image scaled to display size"""
        if self.driver:
            # Minimal PNG decoder for non-interlaced truecolor 8-bit images (color type 2 or 6)
            try:
                import uzlib
                import struct

                with open(path, 'rb') as f:
                    data = f.read()

                # simple PNG signature check
                if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                    print('Not a PNG:', path)
                    return

                # Parse chunks to find IHDR and concatenated IDAT
                offset = 8
                width = height = None
                bitdepth = None
                colortype = None
                idat_data = b''
                while offset < len(data):
                    if offset + 8 > len(data):
                        break
                    length = struct.unpack('>I', data[offset:offset+4])[0]
                    ctype = data[offset+4:offset+8].decode('ascii')
                    cdata = data[offset+8:offset+8+length]
                    # skip CRC
                    offset = offset + 8 + length + 4
                    if ctype == 'IHDR':
                        width, height, bitdepth, colortype = struct.unpack('>IIBBxxxx', cdata[:13])
                    elif ctype == 'IDAT':
                        idat_data += cdata
                    elif ctype == 'IEND':
                        break

                if not idat_data or width is None:
                    print('PNG missing IDAT or IHDR')
                    return

                # Decompress image data (zlib stream)
                try:
                    decomp = uzlib.decompress(idat_data)
                except Exception as e:
                    # Some PNGs have zlib headers split; try wrapping
                    try:
                        decomp = uzlib.decompress(b'\x78\x9c' + idat_data)
                    except Exception as e2:
                        print('PNG decompress failed', e, e2)
                        return

                # Determine bytes per pixel
                if colortype == 2:
                    bpp = 3
                elif colortype == 6:
                    bpp = 4
                else:
                    print('Unsupported PNG color type', colortype)
                    return

                # Build raw pixel array by parsing scanlines (no interlace)
                row_bytes = width * bpp
                pixels = []
                i = 0
                for y in range(height):
                    if i >= len(decomp):
                        break
                    filter_type = decomp[i]
                    i += 1
                    row = bytearray(decomp[i:i+row_bytes])
                    i += row_bytes
                    # For simplicity, only support filter type 0 (None)
                    if filter_type != 0:
                        print('Unsupported PNG filter type', filter_type)
                        return
                    pixels.append(bytes(row))

                # Scale to display size using nearest-neighbor
                out_w = self.width
                out_h = self.height
                # Prepare buffer line by line and write to display
                for out_y in range(out_h):
                    src_y = int(out_y * height / out_h)
                    row = pixels[src_y]
                    # build RGB565 line
                    line_buf = bytearray()
                    for out_x in range(out_w):
                        src_x = int(out_x * width / out_w)
                        base = src_x * bpp
                        r = row[base]
                        g = row[base+1]
                        b = row[base+2]
                        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                        line_buf.append((rgb565 >> 8) & 0xFF)
                        line_buf.append(rgb565 & 0xFF)
                    # write line to display
                    self.driver._set_window(0, out_y, out_w-1, out_y)
                    if self.driver.cs:
                        self.driver.cs.value(0)
                    if self.driver.dc:
                        self.driver.dc.value(1)
                    self.driver.spi.write(line_buf)
                    if self.driver.cs:
                        self.driver.cs.value(1)
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
