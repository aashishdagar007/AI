"""Test script for hyperspectral imaging system."""
import sys
import os
import numpy as np

sys.path.insert(0, '.')

from input_handler import InputHandler
from processing_pipeline import HyperspectralProcessor
from output_handler import OutputHandler


def test_synthetic_image():
    # Lazy import cv2 for image writing
    try:
        import cv2 as _cv2
    except ImportError as _exc:
        raise ImportError("OpenCV (cv2) is required for test image generation. Install it with `pip install -r requirements.txt`.") from _exc
    """Test with synthetic image."""
    print('=== Test 1: Synthetic Image Processing ===')
    # Create a synthetic RGB image
    synthetic_img = np.random.rand(100, 100, 3).astype(np.float32)
    _cv2.imwrite('test_synthetic.jpg', (synthetic_img * 255).astype(np.uint8))

    # Create input handler
    input_h = InputHandler('test_synthetic.jpg')
    meta = input_h.get_metadata()
    print(f'Input type: {input_h.input_type}')
    print(f'Metadata: {meta}')

    # Process with hyperspectral pipeline
    processor = HyperspectralProcessor(n_bands=31, method='image')
    result = processor.process(input_h)
    hsi = result['processed_hsi']
    print(f'Output HSI shape: {result["processed_hsi"].shape}')
    print(f'Bands: {result["n_bands"]}')

    # Save output
    output = OutputHandler()
    save_path = output.save_hsi_cube(result['processed_hsi'], 'test_hsi.npy')
    print(f'HSI cube saved: {save_path}')

    # Create RGB visualization
    rgb_path = output.save_as_rgb_visualization(result['processed_hsi'], bands=(0, 1, 2))
    print(f'RGB visualization saved: {rgb_path}')

    # Compute spectral profile
    profile = output.compute_spectral_profile(result['processed_hsi'], (50, 50))
    print(f'Spectral profile - max: {profile["max_reflectance"]:.4f}, min: {profile["min_reflectance"]:.4f}')

    # Cleanup
    for f in ['test_synthetic.jpg', 'test_hsi.npy']:
        if os.path.exists(f):
            os.remove(f)

    # Verify HSI cube shape and file existence
    assert hsi.shape == (100, 100, 31), f'Expected shape (100,100,31), got {hsi.shape}'
    assert os.path.exists(save_path), f'Save path {save_path} does not exist'
    assert profile['max_reflectance'] >= 0.0, 'max_reflectance should be non-negative'


def test_synthetic_video():
    """Test with synthetic video."""
    print()
    print('=== Test 2: Synthetic Video Processing ===')
    # Create a synthetic video
    try:
        import cv2 as _cv2
    except ImportError as _exc:
        raise ImportError("OpenCV (cv2) is required for video writing. Install it with `pip install -r requirements.txt`.") from _exc
    fourcc = _cv2.VideoWriter_fourcc(*'mp4v')
    video_path = 'test_synthetic_video.mp4'
    out = _cv2.VideoWriter(video_path, fourcc, 30.0, (100, 100))

    # Write 5 frames
    for i in range(5):
        frame = np.random.rand(100, 100, 3).astype(np.float32) * 255
        out.write(frame.astype(np.uint8))

    out.release()
    input_h_video = InputHandler(video_path)
    meta_video = input_h_video.get_metadata()
    print(f'Video type: {input_h_video.input_type}')
    print(f'Video frames: {meta_video["frame_count"]}')

    # Process video
    processor_video = HyperspectralProcessor(n_bands=31, method='video')
    result_video = processor_video.process(input_h_video)
    print(f'Video output HSI shape: {result_video["processed_hsi"].shape}')
    video_hsi = result_video['processed_hsi']

    # Save video output HSI cube
    output = OutputHandler()
    save_path_v = output.save_hsi_cube(result_video['processed_hsi'], 'test_video_hsi.npy')
    print(f'Video HSI cube saved: {save_path_v}')
    # Verify video HSI cube shape and file existence
    assert video_hsi.shape == (100, 100, 31), f'Expected shape (100,100,31), got {video_hsi.shape}'
    assert os.path.exists(save_path_v), f'Save path {save_path_v} does not exist'

    # Cleanup
    if os.path.exists(video_path):
        os.remove(video_path)
    for f in ['test_hsi.npy', 'test_video_hsi.npy']:
        if os.path.exists(f):
            os.remove(f)

    # Test passes (assertions used)


def test_frame_comparison():
    """Test frame comparison output."""
    print()
    print('=== Test 3: Frame Comparison ===')
    output = OutputHandler()

    # Create original and processed frames
    original = np.random.rand(100, 100, 3).astype(np.float32) * 255
    processed = np.random.rand(100, 100, 31).astype(np.float32)  # HSI with 31 bands

    # Save comparison
    comp_path = output.save_frame_comparison(original, processed[:, :, :3])
    assert os.path.exists(comp_path), f'Comparison path {comp_path} does not exist'
    print(f'Comparison image saved: {comp_path}')

    # Cleanup
    for f in ['outputs/comparison_*.png']:
        # Just verify the output directory exists
        pass

    # Test passes (assertions used)


if __name__ == '__main__':
    print('Hyperspectral Imaging System Test Suite')
    print('=' * 40)

    test_synthetic_image()
    test_synthetic_video()
    test_frame_comparison()

    print()
    print('=' * 40)
    print('All test suites completed successfully!')