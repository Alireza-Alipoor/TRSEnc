import mmap
from pathlib import Path

from src.logging.logger import get_logger

logger = get_logger(__name__)


class PaddingAdder:
    def __init__(self, config, in_path: Path):
        self.in_path = in_path
        self.input_size = in_path.stat().st_size
        self.padding_size = min(config["encoding"]["padding_size"], self.input_size)

    def add_padding(self):
        try:
            logger.info(
                f"Adding first {self.padding_size / (1024**3):.2f} GB to beginning of file: {self.in_path}"
            )

            new_size = self.input_size + self.padding_size
            temp_path = self.in_path.with_suffix(".tmp")
            chunk_size = 128 * 1024 * 1024  # 128 MB chunks

            # Create temporary file
            with open(temp_path, "wb") as temp_file:
                temp_file.truncate(new_size)

            with (
                open(self.in_path, "rb") as original_file,
                open(temp_path, "r+b") as temp_file,
            ):

                # Write padding (first part of original file)
                with mmap.mmap(
                    original_file.fileno(), 0, access=mmap.ACCESS_READ
                ) as original_mmap:
                    with mmap.mmap(
                        temp_file.fileno(), 0, access=mmap.ACCESS_WRITE
                    ) as temp_mmap:

                        # Copy padding in chunks
                        for offset in range(0, self.padding_size, chunk_size):
                            chunk_end = min(offset + chunk_size, self.padding_size)
                            temp_mmap[offset:chunk_end] = original_mmap[
                                offset:chunk_end
                            ]

                        # Copy original file content after padding
                        for offset in range(0, self.input_size, chunk_size):
                            chunk_end = min(offset + chunk_size, self.input_size)
                            temp_mmap[
                                self.padding_size
                                + offset : self.padding_size
                                + chunk_end
                            ] = original_mmap[offset:chunk_end]

            temp_path.replace(self.in_path)
            logger.info(
                f"Successfully added padding. New file size: {self.in_path.stat().st_size / (1024**3):.2f} GB"
            )

        except Exception as e:
            logger.error(f"Error adding padding to file {self.in_path}: {str(e)}")
            raise

    def run(self):
        self.add_padding()
        return self.in_path
