import os
import numpy as np
from io import BytesIO
try:
    from PIL import Image
except ImportError:
    raise ImportError("Pillow is required for cv2 stub. Install with `pip install pillow`.")

# Constants
COLORMAP_JET = 0
COLOR_RGB2BGR = None
COLOR_BGR2RGB = None
FONT_HERSHEY_SIMPLEX = None
CAP_PROP_POS_FRAMES = 0
CAP_PROP_FRAME_COUNT = 1
CAP_PROP_FRAME_WIDTH = 2
CAP_PROP_FRAME_HEIGHT = 3
CAP_PROP_FPS = 4
CAP_PROP_FOURCC = 5

def imwrite(filename, img):
    """Write an image to file. Expects BGR uint8 numpy array."""
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    # Convert BGR to RGB for saving
    if img.ndim == 3 and img.shape[2] == 3:
        img_rgb = img[..., ::-1]
    else:
        img_rgb = img
    Image.fromarray(img_rgb).save(filename)
    return True

def imread(filename):
    """Read an image from file and return BGR uint8 array."""
    img = Image.open(filename)
    img = np.array(img)
    if img.ndim == 3 and img.shape[2] == 3:
        img = img[..., ::-1]
    return img.astype(np.uint8)

def VideoWriter(filename, fourcc, fps, size):
    class DummyWriter:
        def __init__(self):
            self.frames = []
            self.filename = filename
            self.size = size
            self.fps = fps
        def write(self, frame):
            self.frames.append(frame.copy())
        def release(self):
            np.save(self.filename, np.array(self.frames, dtype=object))
    return DummyWriter()

def VideoWriter_fourcc(*args):
    return 0

def VideoCapture(source):
    class DummyCapture:
        def __init__(self, src):
            self.src = src
            self.opened = True
            self.idx = 0
            self.frames = []
            if isinstance(src, str) and os.path.exists(src):
                try:
                    loaded = np.load(src, allow_pickle=True)
                    self.frames = list(loaded)
                except Exception:
                    self.frames = []
        def isOpened(self):
            return self.opened
        def read(self):
            if self.idx < len(self.frames):
                frame = self.frames[self.idx]
                self.idx += 1
                return True, frame
            return False, None
        def release(self):
            self.opened = False
        def set(self, prop, value):
            if prop == CAP_PROP_POS_FRAMES:
                self.idx = int(value)
        def get(self, prop):
            if prop == CAP_PROP_FRAME_COUNT:
                return len(self.frames)
            if prop == CAP_PROP_FRAME_WIDTH and self.frames:
                return self.frames[0].shape[1]
            if prop == CAP_PROP_FRAME_HEIGHT and self.frames:
                return self.frames[0].shape[0]
            if prop == CAP_PROP_FPS:
                return 30.0
            if prop == CAP_PROP_FOURCC:
                return 0
            return 0
    return DummyCapture(source)

def resize(img, dsize):
    if isinstance(dsize, tuple):
        width, height = dsize
    else:
        width, height = dsize
    pil = Image.fromarray(img)
    resized = pil.resize((width, height), Image.NEAREST)
    return np.array(resized)

def applyColorMap(img, colormap):
    if img.ndim == 2:
        img = np.stack([img]*3, axis=2)
    return img.astype(np.uint8)

def GaussianBlur(img, ksize, sigmaX, sigmaY=None):
    return img

def Canny(image, threshold1, threshold2):
    return np.zeros_like(image)

def putText(img, text, org, font, fontScale, color, thickness):
    return img

def imencode(ext, img):
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    if img.ndim == 3 and img.shape[2] == 3:
        img_rgb = img[..., ::-1]
    else:
        img_rgb = img
    buffer = BytesIO()
    Image.fromarray(img_rgb).save(buffer, format='PNG')
    data = np.frombuffer(buffer.getvalue(), dtype=np.uint8)
    return True, data

def cvtColor(src, code):
    if src.ndim == 3 and src.shape[2] == 3:
        return src[..., ::-1]
    return src

__all__ = [
    'imwrite', 'imread', 'VideoWriter', 'VideoWriter_fourcc', 'VideoCapture',
    'resize', 'applyColorMap', 'GaussianBlur', 'Canny', 'putText',
    'imencode', 'cvtColor',
    'COLORMAP_JET', 'COLOR_RGB2BGR', 'COLOR_BGR2RGB', 'FONT_HERSHEY_SIMPLEX',
    'CAP_PROP_POS_FRAMES', 'CAP_PROP_FRAME_COUNT', 'CAP_PROP_FRAME_WIDTH',
    'CAP_PROP_FRAME_HEIGHT', 'CAP_PROP_FPS', 'CAP_PROP_FOURCC'
]
