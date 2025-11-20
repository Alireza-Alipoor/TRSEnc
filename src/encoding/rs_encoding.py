import os
from pathlib import Path

import numpy as np
from reedsolo import RSCodec

from src.logging.logger import get_logger

logger = get_logger(__name__)


class RSEncoding:
    def __init__(self, config, in_path: Path):
        self.rs_params = config["encoding"]["reed_solomon"]
        self.block_size = self.rs_params["nsize"] - self.rs_params["nsym"]
        self.RS = RSCodec(**self.rs_params)

        self.in_path = in_path
        self.encoded_path = (
            self.in_path.parent / f"{self.in_path.stem}_encoded{self.in_path.suffix}"
        )
        self.out_path = self.encoded_path
        self.output_size = None

    def encode(self):
        logger.info("Started Reed-Solomon encoding")
        try:
            with open(self.in_path, "rb") as fin, open(self.encoded_path, "wb") as fout:
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

            self.output_size = self.encoded_path.stat().st_size
            self.out_path = self.encoded_path
            logger.info(f"Successfully encoded {self.in_path} -> {self.encoded_path}")
            logger.info(f"Encoded output size: {self.output_size} bytes")

        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            try:
                if self.encoded_path.exists():
                    os.remove(self.encoded_path)
            except Exception as cleanup_err:
                logger.error(
                    f"Failed to remove partial encoded file {self.encoded_path}: "
                    f"{cleanup_err}"
                )
            raise RuntimeError(f"Encoding failed for {self.in_path}") from e

    def transpose(self):
        try:
            src_path = self.encoded_path
            file_size = src_path.stat().st_size
            cols = self.rs_params["nsize"]

            if file_size % cols != 0:
                raise ValueError(
                    f"Encoded file size ({file_size}) is not divisible by cols ({cols})"
                )

            rows = file_size // cols
            out_path = src_path.parent / f"{src_path.stem}_T{src_path.suffix}"

            src = np.memmap(src_path, dtype=np.uint8, mode="r", shape=(rows, cols))
            dst = np.memmap(out_path, dtype=np.uint8, mode="w+", shape=(cols, rows))

            try:
                block = 1024
                for i in range(0, rows, block):
                    for j in range(0, cols, block):
                        sub = src[i : i + block, j : j + block]
                        dst[j : j + block, i : i + block] = sub.T
                dst.flush()
                logger.info(f"Transposed file written to {out_path}")
                logger.info(f"Input: {rows}x{cols}, Output: {cols}x{rows}")
            finally:
                del src
                del dst

            self.out_path = out_path
            self.output_size = out_path.stat().st_size

            return out_path

        except Exception as e:
            logger.error(f"Transpose failed: {e}")
            raise RuntimeError(f"Transpose failed for {self.out_path}") from e

    def cleanup_intermediate_files(self):
        files_to_delete = [self.in_path, self.encoded_path]
        for target in files_to_delete:
            try:
                if target.exists():
                    target.unlink()
                    logger.info(f"Deleted intermediate file: {target}")
            except Exception as e:
                logger.error(f"Failed to delete file {target}: {e}")

    def run(self):
        self.encode()
        result = self.transpose()
        self.cleanup_intermediate_files()
        return result
