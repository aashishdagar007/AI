import sys
import sys as _sys
(_sys.path.insert(0, _sys.path[0]) if not any(_sys.path[0].startswith(d) for d in ['D:\\AASHISH\\Projects\\AI', '']) else None)

import tempfile
import os
from flask import Flask, render_template, request, Response
import cv2
import numpy as np
from input_handler import InputHandler
from processing_pipeline import HyperspectralProcessor

app = Flask(__name__)

# Global processor instance
processor = None

def init_processor():
    global processor
    processor = HyperspectralProcessor(n_bands=31, method='auto')

def release_resources():
    pass

def process_frame_to_hsi(frame_bgr, source_type, source_index):
    """Process a single BGR frame through the HSI pipeline.
    
    Args:
        frame_bgr: Input frame in BGR format (from OpenCV)
        source_type: 'live' or 'pre-recorded'
        source_index: camera index or file path
        
    Returns:
        combined_frame_bgr: 200x100x3 concatenated image for streaming
    """
    global processor
    if processor is None:
        init_processor()
    
    try:
        # Resize frame for processing - always use 100x100 for HSI processing
        small_frame = cv2.resize(frame_bgr, (100, 100))
        small_frame_norm = small_frame.astype(np.float32) / 255.0  # Normalize to [0,1]
        
        # Save frame to temporary file for InputHandler
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
            # Save the normalized frame (denormalize for saving to [0,255])
            cv2.imwrite(tmp_path, (small_frame_norm * 255).astype(np.uint8))
        
        try:
            # Create input handler based on source type
            if source_type == 'live':
                # For live camera, use the index
                input_h = InputHandler(str(source_index))
                input_h.input_type = 'live_camera'
            else:
                # For pre-recorded, use file path
                input_h = InputHandler(str(source_index))
            
            # Process through HSI pipeline
            result = processor.process(input_h)
            hsi_cube = result['processed_hsi']
            
            # Get middle band for visualization (band index 10 out of 31)
            band_idx = 10 if hsi_cube.shape[2] > 10 else 0
            hsi_vis_band = hsi_cube[:, :, band_idx]
            
            # Normalize HSI band to [0, 255]
            hsi_vis = (hsi_vis_band - hsi_vis_band.min()) / (hsi_vis_band.max() - hsi_vis_band.min() + 1e-8)
            hsi_vis = (hsi_vis * 255).astype(np.uint8)
            
            # small_frame was normalized to [0,1], convert back to uint8
            small_frame_uint8 = (small_frame_norm * 255).astype(np.uint8)
            
            # Convert HSI band to color visualization (apply colormap makes it 3-channel)
            # Ensure hsi_vis is properly sized to 100x100
            hsi_vis_resized = cv2.resize(hsi_vis, (100, 100)) if hsi_vis.shape[0] != 100 or hsi_vis.shape[1] != 100 else hsi_vis
            hsi_vis_bgr = cv2.applyColorMap(hsi_vis_resized, cv2.COLORMAP_JET)
            
            # Combine side-by-side: both should be 100x100x3
            combined = np.hstack([small_frame_uint8, hsi_vis_bgr])
            
            return combined
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        print(f"Error processing frame: {e}")
        # Return error frame - red side, black HSI side
        error_frame = np.zeros((100, 200, 3), dtype=np.uint8)
        error_frame[:, :100] = (0, 0, 255)  # Blue original
        error_frame[:, 100:] = (0, 0, 0)    # Black HSI
        return error_frame

def generate_frames(source_type, source_index):
    """Generate video frames with HSI processing for streaming."""
    camera = None
    
    if source_type == 'live':
        camera = cv2.VideoCapture(int(source_index))
        if not camera.isOpened():
            print(f"Error: Could not open live camera source {source_index}")
            # Return error frames
            error_mjpeg = generate_error_mjpeg()
            yield error_mjpeg
            return
    else:
        # For pre-recorded, open the video file
        camera = cv2.VideoCapture(str(source_index))
        if not camera.isOpened():
            print(f"Error: Could not open pre-recorded source {source_index}")
            # Return error frames
            error_mjpeg = generate_error_mjpeg()
            yield error_mjpeg
            return
    
    try:
        frame_count = 0
        while True:
            success, frame = camera.read()
            if not success:
                # For pre-recorded video, reset to beginning
                if source_type == 'pre-recorded':
                    camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break  # End of live stream
            
            # Process frame through HSI pipeline
            combined = process_frame_to_hsi(frame, source_type, source_index)
            
            # Encode as JPEG for streaming
            (ret, buffer) = cv2.imencode('.jpg', combined)
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    except Exception as e:
        print(f"Error in frame generation: {e}")
    finally:
        if camera is not None:
            camera.release()
        release_resources()

def generate_error_mjpeg():
    """Generate MJPEG with error message frame."""
    error_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(error_frame, "Camera/Source Error", (200, 180), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    (ret, buffer) = cv2.imencode('.jpg', error_frame)
    if ret:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main page with source selection form and video display."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route with source parameters.
    
    Query parameters:
        source: 'live' or 'pre-recorded'
        source_index: camera index (0,1,2) or file path
    """
    source_type = request.args.get('source', 'live')
    source_index = request.args.get('source_index', '0')
    
    return Response(generate_frames(source_type, source_index),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    init_processor()
    print("Starting Web HSI System...")
    print("Access at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)