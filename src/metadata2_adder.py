import ast
import json
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


class Metadata2Adder:
    def __init__(self, config, file_path: Path):
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

        self.gaps = {
            "d1": int(self.meta2_cfg.get("d1_gap", 0)),
            "d2": int(self.meta2_cfg.get("d2_gap", 0)),
            "d3": int(self.meta2_cfg.get("d3_gap", 0)),
        }

        self.padding_applied = self._calculate_applied_padding()
        self.size_before_padding = self.file_size - self.padding_applied

    def _parse_delimiter(self, value):
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

    def _build_metadata_bytes(self, label):
        meta = {
            "label": label,
            "gap_from_eof": self.gaps[label],
            "file_size": self.file_size,
            "size_before_padding": self.size_before_padding,
            "padding": {
                "configured_size": self.padding_config,
                "applied_size": self.padding_applied,
            },
            "reed_solomon": dict(self.rs_params),
        }

        json_bytes = json.dumps(meta, separators=(",", ":")).encode("utf-8")
        length = len(json_bytes)
        length_bytes = length.to_bytes(4, "big")  # 4-byte big-endian length

        # final layout: [delimiter][length][json]
        return self.delimiter + length_bytes + json_bytes

    def _calculate_positions(self):
        positions = {}
        size = self.file_size

        for label, gap in self.gaps.items():
            start = size - gap
            if start < 0:
                raise ValueError(
                    f"Gap for {label} ({gap}) is larger than file size ({size})"
                )
            positions[label] = start

        return positions

    def add_metadata(self):
        logger.info(
            f"Adding metadata2 to {self.file_path} "
            f"(size={self.file_size}, padding_applied={self.padding_applied})"
        )

        positions = self._calculate_positions()

        for label, offset in sorted(positions.items(), key=lambda kv: kv[1]):
            record = self._build_metadata_bytes(label)

            logger.info(
                f"Writing {label} metadata at offset {offset} "
                f"(gap_from_eof={self.gaps[label]}, record_len={len(record)})"
            )

            with open(self.file_path, "r+b") as f:
                f.seek(offset)
                f.write(record)

        logger.info("Finished writing metadata2 records")
        return self.file_path

    def run(self):
        return self.add_metadata()
