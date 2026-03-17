#!/usr/bin/env python3
from flask import Flask, Response, render_template_string, jsonify
from picamera2 import Picamera2
import cv2
from datetime import datetime
from pathlib import Path
import threading
import calibration_results as cr

app = Flask(__name__)

# Initialize camera
FRAME_SIZE = (640, 480)

picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": FRAME_SIZE})
picam2.configure(config)
picam2.start()

latest_frame = None
frame_lock = threading.Lock()
new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
    cr.camera_matrix,
    cr.distortion_coefficients,
    FRAME_SIZE,
    1,
    FRAME_SIZE
)
map1, map2 = cv2.initUndistortRectifyMap(
    cr.camera_matrix,
    cr.distortion_coefficients,
    None,
    new_camera_matrix,
    FRAME_SIZE,
    cv2.CV_16SC2
)

PHOTO_DIR = Path("captured_photos")
PHOTO_DIR.mkdir(exist_ok=True)

# Simple HTML page
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi Camera Stream</title>
</head>
<body style="background: #111; color: white; text-align: center; font-family: Arial, sans-serif;">
    <h1>Raspberry Pi Camera Stream</h1>

    <div style="margin-bottom: 20px;">
        <button
            id="take-photo-btn"
            style="padding: 12px 24px; font-size: 18px; cursor: pointer;"
        >
            Take Photo
        </button>
    </div>

    <p id="status-message" style="min-height: 24px; color: #7CFC98;"></p>

    <img src="/video_feed" style="width: 80%; border: 3px solid white;">

    <script>
        const takePhotoButton = document.getElementById("take-photo-btn");
        const statusMessage = document.getElementById("status-message");

        takePhotoButton.addEventListener("click", async () => {
            takePhotoButton.disabled = true;
            statusMessage.textContent = "Taking photo...";

            try {
                const response = await fetch("/take_photo", {
                    method: "POST"
                });

                const data = await response.json();

                if (response.ok) {
                    statusMessage.textContent = data.message;
                } else {
                    statusMessage.textContent = data.message || "Failed to take photo.";
                }
            } catch (error) {
                statusMessage.textContent = "Error taking photo.";
            } finally {
                takePhotoButton.disabled = false;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

def undistort_frame(frame):
    undistorted = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR)
    x, y, w, h = roi
    return undistorted[y:y+h, x:x+w]

def capture_frames():
    global latest_frame

    while True:
        frame = picam2.capture_array()
        frame = undistort_frame(frame)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        with frame_lock:
            latest_frame = frame_rgb

def generate_frames():
    while True:

        with frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()

        if frame is None:
            time.sleep(0.01)
            continue

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        jpg = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n'
        )

@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/take_photo', methods=['POST'])
def take_photo():
    try:
        frame = picam2.capture_array()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = PHOTO_DIR / f"photo_{timestamp}.jpg"

        cv2.imwrite(str(photo_path), frame)
        print(f"[INFO] Photo saved to {photo_path}")

        return jsonify({
            "success": True,
            "message": f"Photo saved: {photo_path.name}"
        })
    except Exception as error:
        return jsonify({
            "success": False,
            "message": f"Failed to save photo: {error}"
        }), 500

if __name__ == '__main__':
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    capture_thread.start()
    # host='0.0.0.0' makes it accessible only within the local network
    app.run(host='0.0.0.0', port=5000, debug=False)