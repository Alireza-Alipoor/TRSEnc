from pathlib import Path

from logger import get_logger

logger = get_logger(__name__)


class Metadata2Adder:

    def __init__(self, file_path: Path, config):
        self.in_path = file_path
        self.rs_configs = config["encoding"]["reed_solomon"]
        self.padding_size = config["encoding"]["pading_size"]
        self.delimiter = config["encoding"]["delimiter"]
        self.encoded_file_suffix = config["encoding"]["encoded_file_suffix"]

        self.out_path = self.in_path.with_suffix(
            self.in_path.suffix + self.encoded_file_suffix
        )

    def _calculate_dynamic_gaps(self, file_size: int) -> dict:

        base_gaps = {
            "d1": self.rs_configs["d1_gap"],  # مثلاً 64K
            "d2": self.rs_configs["d2_gap"],  # مثلاً 128K
            "d3": self.rs_configs["d3_gap"],  # مثلاً 1G
        }

        valid = {}
        for k, gap in base_gaps.items():
            if file_size > gap:
                valid[k] = gap
            else:
                logger.warning(f"gap {k} ({gap}) removed — file too small.")

        return valid

    def add_metadata(self):
        data = self.in_path.read_bytes()
        file_size = len(data)

        logger.info(f"Input size: {file_size:,} bytes")

        gaps = self._calculate_dynamic_gaps(file_size)
        if not gaps:
            logger.error("No valid delimiter gaps found.")
            raise ValueError("file too small for metadata insertion.")

        chunks = []
        cursor = 0

        for name, gap in gaps.items():
            end = cursor + gap
            if end > file_size:
                end = file_size

            chunk = data[cursor:end]
            chunks.append(chunk)
            chunks.append(self.delimiter)

            logger.debug(f"Inserted delimiter after {name} gap ({gap} bytes).")

            cursor = end

        if cursor < file_size:
            chunks.append(data[cursor:])

        output = b"".join(chunks)

        self.out_path.write_bytes(output)
        logger.info(f"New file written: {self.out_path}")

    def remove_old_file(self):
        try:
            self.in_path.unlink()
            logger.info(f"Removed old file: {self.in_path}")
        except Exception as e:
            logger.error(f"Could not remove old file: {e}")

    def run(self):
        logger.info("Metadata2Adder started.")
        self.add_metadata()
        self.remove_old_file()
        logger.info("Metadata2Adder finished.")
