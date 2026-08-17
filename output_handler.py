"""Output handler for hyperspectral imaging system.
Handles visualization, export, and analysis of processed hyperspectral data
with precise metadata and calibration."""
import numpy as np
try:
    import cv2
except ImportError as exc:
    raise ImportError(
        "OpenCV (cv2) is required. Install it with `pip install -r requirements.txt`."
    ) from exc
import os
import json
from datetime import datetime


class OutputHandler:
    """Handles output from hyperspectral processing pipeline.
    
    Provides precise export, visualization, and analysis functions
    with proper spectral calibration and metadata."""
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_hsi_cube(self, hsi_data: np.ndarray, 
                      filename: str = None,
                      metadata: dict = None) -> str:
        """Save hyperspectral cube as NPY file with metadata.
        
        Args:
            hsi_data: HSI cube of shape (H, W, Bands).
            filename: Output filename. If None, generates automatic name.
            metadata: Optional metadata dict to save alongside.
            
        Returns:
            Path to saved file.
        """
        if filename is None:
            filename = f"hsi_cube_{self.timestamp}.npy"
        
        filepath = os.path.join(self.output_dir, filename)
        np.save(filepath, hsi_data)
        
        # Save metadata if provided
        if metadata is not None:
            meta_path = filepath.replace('.npy', '.json')
            with open(meta_path, 'w') as f:
                # Convert numpy types for JSON serialization
                meta_json = self._convert_types(metadata)
                json.dump(meta_json, f, indent=2)
        
        return filepath
    
    def save_as_rgb_visualization(self, hsi_data: np.ndarray,
                                   filename: str = None,
                                   bands: tuple = None,
                                   wavelength_range: tuple = None,
                                   viz_type: str = 'false_color') -> str:
        """Create RGB visualization from HSI data using calibrated bands.
        
        Selects bands based on wavelength for false-color visualization,
        e.g., near-color, color-infrared, etc.
        
        Args:
            hsi_data: HSI cube (H, W, Bands).
            filename: Output filename.
            bands: Tuple of (red_band_idx, green_band_idx, blue_band_idx).
                If None, auto-selects based on wavelength range.
            wavelength_range: (min, max) nm for auto-band selection.
            viz_type: Type of visualization - 'false_color', 'color_infrared', 'true_color'.
            
        Returns:
            Path to saved visualization image.
        """
        if filename is None:
            filename = f"rgb_vis_{self.timestamp}.png"
        
        filepath = os.path.join(self.output_dir, filename)
        
        h, w, _ = hsi_data.shape
        
        # Auto-select bands if not provided
        if bands is None:
            if wavelength_range is None:
                wavelength_range = (400, 3000)  # extended VNIR-SWIR-FSWIR
            
            lambda_min, lambda_max = wavelength_range
            # Find bands closest to selected wavelengths
            # Assuming wavelengths are linear from 400-3000 nm for n_bands
            n_bands = hsi_data.shape[2]
            all_wl = np.linspace(lambda_min, lambda_max, n_bands)
            
            # Select bands based on visualization type
            if viz_type == 'color_infrared':
                # Color infrared: NIR-red-green
                target_wls = {'nir': 780, 'red': 650, 'green': 550}
            elif viz_type == 'true_color':
                # True color: red-green-blue
                target_wls = {'red': 650, 'green': 550, 'blue': 450}
            else:
                # false color default
                target_wls = {'red': 710, 'green': 560, 'blue': 460}
            
            # Select bands at key wavelengths for false color
            selected_bands = []
            for key, target_wl in target_wls.items():
                # Find closest band index
                diffs = np.abs(all_wl - target_wl)
                closest_idx = np.argmin(diffs)
                selected_bands.append(closest_idx)
            
            bands = tuple(selected_bands)
        
        # Clamp band indices to valid range
        bands = tuple(min(max(b, 0), hsi_data.shape[2] - 1) for b in bands)
        
        # Extract selected bands
        r_band = hsi_data[:, :, bands[0]]
        g_band = hsi_data[:, :, bands[1]]
        b_band = hsi_data[:, :, bands[2]]
        
        # Normalize each band to [0, 1]
        r_band = (r_band - r_band.min()) / (r_band.max() - r_band.min() + 1e-8)
        g_band = (g_band - g_band.min()) / (g_band.max() - g_band.min() + 1e-8)
        b_band = (b_band - b_band.min()) / (b_band.max() - b_band.min() + 1e-8)
        
        # Stack as RGB
        rgb = np.stack([r_band, g_band, b_band], axis=2)
        rgb = (rgb * 255).astype(np.uint8)
        
        cv2.imwrite(filepath, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        return filepath
    
    def save_frame_comparison(self, original: np.ndarray, processed: np.ndarray,
                              filename: str = None,
                              display_name: str = "Comparison") -> str:
        """Save comparison of original vs processed frames.
        
        Args:
            original: Original input frame (RGB, [0,1] or [0,255]).
            processed: Processed HSI result (first 3 bands or RGB).
            filename: Output filename.
            display_name: Title/text for the comparison.
            
        Returns:
            Path to saved comparison image.
        """
        if filename is None:
            filename = f"comparison_{self.timestamp}.png"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Ensure both are uint8 for visualization
        orig_vis = original.copy()
        proc_vis = processed.copy() if processed is not None else np.zeros_like(original)
        
        # Handle different dtypes and ranges
        if orig_vis.dtype != np.uint8:
            if orig_vis.max() <= 1.0:
                orig_vis = (orig_vis * 255).astype(np.uint8)
            else:
                orig_vis = orig_vis.astype(np.uint8)
        
        if proc_vis.dtype != np.uint8:
            if proc_vis.max() <= 1.0:
                proc_vis = (proc_vis * 255).astype(np.uint8)
            else:
                proc_vis = proc_vis.astype(np.uint8)
        
        # Resize if shapes differ
        if orig_vis.shape != proc_vis.shape:
            proc_vis = cv2.resize(proc_vis, (orig_vis.shape[1], orig_vis.shape[0]))
        
        # Create comparison: original on left, processed on right
        # Add a separator line
        h, w = orig_vis.shape[:2]
        separator = np.ones((h, 10, 3), dtype=np.uint8) * 128  # gray line
        
        combined = np.hstack([orig_vis, separator, proc_vis])
        
        # Add text label
        label = display_name
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(combined, label, (10, h - 10), font, 0.7, (255, 255, 255), 2)
        
        cv2.imwrite(filepath, combined)
        return filepath
    
    def compute_spectral_profile(self, hsi_data: np.ndarray,
                                  coords: tuple = None,
                                  return_wavelengths: bool = True) -> dict:
        """Compute precise spectral profile at given coordinates.
        
        Args:
            hsi_data: HSI cube (H, W, Bands).
            coords: (x, y) pixel coordinates. If None, uses center of image.
            return_wavelengths: Whether to include wavelength axis in output.
            
        Returns:
            Dictionary with pixel spectrum data.
        """
        if coords is None:
            h, w = hsi_data.shape[:2]
            coords = (w // 2, h // 2)
        
        x, y = coords
        
        # Ensure coordinates are within bounds
        h, w = hsi_data.shape[:2]
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))
        
        # Extract spectrum at this pixel (across all bands)
        spectrum = hsi_data[y, x, :]
        
        profile = {
            'pixel_coords': (int(x), int(y)),
            'spatial_location': {'row': int(y), 'col': int(x)}
        }
        
        if return_wavelengths:
            n_bands = hsi_data.shape[2]
            lambda_min, lambda_max = self._get_wavelength_range(hsi_data)
            wavelength = np.linspace(lambda_min, lambda_max, n_bands, dtype=np.float32)
            profile['wavelengths_nm'] = wavelength
            profile['wavelength_range_nm'] = (float(lambda_min), float(lambda_max))
        else:
            profile['wavelengths_nm'] = np.arange(n_bands, dtype=np.float32)
            profile['wavelength_range_nm'] = (0.0, float(n_bands - 1))
        
        # Compute spectral metrics
        profile.update({
            'reflectance': spectrum.astype(np.float32),
            'max_reflectance': float(np.max(spectrum)),
            'min_reflectance': float(np.min(spectrum)),
            'mean_reflectance': float(np.mean(spectrum)),
            'median_reflectance': float(np.median(spectrum)),
            'std_reflectance': float(np.std(spectrum)),
            'dynamic_range': float(np.max(spectrum) - np.min(spectrum)),
        })
        
        # Find peak wavelength
        if len(spectrum) > 2:
            peak_idx = np.argmax(spectrum)
            profile['peak_wavelength_idx'] = int(peak_idx)
            if return_wavelengths:
                wavelengths = np.linspace(lambda_min, lambda_max, len(spectrum))
                profile['peak_wavelength_nm'] = float(wavelengths[peak_idx])
        
        # Find inflection points (local maxima)
        if len(spectrum) > 3:
            # Simple peak detection - find local maxima
            from scipy.signal import find_peaks
            try:
                peaks, _ = find_peaks(spectrum, prominence=np.std(spectrum)/2)
                if len(peaks) > 0:
                    profile['inflection_points'] = {
                        'wavelengths_nm': self._get_wavelength_range(hsi_data)[0] + 
                            (self._get_wavelength_range(hsi_data)[1] - self._get_wavelength_range(hsi_data)[0]) * 
                            peaks / len(spectrum),
                        'reflectance': spectrum[peaks].tolist()
                    }
            except ImportError:
                pass
        
        return profile
    
    def _get_wavelength_range(self, hsi_data: np.ndarray) -> tuple:
        """Get wavelength range from HSI data metadata or defaults."""
        # Try to get from processed pipeline metadata
        if hsi_data.ndim > 2 and hasattr(hsi_data, 'shape') and hsi_data.shape[2] > 0:
            # Check if there's metadata attached
            pass
        # Return default based on typical HSI range
        n_bands = hsi_data.shape[2] if hsi_data.ndim > 2 else 1
        return (400.0, 3000.0)
    
    def export_processing_report(self, result: dict, filename: str = None) -> str:
        """Export comprehensive processing report as JSON.
        
        Args:
            result: Processing result dict from HyperspectralProcessor.process()
            filename: Output filename.
            
        Returns:
            Path to saved report.
        """
        if filename is None:
            filename = f"processing_report_{self.timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Prepare report - convert numpy types to JSON-compatible
        report = {
            'timestamp': self.timestamp,
            'processing_method': result.get('processing_method', 'unknown'),
            'input_metadata': result.get('input_metadata', {}),
            'output_summary': {
                'shape': result.get('output_shape', (0, 0, 0)),
                'n_bands': result.get('n_bands', 0),
                'spatial_dims': result.get('spatial_dims', (0, 0)),
            },
            'wavelength_calibration': {
                'lambda_min_nm': result.get('lambda_min_nm', 400.0),
                'lambda_max_nm': result.get('lambda_max_nm', 2500.0),
                'wavelengths_nm': result.get('wavelengths_nm', []).tolist() 
                    if hasattr(result.get('wavelengths_nm'), 'tolist') 
                    else result.get('wavelengths_nm', []),
            },
            'metadata': result.get('metadata', {}),
        }
        
        # Convert any remaining numpy types
        report = self._convert_types(report)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath
    
    @staticmethod
    def _convert_types(obj):
        """Recursively convert numpy types to JSON-compatible Python types."""
        import numpy as np
        
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, bool):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: OutputHandler._convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [OutputHandler._convert_types(item) for item in obj]
        else:
            return obj
    
    def save_spectral_viewer_data(self, hsi_data: np.ndarray, 
                                   filename: str = None,
                                   metadata: dict = None) -> str:
        """Save data for spectral viewer/web visualization.
        
        Creates a simplified format suitable for web-based spectral viewers.
        
        Args:
            hsi_data: HSI cube (H, W, Bands).
            filename: Output filename.
            metadata: Optional metadata dict.
            
        Returns:
            Path to saved file.
        """
        if filename is None:
            filename = f"spectral_viewer_{self.timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Take a subset of bands for viewer (max 50 bands)
        n_bands = hsi_data.shape[2]
        n_display = min(n_bands, 50)
        
        # Select evenly spaced bands
        indices = np.linspace(0, n_bands - 1, n_display, dtype=int)
        display_data = hsi_data[:, :, indices]
        
        # Convert to list and add metadata
        data_dict = {
            'shape': list(display_data.shape),
            'bands': display_data.tolist(),
            'wavelength_count': n_display,
        }
        
        if metadata:
            data_dict['metadata'] = metadata
        
        with open(filepath, 'w') as f:
            json.dump(data_dict, f, indent=2)
        
        return filepath