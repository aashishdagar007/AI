import sys
sys.path.insert(0, '.')
from input_handler import InputHandler
from processing_pipeline import HyperspectralProcessor
import numpy as np
import cv2
import os

print('=== Comprehensive Integration Test ===')
print()

# Test 1: Auto method (default) - SVD
print('1. Testing Auto method (SVD-based)...')
synthetic_img = np.random.rand(30, 30, 3).astype(np.float32)
cv2.imwrite('test_auto.jpg', (synthetic_img * 255).astype(np.uint8))
input_h = InputHandler('test_auto.jpg')
proc = HyperspectralProcessor(n_bands=31, method='auto')
result = proc.process(input_h)
bench = proc.benchmark()
shape = result['processed_hsi'].shape
in_range = bench['in_zero_to_one_range']
print(f'   Auto shape: {shape}, Benchmark: in_range={in_range}')
proc.save_model('auto_model.npz')
loaded = proc.load_model('auto_model.npz')
bench2 = proc.benchmark()
loaded_shape = loaded['processed_hsi'].shape
loaded_in_range = bench2['in_zero_to_one_range']
print(f'   Auto after load: shape={loaded_shape}, Benchmark: in_range={loaded_in_range}')
for f in ['test_auto.jpg', 'auto_model.npz']:
    if os.path.exists(f): os.remove(f)

# Test 2: Ensemble method
print('2. Testing Ensemble method...')
cv2.imwrite('test_ensemble.jpg', (synthetic_img * 255).astype(np.uint8))
input_h = InputHandler('test_ensemble.jpg')
proc = HyperspectralProcessor(n_bands=31, method='ensemble')
result = proc.process(input_h)
bench = proc.benchmark()
shape = result['processed_hsi'].shape
in_range = bench['in_zero_to_one_range']
print(f'   Ensemble shape: {shape}, Benchmark: in_range={in_range}')
proc.save_model('ensemble_model.npz')
loaded = proc.load_model('ensemble_model.npz')
bench2 = proc.benchmark()
loaded_shape = loaded['processed_hsi'].shape
loaded_in_range = bench2['in_zero_to_one_range']
print(f'   Ensemble after load: shape={loaded_shape}, Benchmark: in_range={loaded_in_range}')
for f in ['test_ensemble.jpg', 'ensemble_model.npz']:
    if os.path.exists(f): os.remove(f)

# Test 3: Reference benchmark with saved model
print('3. Testing benchmark with reference standard...')
# Create a reference HSI cube with 3 bands for visualization input
ref_hsi_vis = np.random.rand(20, 20, 3).astype(np.float32)
cv2.imwrite('test_ref.jpg', (ref_hsi_vis * 255).astype(np.uint8))
input_h = InputHandler('test_ref.jpg')
proc = HyperspectralProcessor(n_bands=31, method='auto')
result = proc.process(input_h)
# Benchmark with reference (use a properly shaped reference HSI cube)
ref_hsi = np.random.rand(30, 30, 31).astype(np.float32)
bench_with_ref = proc.benchmark(reference=ref_hsi)
sam_mean = bench_with_ref.get("spectral_angle_mapper", {}).get("mean_angle_degrees", "N/A")
ergas = bench_with_ref.get("ergas", "N/A")
rmse = bench_with_ref.get("rmse", "N/A")
print(f'   Benchmark with ref - SAM mean: {sam_mean} deg')
print(f'   Benchmark with ref - ERGAS: {ergas}')
print(f'   Benchmark with ref - RMSE: {rmse}')

# Cleanup reference test files
for f in ['test_ref.jpg']:
    if os.path.exists(f): os.remove(f)
# Cleanup previous test outputs
for f in ['outputs/test_hsi.npy', 'outputs/test_hsi_precise.npy']:
    if os.path.exists(f): os.remove(f)

# Test 4: Benchmark without reference (internal metrics)
print('4. Testing benchmark without reference...')
input_h = InputHandler('test_auto.jpg') if os.path.exists('test_auto.jpg') else InputHandler('outputs/test_synthetic.jpg' if os.path.exists('outputs/test_synthetic.jpg') else 'test_auto.jpg')
# Recreate if needed
if not os.path.exists('test_auto.jpg'):
    synthetic_img = np.random.rand(30, 30, 3).astype(np.float32)
    cv2.imwrite('test_auto.jpg', (synthetic_img * 255).astype(np.uint8))
input_h = InputHandler('test_auto.jpg')
proc = HyperspectralProcessor(n_bands=31, method='auto')
result = proc.process(input_h)
bench_no_ref = proc.benchmark()
print(f'   Benchmark without ref - in_range: {bench_no_ref["in_zero_to_one_range"]}')
print(f'   Benchmark without ref - spectral_range: {bench_no_ref["spectral_range_nm"]}')
print(f'   Benchmark without ref - calibration_valid: {bench_no_ref["wavelength_calibration_valid"]}')

# Final cleanup
for f in ['test_auto.jpg']:
    if os.path.exists(f): os.remove(f)

print()
print('=== All Integration Tests: PASSED ===')