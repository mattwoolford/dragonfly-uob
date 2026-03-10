from pathlib import Path
import subprocess


def capture_and_upload_image(camera, local_image_path, host_user, host_ip, remote_path):
    """
    Capture one image with an already-initialized camera and upload it to a host computer.

    Args:
        camera: An already-initialized camera object (e.g. Picamera2 instance).
        local_image_path (str): Local path/filename to save the captured image.
        host_user (str): Username on the host computer.
        host_ip (str): IP address of the host computer.
        remote_path (str): Destination path on the host computer.

    Returns:
        str: The local image path if capture and upload succeed.

    Raises:
        RuntimeError: If image capture or upload fails.
    """
    local_image_path = str(Path(local_image_path))

    # 1. Capture one image
    try:
        camera.capture_file(local_image_path)
    except Exception as e:
        raise RuntimeError(f"Image capture failed: {e}")

    # 2. Upload image to host computer
    try:
        subprocess.run(
            [
                "scp",
                local_image_path,
                f"{host_user}@{host_ip}:{remote_path}"
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Image upload failed: {e}")

    return local_image_path