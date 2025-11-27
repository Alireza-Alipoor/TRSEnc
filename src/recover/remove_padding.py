import mmap
import os
from pathlib import Path

from src.logging.logger import get_logger

logger = get_logger(__name__)


class PaddingRemover:
    def __init__(self, padding_size: int, file_path: Path):
        self.file_path = file_path
        self.padding_size = padding_size
        self.input_size = self.file_path.stat().st_size

    def remove_padding(self):
        try:
            logger.info(
                f"Removing first {self.padding_size / (1024**3):.2f} GB of padding from file: {self.file_path}"
            )

            new_size = self.input_size - self.padding_size

            temp_path = self.file_path.with_suffix(".tmp")
            removed_padding_path = self.file_path.with_suffix(
                ".removed_padding"
            )  # File to store removed padding

            with open(removed_padding_path, "wb") as padding_file:
                with open(self.file_path, "rb") as original_file:
                    padding_file.write(original_file.read(self.padding_size))

            with open(temp_path, "wb") as temp_file:
                temp_file.truncate(new_size)

            with (
                open(self.file_path, "rb") as original_file,
                open(temp_path, "r+b") as temp_file,
            ):
                with mmap.mmap(
                    original_file.fileno(), 0, access=mmap.ACCESS_READ
                ) as original_mmap:
                    with mmap.mmap(
                        temp_file.fileno(), 0, access=mmap.ACCESS_WRITE
                    ) as temp_mmap:
                        temp_mmap[:new_size] = original_mmap[self.padding_size :]

            os.replace(temp_path, self.file_path)
            logger.info(
                f"Successfully removed padding. New file size: {self.file_path.stat().st_size / (1024**3):.2f} GB"
            )
            logger.info(f"Removed padding saved to: {removed_padding_path}")

            return removed_padding_path, self.file_path

        except Exception as e:
            logger.error(f"Error removing padding from file {self.file_path}: {str(e)}")
            raise

    def run(self):
        """Run the padding removal process and save the removed padding."""
        return self.remove_padding()
