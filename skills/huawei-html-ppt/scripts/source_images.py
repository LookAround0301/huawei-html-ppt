"""Embed local source figures unchanged; never fetch remote material."""
from pathlib import Path
import base64
import hashlib
import html


def read_image(spec):
    if not isinstance(spec, dict):
        raise ValueError('image must be an object')
    value = spec.get('path')
    if not isinstance(value, str) or '://' in value or value.startswith('data:'):
        raise ValueError('image.path must name a local file')
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise ValueError('image.path must be an existing absolute local file')
    if not isinstance(spec.get('alt'), str) or not spec['alt'].strip():
        raise ValueError('image.alt must describe the figure')
    source = spec.get('source')
    if not isinstance(source, dict) or not source or not any(source.values()):
        raise ValueError('image.source must record its original reference')
    data = path.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    elif data.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        mime = 'image/gif'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        mime = 'image/webp'
    else:
        raise ValueError('image must be PNG, JPEG, GIF or WebP; export other figures locally first')
    return data, mime


def image_html(spec):
    data, mime = read_image(spec)
    uri = 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')
    alt = html.escape(spec['alt'], quote=True)
    sha = hashlib.sha256(data).hexdigest()
    return (f'<figure class="source-figure"><img src="{uri}" alt="{alt}" '
            f'data-source-sha256="{sha}"></figure>')
