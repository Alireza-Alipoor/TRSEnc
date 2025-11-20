import json
import shutil
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


class Metadata1Appender:

    def __init__(self, config, file_path: Path):
        self.file_path = file_path
        self.dest_dir = Path(config["encoding"]["destination_directory"])

        if not self.validate_file():
            raise FileNotFoundError(f"Source file {file_path} is invalid")

        self.file_size = self.get_file_size()
        self.file_name = self.get_file_name()
        self.metadata = self.get_metadata()
        self.dest_path = self.dest_dir / self.file_name

    def validate_file(self):
        """Validate that the source file exists and is accessible"""
        if not self.file_path.exists():
            logger.error(f"Source file does not exist: {self.file_path}")
            return False
        if not self.file_path.is_file():
            logger.error(f"Source path is not a file: {self.file_path}")
            return False
        return True

    def get_file_size(self):
        """Get file size with proper error handling"""
        try:
            return self.file_path.stat().st_size
        except OSError as e:
            logger.error(f"Failed to get file size for {self.file_path}: {e}")
            raise

    def get_file_name(self):
        return self.file_path.name

    def get_metadata(self):
        metadata = {
            "name": self.file_name,
            "path": str(self.file_path),
            "size": self.file_size,
        }
        return metadata

    def append_metadata(self):
        """Append metadata to destination file"""
        try:
            with open(self.dest_path, "ab") as f:
                metadata_str = f"Metadata1 for : {json.dumps(self.metadata)}\n"
                f.write(metadata_str.encode("utf-8"))
            logger.debug(f"Metadata appended to {self.dest_path}")
        except IOError as e:
            logger.error(f"Failed to append metadata to {self.dest_path}: {e}")
            raise

    def copy_file(self):
        """Copy file to destination directory"""
        try:
            self.dest_dir.mkdir(exist_ok=True, parents=True)
            shutil.copy(self.file_path, self.dest_path)
            logger.info(f"File copied from {self.file_path} to {self.dest_path}")
        except (shutil.Error, IOError) as e:
            logger.error(f"Failed to copy file to {self.dest_path}: {e}")
            raise

    def run(self):
        """Main execution method with comprehensive error handling"""
        try:
            logger.info(
                f"Starting metadata1 processing for {self.file_path} (size: {self.file_size})"
            )

            self.copy_file()
            logger.info(f"File copied successfully to {self.dest_path}")

            self.append_metadata()
            logger.info("Metadata1 appended successfully")

        except Exception as e:
            logger.error(f"Failed to process file {self.file_path}: {e}")
            raise
        return self.dest_path
