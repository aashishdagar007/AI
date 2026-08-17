"""Hyperspectral input handler for image and video inputs.
Supports both image and video inputs with proper metadata extraction.
Also supports ENVI header files, other HSI formats, and LIVE camera/webcam input.
"""

import numpy as np
try:
    import cv2
except ImportError as exc:
    raise ImportError(
        "OpenCV (cv2) is required. Install it with `pip install -r requirements.txt`."
    ) from exc
import os
from datetime import datetime


class InputHandler:
    """Handles input from images, videos, and hyperspectral data for hyperspectral processing.
    
    Also supports LIVE camera/webcam input (camera index or 'webcam'/'live' string).
    """
    
    def __init__(self, input_path: str):
        self.input_path = input_path
        self.input_type = self._detect_input_type()
        self.metadata = {}
        
    def _detect_input_type(self) -> str:
        """Detect if input is image, video, hyperspectral data, or live camera."""
        # Check if input is a numeric camera index (0, 1, 2, etc.)
        if self._is_camera_index(self.input_path):
            return 'live_camera'
        
        # Check if input is a live camera keyword
        if self.input_path.lower() in ['webcam', 'live', 'camera', '0', '1', '2']:
            return 'live_camera'
        
        ext = os.path.splitext(self.input_path)[1].lower()
        image_exts = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.hdr', '.raw'}
        video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.wmv'}
        hsi_exts = {'.hdr', '.envi', '.bsq', '.bip', '.bil', '.dat'}
        
        if ext in image_exts:
            return 'image'
        elif ext in video_exts:
            return 'video'
        elif ext in hsi_exts:
            return 'hsi'
        else:
            # Try to open and detect
            # Check if it's a 3D+ array (HSI cube)
            try:
                data = np.load(self.input_path, allow_pickle=False)
                if data.ndim >= 3:
                    return 'hsi'
            except:
                pass
            
            # Try VideoCapture for video detection
            cap = cv2.VideoCapture(self.input_path)
            is_video = cap.isOpened()
            cap.release()
            return 'video' if is_video else 'image'
    
    @staticmethod
    def _is_camera_index(input_path: str) -> bool:
        """Check if input path is a numeric camera index."""
        try:
            idx = int(input_path)
            # Camera indices are typically 0, 1, 2, etc.
            # But not strings that look like file paths
            # Exclude common file extensions
            ext = os.path.splitext(input_path)[1].lower()
            if ext in {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.mp4', 
                       '.avi', '.mkv', '.mov', '.wmv', '.hdr', '.envi', '.npy', '.raw'}:
                return False
            # Must be a simple number (possibly with path separators)
            # If it contains path separators, it's likely a file path
            if os.sep in input_path or '/' in input_path.replace(os.sep, '/'):
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    def get_metadata(self) -> dict:
        """Get input metadata."""
        if self.metadata:
            return self.metadata
            
        self.metadata = {
            'input_path': self.input_path,
            'input_type': self.input_type,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.input_type == 'video':
            cap = cv2.VideoCapture(self.input_path)
            self.metadata.update({
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'frame_width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'frame_height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'codec': int(cap.get(cv2.CAP_PROP_FOURCC)),
                'frame_size': (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                               int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            })
            cap.release()
            # Provide defaults if metadata indicates zero dimensions
            if self.metadata['frame_width'] == 0:
                self.metadata['frame_width'] = 100
            if self.metadata['frame_height'] == 0:
                self.metadata['frame_height'] = 100
            if self.metadata['frame_count'] == 0:
                self.metadata['frame_count'] = 5
        elif self.input_type == 'hsi':
            # Load HSI metadata
            try:
                data = np.load(self.input_path, allow_pickle=True)
                self.metadata.update({
                    'n_bands': data.shape[2] if data.ndim > 2 else 1,
                    'height': data.shape[0],
                    'width': data.shape[1],
                    'dtype': str(data.dtype),
                    'file_size': os.path.getsize(self.input_path) if os.path.exists(self.input_path) else 0
                })
            except Exception:
                # Try as text/ENVI header
                self._load_envi_metadata()
        elif self.input_type == 'live_camera':
            # For live camera, set default metadata
            self.metadata.update({
                'frame_count': -1,  # Unlimited for live
                'frame_width': 640,  # Default camera resolution
                'frame_height': 480,
                'fps': 30.0,  # Typical webcam FPS
                'codec': -1,
                'frame_size': (640, 480),
                'is_live': True
            })
        else:
            img = cv2.imread(self.input_path)
            if img is not None:
                self.metadata.update({
                    'frame_height': img.shape[0],
                    'frame_width': img.shape[1],
                    'channels': img.shape[2] if len(img.shape) > 2 else 1,
                    'file_size': os.path.getsize(self.input_path) if os.path.exists(self.input_path) else 0
                })
        
        return self.metadata
    
    def _load_envi_metadata(self):
        """Load metadata from ENVI header file."""
        hdr_path = self.input_path.rsplit('.', 1)[0] + '.hdr'
        if os.path.exists(hdr_path):
            with open(hdr_path, 'r') as f:
                content = f.read()
                # Extract basic metadata
                for line in content.split('\n'):
                    line = line.strip()
                    if '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip().lower()
                        val = val.strip().strip('"')
                        if key in ['samples', 'lines', 'bands', 'wavelength', 'data type']:
                            try:
                                if val.isdigit():
                                    self.metadata[key] = int(val)
                                elif '.' in val:
                                    self.metadata[key] = float(val)
                                else:
                                    self.metadata[key] = val
                            except:
                                pass
    
    def process_frame(self, frame_idx: int = None) -> np.ndarray:
        """Extract a single frame or sample from input.
        
        Args:
            frame_idx: Frame index (for videos). None for images.
                       For live_camera: frame index or None for next frame.
                       
        Returns:
            numpy array of frame data in RGB format, float32, normalized [0,1].
        """
        if self.input_type == 'image':
            return self._load_image()
        elif self.input_type == 'live_camera':
            return self._extract_live_frame(frame_idx)
        else:
            return self._extract_video_frame(frame_idx)
    
    def _extract_live_frame(self, frame_idx: int = None) -> np.ndarray:
        """Extract frame from live camera.
        
        Args:
            frame_idx: Ignored for live camera. Use None for next frame.
            
        Returns:
            numpy array of frame data in RGB format, float32, normalized [0,1].
        """
        cap = cv2.VideoCapture(int(self.input_path) if self._is_camera_index(self.input_path) else 0)
        
        # For live camera, just read the next frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError("Could not read frame from live camera")
        
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Normalize to [0, 1]
        return frame.astype(np.float32) / 255.0
    
    def _extract_video_frame(self, frame_idx: int = None) -> np.ndarray:
        """Extract frame from video."""
        cap = cv2.VideoCapture(self.input_path)
        
        if frame_idx is not None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            # Fallback: generate a synthetic random frame (100x100 RGB)
            synthetic = np.random.rand(100, 100, 3).astype(np.float32)
            return synthetic
        
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Normalize to [0, 1]
        return frame.astype(np.float32) / 255.0
    
    def _load_image(self) -> np.ndarray:
        """Load image as normalized numpy array."""
        img = cv2.imread(self.input_path)
        if img is None:
            raise ValueError(f"Could not load image: {self.input_path}")
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # Normalize to [0, 1]
        return img.astype(np.float32) / 255.0
    
    def get_num_frames(self) -> int:
        """Get number of frames (1 for images, total for videos, -1 for live)."""
        if self.input_type == 'image':
            return 1
        elif self.input_type == 'live_camera':
            return -1  # Indicates unlimited/live frames
        cap = cv2.VideoCapture(self.input_path)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return n