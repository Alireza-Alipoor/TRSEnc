import os
from pathlib import Path

import numpy as np
from reedsolo import RSCodec

from logger import get_logger

logger = get_logger(__name__)


class RSEncoding:
    def __init__(self, config, in_path: Path):
        self.rs_params = config["reed_solomon"]
        self.block_size = self.rs_params["nsize"] - self.rs_params["nsym"]
        self.RS = RSCodec(**self.rs_params)
        self.in_path = in_path
        self.out_path = (
            self.in_path.parent / f"{self.in_path.stem}_encoded{self.in_path.suffix}"
        )
        self.output_size = None

    def transpose(self):

        try:
            file_size = os.path.getsize(self.in_path)
            if self.output_size is None:
                self.output_size = os.path.getsize(self.out_path)
            # Get matrix shape from config (must match total bytes)
            cols = self.rs_params["nsize"]
            rows = self.output_size // cols

            if rows * cols != file_size:
                raise ValueError(
                    f"File size ({file_size}) doesn't match rows*cols ({rows*cols})"
                )

            out_path = (
                self.in_path.parent / f"{self.in_path.stem}_T{self.in_path.suffix}"
            )

            # Create memory maps for input and output
            src = np.memmap(self.in_path, dtype=np.uint8, mode="r", shape=(rows, cols))
            dst = np.memmap(out_path, dtype=np.uint8, mode="w+", shape=(cols, rows))

            # Transpose in manageable blocks
            block = 1024  # tune for your memory (e.g., 4096 for faster I/O)
            for i in range(0, rows, block):
                for j in range(0, cols, block):
                    sub = src[i : i + block, j : j + block]
                    dst[j : j + block, i : i + block] = sub.T

            dst.flush()
            logger.info(f"Transposed file written to {out_path}")
            logger.info(f"Input: {rows}*{cols}, Output: {cols}*{rows}")

            self.out_path = out_path
            return out_path

        except Exception as e:
            logger.error(f"Transpose failed: {e}")
            return None

    def encode(self):
        with open(self.in_path, "rb") as fin, open(self.out_path, "wb") as fout:
            try:
                with open(self.in_path, "rb") as fin, open(self.out_path, "wb") as fout:
                    while True:
                        block = fin.read(self.block_size)
                        if not block:
                            break

                        # Pad if necessary
                        if len(block) < self.block_size:
                            padding = b"\x00" * (self.block_size - len(block))
                            block += padding
                            logger.debug(f"Padded block with {len(padding)} zeros")

                        encoded_block = self.RS.encode(block)
                        fout.write(encoded_block)
                self.output_size = self.out_path.stat().st_size
                logger.info(f"Successfully encoded {self.in_path} -> {self.out_path}")
                logger.info(f"Output size: {self.output_size} bytes")

            except Exception as e:
                logger.error(f"Encoding failed: {str(e)}")
                # Clean up partial output on failure
                if self.out_path.exists():
                    os.remove(self.out_path)
                return False

    def run(self):
        if not self.encode():
            logger.error("Encode failed — skipping transpose.")
            return False
        return self.transpose()
