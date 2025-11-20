import os
from pathlib import Path

import numpy as np
from reedsolo import RSCodec

from .logger import get_logger

logger = get_logger(__name__)


class RSEncoding:
    def __init__(self, config, in_path: Path):
        self.rs_params = config["encoding"]["reed_solomon"]
        self.block_size = self.rs_params["nsize"] - self.rs_params["nsym"]
        self.RS = RSCodec(**self.rs_params)
        self.in_path = in_path
        self.out_path = (
            self.in_path.parent / f"{self.in_path.stem}_encoded{self.in_path.suffix}"
        )
        self.output_size = None

    def transpose(self):
        try:
            file_size = self.in_path.stat().st_size
            if self.output_size is None:
                self.output_size = self.out_path.stat().st_size

            cols = self.rs_params["nsize"]
            rows = self.output_size // cols

            if rows * cols != file_size:
                raise ValueError(
                    f"File size ({file_size}) doesn't match rows*cols ({rows*cols})"
                )

            out_path = (
                self.in_path.parent / f"{self.in_path.stem}_T{self.in_path.suffix}"
            )

            src = np.memmap(self.in_path, dtype=np.uint8, mode="r", shape=(rows, cols))
            dst = np.memmap(out_path, dtype=np.uint8, mode="w+", shape=(cols, rows))

            block = 1024
            for i in range(0, rows, block):
                for j in range(0, cols, block):
                    sub = src[i : i + block, j : j + block]
                    dst[j : j + block, i : i + block] = sub.T

            dst.flush()
            logger.info(f"Transposed file written to {out_path}")
            logger.info(f"Input: {rows}*{cols}, Output: {cols}*{rows}")

            try:
                self.in_path.unlink()
                logger.info(f"{self.in_path} removed")
            except Exception as e:
                logger.error(f"deleting {self.in_path} failed: {e}")

            self.out_path = out_path
            return out_path

        except Exception as e:
            logger.error(f"Transpose failed: {e}")
            raise RuntimeError(f"Transpose failed for {self.in_path}") from e

    def encode(self):
        try:
            with open(self.in_path, "rb") as fin, open(self.out_path, "wb") as fout:
                while True:
                    block = fin.read(self.block_size)
                    if not block:
                        break

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
            try:
                if self.out_path.exists():
                    os.remove(self.out_path)
            except Exception as cleanup_err:
                logger.error(
                    f"Failed to remove partial output {self.out_path}: {cleanup_err}"
                )

            # Raise an explicit error so callers don't have to deal with False/None
            raise RuntimeError(f"Encoding failed for {self.in_path}") from e

    def run(self):
        self.encode()
        return self.transpose()
