import os
import shutil
import tempfile
from git import Repo, GitCommandError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GitHubLoader:
    """
    Clones a public GitHub repository into a temporary directory.
    Returns the local path for downstream parsing.
    """

    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir

    def clone(self, github_url: str, job_id: str) -> str:
        """
        Clone a GitHub repo URL into a job-specific directory.

        Args:
            github_url: Full HTTPS GitHub URL e.g. https://github.com/user/repo
            job_id:     UUID string used to namespace the clone directory

        Returns:
            Absolute path to the cloned repo directory

        Raises:
            ValueError: If URL is not a valid GitHub URL
            RuntimeError: If clone fails (private repo, network issue, etc.)
        """
        if not github_url.startswith("https://github.com/"):
            raise ValueError(f"Invalid GitHub URL: {github_url}")

        # Ensure the URL ends without .git so we can add it cleanly
        clone_url = github_url.rstrip("/")
        if not clone_url.endswith(".git"):
            clone_url += ".git"

        dest_dir = os.path.join(self.upload_dir, f"repo_{job_id}")

        # Clean up any previous attempt for this job
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

        os.makedirs(dest_dir, exist_ok=True)

        logger.info("Cloning repository", url=github_url, dest=dest_dir)

        try:
            Repo.clone_from(
                clone_url,
                dest_dir,
                depth=1,           # Shallow clone — only latest commit, much faster
                single_branch=True,
            )
            logger.info("Clone successful", dest=dest_dir)
            return dest_dir

        except GitCommandError as e:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise RuntimeError(
                f"Failed to clone {github_url}. "
                f"Check that it is a public repository. Error: {str(e)}"
            )

    def cleanup(self, job_id: str):
        """Remove cloned repo after processing to free disk space."""
        dest_dir = os.path.join(self.upload_dir, f"repo_{job_id}")
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
            logger.info("Cleaned up repo directory", job_id=job_id)