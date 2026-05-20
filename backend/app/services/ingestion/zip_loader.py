import os
import shutil
import zipfile
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ZipLoader:
    """
    Extracts a ZIP file into a job-specific directory.
    Handles nested single-folder ZIPs (common with GitHub download ZIPs).
    """

    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir

    def extract(self, zip_path: str, job_id: str) -> str:
        """
        Extract a ZIP archive into a clean directory.

        Args:
            zip_path: Absolute path to the .zip file on disk
            job_id:   UUID string for directory namespacing

        Returns:
            Absolute path to the extracted directory

        Raises:
            FileNotFoundError: ZIP file doesn't exist
            RuntimeError: ZIP is invalid / corrupted
        """
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError(f"File is not a valid ZIP archive: {zip_path}")

        dest_dir = os.path.join(self.upload_dir, f"zip_{job_id}")

        # Clean up any previous attempt
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        os.makedirs(dest_dir, exist_ok=True)

        logger.info("Extracting ZIP", zip_path=zip_path, dest=dest_dir)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Security check — prevent zip slip attacks
                for member in zf.namelist():
                    member_path = os.path.realpath(os.path.join(dest_dir, member))
                    if not member_path.startswith(os.path.realpath(dest_dir)):
                        raise RuntimeError(f"Zip slip detected in member: {member}")
                zf.extractall(dest_dir)

        except zipfile.BadZipFile as e:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise RuntimeError(f"Corrupted ZIP file: {str(e)}")

        # GitHub ZIPs often extract into a single top-level subfolder
        # e.g. repo-main/ — we unwrap that for cleaner paths
        entries = os.listdir(dest_dir)
        if len(entries) == 1:
            single = os.path.join(dest_dir, entries[0])
            if os.path.isdir(single):
                logger.info("Unwrapping single top-level folder", folder=entries[0])
                return single

        logger.info("ZIP extracted", dest=dest_dir)
        return dest_dir

    def cleanup(self, job_id: str):
        """Remove extracted directory after processing."""
        for prefix in ("zip_", "repo_"):
            target = os.path.join(self.upload_dir, f"{prefix}{job_id}")
            if os.path.exists(target):
                shutil.rmtree(target)
                logger.info("Cleaned up directory", job_id=job_id, prefix=prefix)