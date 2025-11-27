import ast
import json
import mmap
from pathlib import Path


class Metadata2Remover:
    def __init__(self, config, file_path: Path):
        self.config = config
        self.file_path = Path(file_path)
        self.delimiter = self._parse_delimiter(
            config["encoding"]["metadata2"]["delimiter"]
        )

    def _parse_delimiter(self, value):
        """Parse the delimiter value for metadata."""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)

        if isinstance(value, str):
            text = value.strip()
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, (bytes, bytearray)):
                    return bytes(parsed)
            except Exception:
                pass
            return text.encode("utf-8")

        raise TypeError(f"Unsupported delimiter type: {type(value)}")

    def extract_metadata(self, mmapped_file, first_delim_pos):
        """Extract and return the metadata after the delimiter."""
        # After the delimiter, the next 4 bytes represent the length of the metadata
        length_bytes = mmapped_file[
            first_delim_pos
            + len(self.delimiter) : first_delim_pos
            + len(self.delimiter)
            + 4
        ]
        length = int.from_bytes(length_bytes, byteorder="big")

        # Extract the metadata based on the length
        metadata_bytes = mmapped_file[
            first_delim_pos
            + len(self.delimiter)
            + 4 : first_delim_pos
            + len(self.delimiter)
            + 4
            + length
        ]
        metadata = json.loads(metadata_bytes.decode("utf-8"))

        return metadata

    def remove_metadata2(self):
        """Remove metadata2 and any bytes after the delimiter."""
        with open(self.file_path, "r+b") as file:
            mmapped_file = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)

            # Search backward for the delimiter
            first_delim_pos = mmapped_file.rfind(self.delimiter)
            if first_delim_pos == -1:
                raise ValueError("Delimiter not found in the file.")

            metadata = self.extract_metadata(mmapped_file, first_delim_pos)

            mmapped_file.close()

            with open(self.file_path, "r+b") as file:
                file.truncate(first_delim_pos)
        return metadata

    def run(self):
        """Execute the metadata removal process and return the metadata."""
        metadata = self.remove_metadata2()
        return metadata, self.file_path
