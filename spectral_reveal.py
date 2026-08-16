"""
Spectral Reveal — Stylized Hyperspectral Visualization
=======================================================
IMPORTANT DISCLAIMER:
    This script produces a PURELY ARTISTIC / VISUAL EFFECT.
    All "spectral" data is SYNTHETICALLY GENERATED from a standard RGB image
    through mathematical decomposition (SVD + band expansion). No real hidden
    or invisible spectral information is detected or measured — the tool
    cannot see beyond what a normal camera already captures.
    The "reveal" is entirely image processing, not physical spectral measurement.
    Think of it as a creative filter, not a scientific instrument.

Usage:
    python spectral_reveal.py                       # all images in Inputs/
    python spectral_reveal.py path/to/image.jpg     # single specific image
    python spectral_reveal.py path/to/folder/       # all images in that folder

Outputs (written to outputs/ folder):
    <name>_spectral_reveal.png            — full composite reveal image
    <name>_spectral_reveal_comparison.png — side-by-side original vs reveal
"""

import sys
import os
import numpy as np
import cv2
from pathlib import Path

# Project modules
from input_handler import InputHandler
from processing_pipeline import HyperspectralProcessor
from output_handler import OutputHandler


# ---------------------------------------------------------------------------
# Spectral analysis helpers
# ---------------------------------------------------------------------------

def compute_anomaly_map(hsi_cube):
    """Compute per-pixel spectral angle distance from the scene mean spectrum.

    For each pixel, the Spectral Angle Mapper (SAM) distance measures how
    different that pixel's synthetic spectrum is from the image-wide average.
    High values = pixels whose spectral profile deviates most from the norm.

    Args:
        hsi_cube: float32 array of shape (H, W, n_bands), values in [0, 1].

    Returns:
        Normalized float32 anomaly map of shape (H, W), values in [0, 1].
    """
    h, w, n_bands = hsi_cube.shape
    flat = hsi_cube.reshape(-1, n_bands).astype(np.float64)

    # Mean spectrum across all pixels
    mean_spectrum = flat.mean(axis=0)  # (n_bands,)
    mean_norm = np.linalg.norm(mean_spectrum) + 1e-10

    # Per-pixel norms
    pixel_norms = np.linalg.norm(flat, axis=1) + 1e-10  # (n_pixels,)

    # Cosine similarity with the mean spectrum
    dot_products = flat @ mean_spectrum  # (n_pixels,)
    cosine_sim = dot_products / (pixel_norms * mean_norm)
    cosine_sim = np.clip(cosine_sim, -1.0, 1.0)

    # Spectral angle: 0 = identical to mean, pi/2 = maximally different
    spectral_angle = np.arccos(cosine_sim).reshape(h, w).astype(np.float32)

    # Normalize to [0, 1]
    a_min, a_max = spectral_angle.min(), spectral_angle.max()
    if a_max - a_min > 1e-8:
        return (spectral_angle - a_min) / (a_max - a_min)
    return np.zeros((h, w), dtype=np.float32)


def build_false_color(hsi_cube):
    """Build false-color RGB using 3 bands spread across the spectral range.

    Bands at ~5%, ~50%, ~95% of n_bands are mapped to R, G, B respectively
    to produce a vivid false-color rendering.

    Args:
        hsi_cube: float32 (H, W, n_bands).

    Returns:
        uint8 RGB image (H, W, 3).
    """
    n_bands = hsi_cube.shape[2]
    r_idx = max(0, int(0.05 * (n_bands - 1)))
    g_idx = int(0.50 * (n_bands - 1))
    b_idx = min(n_bands - 1, int(0.95 * (n_bands - 1)))

    def norm_channel(ch):
        mn, mx = ch.min(), ch.max()
        if mx - mn > 1e-8:
            return ((ch - mn) / (mx - mn)).astype(np.float32)
        return np.zeros_like(ch)

    r = norm_channel(hsi_cube[:, :, r_idx])
    g = norm_channel(hsi_cube[:, :, g_idx])
    b = norm_channel(hsi_cube[:, :, b_idx])

    rgb = np.stack([r, g, b], axis=2)
    return (rgb * 255).astype(np.uint8)


def screen_blend(base, overlay):
    """Photoshop-style screen blend.

    result = 1 - (1 - base) * (1 - overlay)
    Both inputs and output are float32 in [0, 1].
    """
    return 1.0 - (1.0 - base) * (1.0 - overlay)


# ---------------------------------------------------------------------------
# Main compositing function
# ---------------------------------------------------------------------------

