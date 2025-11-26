import ast
import json
from pathlib import Path

from src.logging.logger import get_logger

logger = get_logger(__name__)


class Metadata2Adder:
    def __init__(self, config, file_path: Path):
        """Initialize the Metadata2Adder with configuration and file path."""
        self.config = config
        self.file_path = Path(file_path)

        if not self.file_path.exists():
            raise FileNotFoundError(f"{self.file_path} does not exist")

        self.encoding_cfg = config["encoding"]
        self.rs_params = self.encoding_cfg["reed_solomon"]
        self.meta2_cfg = self.encoding_cfg["metadata2"]

        self.file_size = self.file_path.stat().st_size
        self.padding_config = int(self.encoding_cfg.get("padding_size", 0))

        self.delimiter = self._parse_delimiter(self.meta2_cfg.get("delimiter", b""))

        self.padding_applied = self._calculate_applied_padding()

        self.encoded_suffix = self.encoding_cfg.get("encoded_file_suffix", "")

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

    def _calculate_applied_padding(self):
        """Calculate how much padding has been applied to the file."""
        s = self.file_size
        p = self.padding_config

        if p <= 0:
            logger.warning("padding_size is not positive; assuming no padding")
            return 0

        # small file: duplicated → padding == original size
        if s < 2 * p:
            if s % 2 != 0:
                logger.warning(
                    f"Padded file size {s} is not even; "
                    "cannot split exactly in half, using floor division."
                )
            padding = s // 2
        else:
            # big file: padded with exactly padding_size
            padding = p

        logger.info(
            f"Detected padding_applied={padding} bytes "
            f"(file_size={s}, padding_config={p})"
        )
        return padding

    def _build_metadata_bytes(self):
        """Build the metadata bytes to be appended to the file."""
        meta = {
            "size_before_padding": self.file_size - self.padding_applied,
            "padding": self.padding_applied,
            "rs": dict(self.rs_params),
        }

        json_bytes = json.dumps(meta, separators=(",", ":")).encode("utf-8")
        length = len(json_bytes)
        length_bytes = length.to_bytes(4, "big")

        return self.delimiter + length_bytes + json_bytes

    def add_metadata(self):
        logger.info(f"Appending metadata2 to {self.file_path} (size={self.file_size})")

        metadata_record = self._build_metadata_bytes()

        try:
            # Open the file in append mode and write the metadata
            with open(self.file_path, "ab") as f:
                f.write(metadata_record)
                logger.info(f"Successfully appended metadata2 to {self.file_path}")
        except IOError as e:
            logger.error(f"Failed to append metadata2 to {self.file_path}: {e}")
            raise

        return self.file_path

    def _ensure_encoded_suffix(self):
        """Ensure the file has the correct encoded suffix."""
        if self.encoded_suffix and str(self.file_path).endswith(self.encoded_suffix):
            return self.file_path

        if not self.encoded_suffix:
            return self.file_path

        new_path = self.file_path.with_name(self.file_path.name + self.encoded_suffix)
        self.file_path.rename(new_path)
        self.file_path = new_path
        return new_path

    def run(self):
        """Run the process of appending metadata and ensuring the suffix."""
        self.add_metadata()
        final_path = self._ensure_encoded_suffix()
        return final_path
