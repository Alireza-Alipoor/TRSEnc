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

    def extract_metadata(self, mmapped_file, second_delim_pos, first_delim_pos):
        """Extract and return the metadata between the delimiters."""
        metadata_bytes = mmapped_file[
            first_delim_pos + len(self.delimiter) : second_delim_pos
        ]

        try:
            length_bytes = metadata_bytes[:4]
            length = int.from_bytes(length_bytes, byteorder="big")

            metadata_json = metadata_bytes[4 : 4 + length]
            metadata = json.loads(metadata_json.decode("utf-8"))
            return metadata
        except Exception as e:
            raise ValueError(f"Failed to extract and parse metadata: {e}")

    def remove_metadata2(self):
        """Remove metadata2 and any bytes after the second delimiter."""
        with open(self.file_path, "r+b") as file:
            mmapped_file = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)

            second_delim_pos = mmapped_file.rfind(self.delimiter)
            if second_delim_pos == -1:
                raise ValueError("Second delimiter not found in the file.")

            first_delim_pos = mmapped_file.rfind(self.delimiter, 0, second_delim_pos)
            if first_delim_pos == -1:
                raise ValueError("First delimiter not found in the file.")

            metadata = self.extract_metadata(
                mmapped_file, second_delim_pos, first_delim_pos
            )

            mmapped_file.close()

            with open(self.file_path, "r+b") as file:
                file.truncate(first_delim_pos)

        print(
            f"Metadata2 removed. The file size is now {Path(self.file_path).stat().st_size} bytes."
        )
        return metadata

    def run(self):
        """Execute the metadata removal process and return the metadata."""
        metadata = self.remove_metadata2()
        return metadata, self.file_path


if __name__ == "__main__":
    from src.encoding.config_reader import read_config

    path = Path(input())
    m = Metadata2Remover(read_config("configs/configs.yaml"), path)
    print(m.run())
