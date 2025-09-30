# Automatic1111 Passthrough Service for Pico LCD

## Project Overview

A standalone Flask/FastAPI service that mimics the Automatic1111 webui API, proxies requests to a real A1111 instance, and converts returned RGB PNGs to Pico-optimized RGB565 raw binary format. This eliminates on-device image processing complexity and memory fragmentation issues discovered during Pico development.

**Target Environment**: Jetson Orin Nano Super Developer Kit (Ubuntu)  
**Architecture**: Python web service with image processing pipeline  
**API Compatibility**: Drop-in replacement for A1111 `/sdapi/v1/txt2img` endpoint  

---

## Technical Requirements

### Hardware Specifications
- **Platform**: NVIDIA Jetson Orin Nano Super Developer Kit
- **OS**: Ubuntu 22.04 LTS (JetPack SDK)
- **Memory**: 8GB RAM (sufficient for image processing)
- **Storage**: Fast NVMe SSD recommended for image caching
- **Network**: Gigabit Ethernet for low-latency A1111 communication

### Software Dependencies
- **Python**: 3.10+ with pip
- **Web Framework**: FastAPI (recommended) or Flask
- **Image Processing**: Pillow (PIL) 9.0+
- **HTTP Client**: httpx (async) or requests
- **Configuration**: python-dotenv, pydantic
- **Production**: uvicorn (ASGI server), nginx (reverse proxy)

---

## API Specification

### Endpoint Design
```
Service listens on: http://jetson-ip:8080
Upstream A1111: http://a1111-host:7860
```

**Primary Endpoint**: `POST /sdapi/v1/txt2img`
- Accepts standard A1111 txt2img request body
- Returns Pico-optimized response with RGB565 data

### Request/Response Flow
1. **Input**: Standard A1111 txt2img JSON payload
2. **Proxy**: Forward request to configured A1111 instance
3. **Convert**: Extract PNG from A1111 response → RGB565 raw binary
4. **Output**: Modified response with RGB565 data + metadata

### Response Format Options
**Option A - Binary Response**:
```http
Content-Type: application/octet-stream
Content-Length: 115200
X-Image-Width: 240
X-Image-Height: 240
X-Image-Format: rgb565-be

[115,200 bytes of RGB565 data]
```

**Option B - Base64 JSON (A1111 compatible)**:
```json
{
  "images": ["<base64-encoded-rgb565>"],
  "parameters": {...},
  "info": "240x240 RGB565 format for Pico LCD"
}
```

---

## Configuration Management

### Environment Variables (.env)
```bash
# Upstream A1111 Configuration
A1111_BASE_URL=http://192.168.1.100:7860
A1111_USERNAME=admin
A1111_PASSWORD=secret123
A1111_TIMEOUT=60

# Service Configuration  
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8080
DEBUG_MODE=false

# Image Processing
TARGET_WIDTH=240
TARGET_HEIGHT=240
LUMINANCE_INVERT=true
ENABLE_CACHING=true
CACHE_DIR=/tmp/pico_images

# Performance
MAX_WORKERS=4
QUEUE_SIZE=10
```

### Configuration Schema (Pydantic)
```python
class Settings(BaseSettings):
    a1111_base_url: HttpUrl
    a1111_username: Optional[str] = None
    a1111_password: Optional[str] = None
    a1111_timeout: int = 60
    
    service_host: str = "0.0.0.0"
    service_port: int = 8080
    
    target_width: int = 240
    target_height: int = 240
    luminance_invert: bool = True
    
    class Config:
        env_file = ".env"
```

---

## Image Processing Pipeline

### Core Conversion Function
Based on validated Pico LCD requirements from `Pico_1.3_LCD_native_RGP.md`:

```python
def png_to_pico_rgb565(png_bytes: bytes, 
                      width: int = 240, 
                      height: int = 240,
                      luminance_invert: bool = True) -> bytes:
    """
    Convert PNG to Pico-optimized RGB565 raw binary.
    
    Format: 240x240 RGB565, big-endian, optional luminance inversion
    Output: Exactly 115,200 bytes (240*240*2)
    """
    img = Image.open(BytesIO(png_bytes)).convert('RGB')
    img = img.resize((width, height), Image.LANCZOS)
    
    data = bytearray()
    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            
            # Apply luminance inversion if needed
            if luminance_invert:
                r, g, b = 255 - r, 255 - g, 255 - b
            
            # Convert to RGB565
            rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            
            # Pack big-endian (high byte first)
            data.append((rgb565 >> 8) & 0xFF)
            data.append(rgb565 & 0xFF)
    
    return bytes(data)
```

### Processing Options
- **Resize Algorithm**: Lanczos (high quality)
- **Color Space**: RGB only (no RGBA/CMYK support)
- **Luminance**: Configurable inversion for displays requiring it
- **Validation**: Ensure output is exactly 115,200 bytes
- **Error Handling**: Graceful fallback for unsupported formats

---

## Service Architecture

### FastAPI Implementation Structure
```
pico-a1111-proxy/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings management
│   ├── models.py            # Pydantic request/response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── a1111_client.py  # Upstream API client
│   │   ├── image_processor.py # PNG→RGB565 conversion
│   │   └── cache.py         # Optional image caching
│   └── routers/
│       ├── __init__.py
│       └── txt2img.py       # Main API endpoints
├── tests/
├── docker/
├── requirements.txt
├── .env.example
└── README.md
```

