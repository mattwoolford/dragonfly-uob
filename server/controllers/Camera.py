import time
from pathlib import Path
import subprocess

class Camera:

    @staticmethod
    def _enforce_jpg_file_ext(self, filename: str) -> str:
        """
        Ensure the filename is valid and ends with .jpg
        """
        if not filename or not filename.strip():
            raise ValueError("filename must be a non-empty string")

        filename = filename.strip()

        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            filename += ".jpg"

        return filename

    @staticmethod
    def _create_local_save_folder(self, desktop_folder_name: str) -> Path:
        """
        Create/use a folder on the Raspberry Pi Desktop.
        """
        desktop_path = Path.home() / "Desktop"
        save_folder = desktop_path / desktop_folder_name
        save_folder.mkdir(parents=True, exist_ok=True)
        return save_folder

    @staticmethod
    def _capture_image(self, camera, local_image_path: Path) -> None:
        """
        Capture one image using an already-running Picamera2 object.
        """
        camera.capture_file(str(local_image_path))

    def capture_and_save_image(
        self,
        camera,
        filename,
        save_dir_path
    ):
        """
        Capture one image with an already-initialized Raspberry Pi camera
        and upload it to a host computer via scp.

        Parameters
        ----------
        camera : Picamera2
            An already-initialized and already-running camera object.
        filename : str
            Image filename, e.g. "image_001.jpg"
        save_dir_path : str
            The path to the directory to save the image

        Returns
        -------
        tuple[str, str]
            (local_image_path, remote_image_path)
        """

        filename = self._enforce_jpg_file_ext(f"img_{int(time.time())}.jpg")
        save_dir_path = self._create_local_save_folder(save_dir_path)

        base_dir = Path(__file__).resolve().parent
        local_image_path = f"{base_dir}/{save_dir_path}/{filename}"

        try:
            # Step 1: capture image on Raspberry Pi
            self._capture_image(camera, local_image_path)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"File transfer command failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Capture/upload failed: {e}") from e

        remote_image_path = f"{save_dir_path.rstrip('/')}/{filename}"

        return str(local_image_path), remote_image_path