def build_spectral_reveal(original_rgb, hsi_cube):
    """Build the full spectral reveal composite image.

    Pipeline:
        1. False-color base from 3 spread HSI bands (R/G/B <- low/mid/high band)
        2. Ghostly glow from Gaussian-blurred anomaly map in cyan/violet tones,
           screen-blended onto the false-color base.
        3. Subtle edge overlay (Canny on original grey, lightly blurred)
           blended in at low opacity for structure.

    Args:
        original_rgb: float32 (H, W, 3) in [0, 1], original input image.
        hsi_cube:     float32 (H, W, n_bands) in [0, 1], processed HSI cube.

    Returns:
        uint8 RGB composite image (H, W, 3).
    """
    h, w = original_rgb.shape[:2]

    # Step 1: false-color base
    false_color = build_false_color(hsi_cube).astype(np.float32) / 255.0  # [0,1]

    # Step 2: ghostly glow from anomaly map
    anomaly = compute_anomaly_map(hsi_cube)  # (h, w), [0,1]

    # Gaussian blur radius proportional to image size
    blur_sigma = max(3.0, min(h, w) / 40.0)
    anomaly_blurred = cv2.GaussianBlur(
        anomaly, (0, 0), sigmaX=blur_sigma, sigmaY=blur_sigma
    )

    # Map to cyan/violet: green and blue channels carry most of the glow
    glow_r = (anomaly_blurred * 0.45).astype(np.float32)   # violet tint
    glow_g = (anomaly_blurred * 0.75).astype(np.float32)   # cyan dominant
    glow_b = (anomaly_blurred * 0.95).astype(np.float32)   # strong blue
    glow = np.stack([glow_r, glow_g, glow_b], axis=2)

    # Screen-blend glow onto false-color base
    result = screen_blend(false_color, glow).astype(np.float32)

    # Step 3: edge overlay from original
    orig_u8 = (np.clip(original_rgb, 0, 1) * 255).astype(np.uint8)
    orig_gray = cv2.cvtColor(orig_u8, cv2.COLOR_RGB2GRAY)

    edges = cv2.Canny(orig_gray, threshold1=40, threshold2=120).astype(np.float32) / 255.0
    edges = cv2.GaussianBlur(edges, (0, 0), sigmaX=1.2, sigmaY=1.2)
    edges = np.clip(edges * 2.5, 0, 1)  # brighten slightly

    edge_rgb = np.stack([edges, edges, edges], axis=2)
    edge_opacity = 0.22
    result = result * (1.0 - edge_opacity * edge_rgb) + edge_rgb * edge_opacity

    result = np.clip(result, 0, 1)
    return (result * 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# File discovery helpers
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}


def find_images(path):
    """Return sorted list of image paths.

    If path is a file, returns [path].
    If path is a directory, returns all image files directly inside it.
    """
    p = Path(path)
    if p.is_file() and p.suffix in _IMAGE_EXTENSIONS:
        return [str(p)]
    if p.is_dir():
        return sorted(
            str(f) for f in p.iterdir()
            if f.is_file() and f.suffix in _IMAGE_EXTENSIONS
        )
    return []


def default_input_folder(script_dir):
    """Locate the default input folder, trying common capitalizations."""
    for name in ('Inputs', 'inputs', 'input', 'Input'):
        candidate = os.path.join(script_dir, name)
        if os.path.isdir(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Per-image processing
# ---------------------------------------------------------------------------

def process_image(image_path, output_dir):
    """Run the full spectral reveal pipeline for a single image.

    Saves:
        <stem>_spectral_reveal.png            - composite reveal
        <stem>_spectral_reveal_comparison.png - side-by-side original vs reveal

    Raises:
        Any exception encountered during processing (caller catches and prints).
    """
    stem = Path(image_path).stem

    print(f"  > {image_path}")

    # Load input
    input_h = InputHandler(image_path)
    original_frame = input_h.process_frame()  # float32 RGB [0,1], (H,W,3)

    # Process through HSI pipeline (SVD-based, 31 bands, 400-3000 nm)
    processor = HyperspectralProcessor(
        n_bands=31,
        method='auto',
        wavelength_range=(400, 3000),
    )
    result = processor.process(input_h)
    hsi_cube = result['processed_hsi']  # (H, W, 31), float32, [0,1]

    # Build spectral reveal composite
    reveal_rgb = build_spectral_reveal(original_frame, hsi_cube)  # uint8 (H,W,3)

    # Save reveal PNG
    reveal_filename = f"{stem}_spectral_reveal.png"
    reveal_path = os.path.join(output_dir, reveal_filename)
    cv2.imwrite(reveal_path, cv2.cvtColor(reveal_rgb, cv2.COLOR_RGB2BGR))
    print(f"    Saved reveal:      {reveal_path}")

    # Save side-by-side comparison
    output_h = OutputHandler(output_dir)
    comp_path = output_h.save_frame_comparison(
        original=original_frame,                           # float32 [0,1]
        processed=reveal_rgb.astype(np.float32) / 255.0,  # float32 [0,1]
        filename=f"{stem}_spectral_reveal_comparison.png",
        display_name=f"Spectral Reveal: {stem}",
    )
    print(f"    Saved comparison:  {comp_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Determine input source
    if len(sys.argv) > 1:
        input_source = sys.argv[1]
    else:
        input_source = default_input_folder(script_dir)
        if input_source is None:
            print(
                "Error: No default input folder found (tried Inputs/, input/, etc.).\n"
                "Usage: python spectral_reveal.py [image_path | folder_path]"
            )
            sys.exit(1)
        print(f"Using default input folder: {input_source}")

    # Find images
    image_paths = find_images(input_source)
    if not image_paths:
        print(f"No image files found at: {input_source}")
        sys.exit(1)

    # Output directory
    output_dir = os.path.join(script_dir, 'outputs')
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Spectral Reveal -- Synthetic Hyperspectral Visualization")
    print("NOTE: Visual effect only; no real spectral data is captured.")
    print("=" * 60)
    print(f"Images found : {len(image_paths)}")
    print(f"Output folder: {output_dir}")
    print()

    # Process each image, catching per-image errors
    succeeded = []
    failed = []

    for img_path in image_paths:
        try:
            process_image(img_path, output_dir)
            succeeded.append(img_path)
        except Exception as exc:
            failed.append((img_path, str(exc)))
            print(f"    ERROR: {exc}")

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print(f"  Images found  : {len(image_paths)}")
    print(f"  Succeeded     : {len(succeeded)}")
    print(f"  Failed        : {len(failed)}")
    if failed:
        print("  Failure details:")
        for path, err in failed:
            print(f"    - {Path(path).name}: {err}")
    print("=" * 60)


if __name__ == '__main__':
    main()