### Key Components

**1. A1111 Client Service**
- Async HTTP client (httpx)
- Authentication handling (Basic Auth)
- Request/response validation
- Timeout and retry logic
- Error translation

**2. Image Processor Service**
- PNG parsing and validation
- Resize with quality settings
- RGB565 conversion pipeline
- Memory-efficient processing
- Format validation

**3. Caching Layer (Optional)**
- LRU cache for processed images
- Disk-based storage
- Cache invalidation
- Size limits and cleanup

---

## Error Handling & Validation

### Input Validation
- **Request Size**: Limit payload size (10MB max)
- **A1111 Response**: Validate PNG format and size
- **Parameters**: Sanitize width/height/steps
- **Authentication**: Verify upstream credentials

### Error Responses
```python
# A1111 upstream errors
{"error": "Upstream A1111 service unavailable", "code": 502}

# Image processing errors  
{"error": "Failed to process image: unsupported format", "code": 422}

# Configuration errors
{"error": "Invalid A1111 credentials", "code": 401}
```

### Logging Strategy
- **Request Logging**: Track all incoming requests
- **Performance Metrics**: Processing time, cache hits
- **Error Tracking**: Detailed error context
- **Debug Mode**: Request/response dumping

---

## Deployment Configuration

### Systemd Service
```ini
[Unit]
Description=Pico A1111 Proxy Service
After=network.target

[Service]
Type=simple
User=pico-proxy
WorkingDirectory=/opt/pico-a1111-proxy
Environment=PATH=/opt/pico-a1111-proxy/venv/bin
ExecStart=/opt/pico-a1111-proxy/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name jetson-a1111-proxy.local;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Handle large image uploads
        client_max_body_size 50M;
        proxy_read_timeout 120s;
    }
}
```

### Docker Alternative
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Performance Considerations

### Optimization Targets
- **Latency**: < 2 seconds total (A1111 + conversion)
- **Throughput**: Handle 10 concurrent requests
- **Memory**: < 500MB peak usage per request
- **CPU**: Efficient PIL operations on ARM64

### Scaling Strategies
- **Process Pool**: Use multiprocessing for CPU-intensive conversion
- **Async Workers**: uvicorn with multiple workers
- **Queue System**: Redis/Celery for high-load scenarios
- **Caching**: Aggressive caching of processed images

### Monitoring
- **Health Endpoint**: `/health` for status checks
- **Metrics Endpoint**: `/metrics` (Prometheus format)
- **Resource Monitoring**: CPU/memory/disk usage
- **A1111 Status**: Upstream service health

---

## Security Considerations

### Authentication
- **Upstream Auth**: Secure A1111 credentials storage
- **Service Auth**: Optional API key protection
- **Network**: Firewall rules for port access
- **HTTPS**: TLS termination at nginx

### Input Sanitization
- **Parameter Validation**: Strict type checking
- **File Upload Limits**: Size and format restrictions
- **Request Rate Limiting**: Prevent abuse
- **Error Information**: Avoid leaking internal details

---

## Testing Strategy

### Unit Tests
- Image conversion accuracy
- A1111 client functionality
- Configuration validation
- Error handling paths

### Integration Tests
- End-to-end API workflow
- A1111 proxy behavior
- Performance benchmarks
- Error scenarios

### Validation Tests
- **RGB565 Format**: Verify exact byte output
- **Pico Compatibility**: Test with actual Pico hardware
- **Color Accuracy**: Compare source vs converted images
- **Memory Usage**: Profile conversion pipeline

---

## Development Workflow

### Setup Steps
1. **Environment**: Python 3.10+ virtual environment
2. **Dependencies**: `pip install -r requirements.txt`
3. **Configuration**: Copy `.env.example` to `.env`
4. **A1111 Setup**: Configure upstream service details
5. **Testing**: Run test suite against mock A1111

### Development Tools
- **Code Quality**: black, flake8, mypy
- **Testing**: pytest, httpx testing client
- **Documentation**: Sphinx or mkdocs
- **API Docs**: FastAPI auto-generated docs

### Deployment Process
1. **Build**: Create production Docker image
2. **Deploy**: Copy to Jetson, install systemd service
3. **Configure**: Update .env with production settings
4. **Validate**: Test Pico integration end-to-end
5. **Monitor**: Set up logging and metrics collection

---

## Success Criteria

### Functional Requirements
- ✅ **API Compatibility**: Drop-in A1111 replacement
- ✅ **Image Quality**: Accurate RGB565 conversion
- ✅ **Pico Integration**: Seamless display on device
- ✅ **Performance**: < 3 second total response time
- ✅ **Reliability**: 99%+ uptime, graceful error handling

### Technical Validation
- ✅ **Format Accuracy**: 240×240×2 = 115,200 byte output
- ✅ **Color Fidelity**: Visual comparison with source
- ✅ **Memory Efficiency**: No memory leaks or fragmentation
- ✅ **Concurrent Handling**: Multiple simultaneous requests

This project plan provides a complete roadmap for building a production-ready Automatic1111 proxy service optimized for Pico LCD integration, based on the specific technical requirements and format discoveries from this codebase.
