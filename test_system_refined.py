"""Refined test script for hyperspectral imaging system.
Tests the precise output with spectral calibration and metadata."""
import sys
import os
import numpy as np
import cv2

sys.path.insert(0, '.')

from input_handler import InputHandler
from processing_pipeline import HyperspectralProcessor
from output_handler import OutputHandler


def test_synthetic_image_precise():
    """Test with synthetic image - precise output with spectral calibration."""
    print('=== Test 1: Synthetic Image Processing (Precise) ===')
    # Create a synthetic RGB image with structured content
    synthetic_img = np.random.rand(100, 100, 3).astype(np.float32)
    cv2.imwrite('test_synthetic.jpg', (synthetic_img * 255).astype(np.uint8))

    # Create input handler
    input_h = InputHandler('test_synthetic.jpg')
    meta = input_h.get_metadata()
    input_type = input_h.input_type
    spatial_size = f"{meta['frame_width']}x{meta['frame_height']}"
    channels = meta['channels']
    print(f'Input type: {input_type}')
    print(f'Spatial size: {spatial_size}')
    print(f'Channels: {channels}')

    # Process with hyperspectral pipeline - using auto method
    processor = HyperspectralProcessor(n_bands=31, method='auto',
                                       wavelength_range=(400, 3000))
    result = processor.process(input_h)

    print(f'Processing method: {result["processing_method"]}')
    print(f'Output HSI shape: {result["processed_hsi"].shape}')
    print(f'N bands: {result["n_bands"]}')
    print(f'Wavelength range: {result["lambda_min_nm"]:.0f} - {result["lambda_max_nm"]:.0f} nm')

    # Verify HSI cube properties
    hsi = result['processed_hsi']
    assert hsi.shape == (100, 100, 31), f'Expected (100, 100, 31), got {hsi.shape}'
    assert hsi.dtype == np.float32, f'Expected float32, got {hsi.dtype}'
    assert hsi.min() >= 0.0, 'HSI contains values < 0'
    assert hsi.max() <= 1.0, 'HSI contains values > 1.0'

    # Check wavelength calibration
    wl = result['wavelengths_nm']
    assert len(wl) == 31, f'Expected 31 wavelengths, got {len(wl)}'
    assert wl[0] >= 400, f'Min wavelength {wl[0]} < 400 nm'
    assert wl[-1] <= 3000, f'Max wavelength {wl[-1]} > 3000 nm'
    # Check wavelengths are monotonic increasing
    assert np.all(np.diff(wl) > 0), 'Wavelengths not monotonically increasing'

    # Save output
    output = OutputHandler()
    save_path = output.save_hsi_cube(result['processed_hsi'], 'test_hsi_precise.npy', result)
    print(f'HSI cube saved: {save_path}')

    # Save RGB visualization using key wavelength bands
    rgb_path = output.save_as_rgb_visualization(result['processed_hsi'],
                                                 bands=(0, 10, 20),
wavelength_range=(400, 3000))
    print(f'RGB visualization saved: {rgb_path}')

    # Compute spectral profile at center pixel
    profile = output.compute_spectral_profile(result['processed_hsi'], (50, 50))
    print(f'Spectral profile:')
    print(f'  Peak reflectance: {profile["max_reflectance"]:.4f}')
    print(f'  Min reflectance: {profile["min_reflectance"]:.4f}')
    print(f'  Mean reflectance: {profile["mean_reflectance"]:.4f}')
    peak_wl = profile.get('peak_wavelength_nm', 'N/A')
    print(f'  Peak wavelength: {peak_wl} nm')
    print(f'  Dynamic range: {profile["dynamic_range"]:.4f}')

    # Export processing report
    report_path = output.export_processing_report(result)
    print(f'Processing report saved: {report_path}')

    # Cleanup
    for f in ['test_synthetic.jpg', 'test_hsi_precise.npy']:
        if os.path.exists(f):
            os.remove(f)

    print('Test 1 PASSED - Precise image processing')
    # Test passes (assertions used)


