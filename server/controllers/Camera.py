import time
from pathlib import Path


class Camera:
    @staticmethod
    def _enforce_jpg_file_ext(filename: str) -> str:
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
    def _create_local_save_folder(save_dir_path: str) -> Path:
        """
        Create/use a folder on the Raspberry Pi Desktop.

        If save_dir_path is just a folder name, it will be created under Desktop.
        If it is an absolute path, use it directly.
        """
        if not save_dir_path or not str(save_dir_path).strip():
            raise ValueError("save_dir_path must be a non-empty string")

        save_dir_path = str(save_dir_path).strip()
        save_path = Path(save_dir_path)

        if not save_path.is_absolute():
            save_path = Path.home() / "Desktop" / save_dir_path

        save_path.mkdir(parents=True, exist_ok=True)
        return save_path

    @staticmethod
    def _capture_image(camera, local_image_path: Path) -> None:
        """
        Capture one image using an already-running camera object.
        """
        if camera is None:
            raise ValueError("camera must not be None")

        camera.capture_file(str(local_image_path))

    def capture_and_save_image(
        self,
        camera,
        save_dir_path,
        filename=None
    ):
        """
        Capture one image with an already-initialized camera
        and save it locally.

        Parameters
        ----------
        camera
            An already-initialized and already-running camera object.
        save_dir_path : str
            Folder name or directory path used to save the image.
        filename : str | None
            Optional image filename. If None, generate one automatically.

        Returns
        -------
        tuple[str, str]
            (local_image_path, remote_image_path)

        Notes
        -----
        remote_image_path is kept only for compatibility with existing code.
        In this version, no actual remote upload is performed.
        """
        if filename is None:
            filename = f"img_{int(time.time())}.jpg"

        filename = self._enforce_jpg_file_ext(filename)
        save_folder = self._create_local_save_folder(save_dir_path)

        local_image_path = save_folder / filename

        try:
            self._capture_image(camera, local_image_path)
        except Exception as e:
            raise RuntimeError(f"Capture failed: {e}") from e

        remote_image_path = str(save_folder / filename)

        return str(local_image_path), remote_image_path