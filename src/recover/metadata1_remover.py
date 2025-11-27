import json
import mmap
from pathlib import Path

from src.logging.logger import get_logger

logger = get_logger(__name__)


class Metadata1Remover:
    """
    Remove the 'Metadata1 for : {...}' footer appended by Metadata1Appender.

    Responsibilities:
    - Find and parse Metadata1 at the end of the file
    - Truncate the file back to the original size
    - Print/log the original path (but DO NOT move the file)
    """

    MARKER = b"Metadata1 for : "

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.metadata: dict = self.find_metadata()

        if not self.file_path.exists():
            raise FileNotFoundError(f"{self.file_path} does not exist")

    def find_metadata(self) -> dict:
        """
        Search from the end of the file for the MARKER and parse the JSON
        that follows it. Stores result in self.metadata and returns it.
        """
        with open(self.file_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                pos = mm.rfind(self.MARKER)
                if pos == -1:
                    raise ValueError("Metadata1 marker not found in file")

                start = pos + len(self.MARKER)

                end = mm.find(b"\n", start)
                if end == -1:
                    end = len(mm)

                json_bytes = mm[start:end]

                try:
                    meta = json.loads(json_bytes.decode("utf-8"))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse Metadata1 JSON: {e}") from e

        logger.info(f"Recovered Metadata1: {meta}")
        return meta

    def remove_redundancy(self):
        """
        - Use self.metadata to truncate the file
        - Print original path (if available)
        - Rename the file to its original name (in the current directory)
        """

        original_size = int(self.metadata["size"])
        original_path = self.metadata.get("path")
        original_name = self.metadata.get("name")

        # 1) Truncate to original size
        with open(self.file_path, "r+b") as f:
            f.truncate(original_size)

        logger.info(
            f"Truncated {self.file_path} to original size {original_size} bytes"
        )

        # 2) Print/log original path if present
        if original_path:
            logger.info(f"Original path from Metadata1: {original_path}")
            print(f"Original path (from Metadata1): {original_path}")

        # 3) Decide the original filename (no directory)
        original_filename = None
        if original_path:
            original_filename = Path(original_path).name
        elif original_name:
            original_filename = Path(original_name).name

        # 4) Rename current file to that original filename in the same directory
        if original_filename:
            dest_path = self.file_path.with_name(original_filename)

            if dest_path.exists():
                logger.warning(
                    f"{dest_path} already exists and will be overwritten by the "
                    "recovered file."
                )
                dest_path.unlink()

            self.file_path.rename(dest_path)
            self.file_path = dest_path  # keep attribute in sync

            logger.info(f"Renamed recovered file to {dest_path}")
            print(f"Renamed recovered file to {dest_path}")

    def run(self) -> Path:
        """
        Example call pattern:
            remover = Metadata1Remover(decoded_file)
            remover.run()
        """
        self.find_metadata()
        self.remove_redundancy()
        return self.file_path