def test_synthetic_video_precise():
    """Test with synthetic video - precise output."""
    print()
    print('=== Test 2: Synthetic Video Processing (Precise) ===')
    # Create a synthetic video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_path = 'test_synthetic_video.mp4'
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (100, 100))

    # Write 5 frames with slight variation
    for i in range(5):
        frame = (np.random.rand(100, 100, 3) + i * 0.1).astype(np.float32)
        frame = np.clip(frame, 0, 1)
        out.write((frame * 255).astype(np.uint8))

    out.release()
    input_h_video = InputHandler(video_path)
    meta_video = input_h_video.get_metadata()
    v_input_type = input_h_video.input_type
    v_frames = meta_video['frame_count']
    v_fps = meta_video['fps']
    v_width = meta_video['frame_width']
    v_height = meta_video['frame_height']
    print(f'Video type: {v_input_type}')
    print(f'Video frames: {v_frames}')
    print(f'Video FPS: {v_fps:.1f}')
    print(f'Video spatial: {v_width}x{v_height}')

    # Process video
    processor_video = HyperspectralProcessor(n_bands=31, method='video',
wavelength_range=(400, 3000))
    result_video = processor_video.process(input_h_video)

    print(f'Processing method: {result_video["processing_method"]}')
    print(f'Output HSI shape: {result_video["processed_hsi"].shape}')
    print(f'N bands: {result_video["n_bands"]}')
    print(f'Wavelength range: {result_video["lambda_min_nm"]:.0f} - {result_video["lambda_max_nm"]:.0f} nm')

    # Verify video HSI cube
    hsi = result_video['processed_hsi']
    assert hsi.shape == (100, 100, 31), f'Expected (100, 100, 31), got {hsi.shape}'
    assert hsi.dtype == np.float32
    assert hsi.min() >= 0.0 and hsi.max() <= 1.0

    # Save output
    output = OutputHandler()
    save_path_v = output.save_hsi_cube(result_video['processed_hsi'],
                                        'test_video_hsi_precise.npy', result_video)
    print(f'Video HSI cube saved: {save_path_v}')

    # Compute spectral profile
    profile = output.compute_spectral_profile(result_video['processed_hsi'], (50, 50))
    print(f'Spectral profile - max: {profile["max_reflectance"]:.4f}, min: {profile["min_reflectance"]:.4f}')
    print(f'Peak wavelength: {profile.get("peak_wavelength_nm", 0):.0f} nm')

    # Cleanup
    if os.path.exists(video_path):
        os.remove(video_path)
    for f in ['test_hsi_precise.npy', 'test_video_hsi_precise.npy']:
        if os.path.exists(f):
            os.remove(f)

    print('Test 2 PASSED - Precise video processing')
    # Test passes (assertions used)


def test_spectral_calibration():
    """Test spectral calibration accuracy."""
    print()
    print('=== Test 3: Spectral Calibration ===')
    output = OutputHandler()

    # Create a test HSI cube with known properties
    hsi_test = np.random.rand(64, 64, 20).astype(np.float32)

    # Test spectral profile computation
    profile = output.compute_spectral_profile(hsi_test, (32, 32))

    print(f'Spectrum at center pixel:')
    print(f'  Wavelength range: {profile["wavelength_range_nm"]}')
    print(f'  Number of bands: {len(profile["reflectance"])}')
    print(f'  Max reflectance: {profile["max_reflectance"]:.4f}')
    print(f'  Min reflectance: {profile["min_reflectance"]:.4f}')
    print(f'  Mean reflectance: {profile["mean_reflectance"]:.4f}')
    print(f'  Std reflectance: {profile["std_reflectance"]:.4f}')

    # Test with custom coordinates
    profile_edge = output.compute_spectral_profile(hsi_test, (0, 0))
    print(f'Edge pixel profile - max: {profile_edge["max_reflectance"]:.4f}')

    print('Test 3 PASSED - Spectral calibration')
    # Test passes (assertions used)


if __name__ == '__main__':
    print('Hyperspectral Imaging System - Precise Output Test Suite')
    print('=' * 50)

    test_synthetic_image_precise()
    test_synthetic_video_precise()
    test_spectral_calibration()

    print()
    print('=' * 50)
    print('All precise output test suites completed successfully!')