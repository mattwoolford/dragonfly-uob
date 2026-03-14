from pathlib import Path
import subprocess


def capture_and_upload_image(
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

    # Create/use a folder on the Desktop
    desktop_path = Path.home() / "Desktop"
    save_folder = desktop_path / desktop_folder_name
    save_folder.mkdir(parents=True, exist_ok=True)

    # Full local path
    local_image_path = save_folder / filename

    # Capture one image to local file
    camera.capture_file(str(local_image_path))

    # Upload image to host computer
    remote_target = f"{host_user}@{host_ip}:{remote_dir}"
    subprocess.run(
        ["scp", str(local_image_path), remote_target],
        check=True
    )

    # Final remote path string for reference
    remote_image_path = f"{remote_dir.rstrip('/')}/{filename}"

    return str(local_image_path), remote_image_path