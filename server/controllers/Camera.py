from pathlib import Path
import subprocess

class Camera:

    def _ensure_jpg_filename(self, filename: str) -> str:
        """
        Ensure the filename is valid and ends with .jpg
        """
        if not filename or not filename.strip():
            raise ValueError("filename must be a non-empty string")

        filename = filename.strip()

        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            filename += ".jpg"

        return filename


    def _create_local_save_folder(self, desktop_folder_name: str) -> Path:
        """
        Create/use a folder on the Raspberry Pi Desktop.
        """
        desktop_path = Path.home() / "Desktop"
        save_folder = desktop_path / desktop_folder_name
        save_folder.mkdir(parents=True, exist_ok=True)
        return save_folder


    def _ensure_remote_dir_exists(self, host_user: str, host_ip: str, remote_dir: str) -> None:
        """
        Ensure the destination directory exists on the host computer.
        """
        subprocess.run(
            [
                "ssh",
                f"{host_user}@{host_ip}",
                f"mkdir -p '{remote_dir}'"
            ],
            check=True
        )


    def _capture_image(self, camera, local_image_path: Path) -> None:
        """
        Capture one image using an already-running Picamera2 object.
        """
        camera.capture_file(str(local_image_path))


    def _upload_image(self, local_image_path: Path, host_user: str, host_ip: str, remote_dir: str) -> None:
        """
        Upload one image to the host computer via scp.
        """
        remote_target = f"{host_user}@{host_ip}:{remote_dir}"
        subprocess.run(
            ["scp", str(local_image_path), remote_target],
            check=True
        )


    def capture_and_save_image(
        self,
        camera,
        filename,
        host_user,
        host_ip,
        remote_dir,
        desktop_folder_name="drone_images"
    ):
        """
        Capture one image with an already-initialized Raspberry Pi camera
        and upload it to a host computer via scp.

        Parameters
        ----------
        camera : Picamera2
            An already-initialized and already-running camera object.
        filename : str
            Image filename, e.g. "image_001.jpg".
        host_user : str
            Username on the host computer.
        host_ip : str
            IP address of the host computer.
        remote_dir : str
            Destination directory on the host computer.
        desktop_folder_name : str, optional
            Name of the folder to create/use on the Desktop.

        Returns
        -------
        tuple[str, str]
            (local_image_path, remote_image_path)
        """

        filename = self._ensure_jpg_filename(filename)
        save_folder = self._create_local_save_folder(desktop_folder_name)

        local_image_path = save_folder / filename

        try:
            # Step 1: capture image on Raspberry Pi
            self._capture_image(camera, local_image_path)

            # Step 2: make sure host destination folder exists
            self._ensure_remote_dir_exists(host_user, host_ip, remote_dir)

            # Step 3: upload image to host computer
            self._upload_image(local_image_path, host_user, host_ip, remote_dir)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"File transfer command failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Capture/upload failed: {e}") from e

        remote_image_path = f"{remote_dir.rstrip('/')}/{filename}"

        return str(local_image_path), remote_image_path