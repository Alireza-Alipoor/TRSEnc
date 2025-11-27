import os
from pathlib import Path

import numpy as np
from reedsolo import RSCodec

from src.logging.logger import get_logger

logger = get_logger(__name__)


class RSDecoder:
    """
    Reverse of RSEncoding.run():

        original -> RS encode -> encoded -> transpose -> encoded_T

    This class takes the transposed file (encoded_T), un-transposes it back
    to the original encoded layout, then RS-decodes each block.
    """

    def __init__(self, config, in_path: Path):
        self.rs_params = config["rs"]
        self.block_size = self.rs_params["nsize"] - self.rs_params["nsym"]
        self.RS = RSCodec(**self.rs_params)

        self.in_path = in_path

        self.encoded_path = (
            self.in_path.parent / f"{self.in_path.stem}_unT{self.in_path.suffix}"
        )
        self.decoded_path = (
            self.in_path.parent / f"{self.in_path.stem}_decoded{self.in_path.suffix}"
        )

        self.out_path = self.decoded_path

        nsize = self.rs_params["nsize"]
        nsym = self.rs_params["nsym"]
        block_size = nsize - nsym
        blocks = config["size_before_padding"] // nsize
        self.original_size = blocks * block_size
        self.output_size: int | None = None

    def untranspose(self) -> Path:
        """
        Undo the transpose performed in RSEncoding.transpose().

        RSEncoding.transpose() takes the encoded file shaped as:
            (rows, nsize)
        and writes its transpose shaped as:
            (nsize, rows)

        Here we know the first dimension of the transposed file is nsize again,
        so we reshape as (nsize, cols_T) and write back (cols_T, nsize).
        """
        logger.info("Started un-transpose of Reed-Solomon encoded file")

        try:
            src_path = self.in_path
            file_size = src_path.stat().st_size
            nsize = self.rs_params["nsize"]

            if file_size % nsize != 0:
                raise ValueError(
                    f"Transposed file size ({file_size}) is not divisible by "
                    f"nsize ({nsize}); file may be corrupt"
                )

            cols_T = file_size // nsize  # == original 'rows'
            rows_T = nsize  # == original 'cols'

            logger.debug(
                f"Untranspose: src shape=({rows_T}, {cols_T}), "
                f"dst shape=({cols_T}, {rows_T})"
            )

            src = np.memmap(src_path, dtype=np.uint8, mode="r", shape=(rows_T, cols_T))
            dst = np.memmap(
                self.encoded_path,
                dtype=np.uint8,
                mode="w+",
                shape=(cols_T, rows_T),
            )

            try:
                block = 1024
                for i in range(0, rows_T, block):
                    i_end = min(i + block, rows_T)
                    for j in range(0, cols_T, block):
                        j_end = min(j + block, cols_T)
                        sub = src[i:i_end, j:j_end]
                        dst[j:j_end, i:i_end] = sub.T

                dst.flush()
                logger.info(f"Un-transposed file written to {self.encoded_path}")
            finally:
                del src
                del dst

            return self.encoded_path

        except Exception as e:
            logger.error(f"Un-transpose failed: {e}")
            raise RuntimeError(f"Un-transpose failed for {self.in_path}") from e

    def decode(self) -> Path:
        """
        RS-decode the un-transposed encoded file into the original data.
        """
        logger.info("Started Reed-Solomon decoding")

        nsize = self.rs_params["nsize"]

        try:
            with (
                open(self.encoded_path, "rb") as fin,
                open(self.decoded_path, "wb") as fout,
            ):
                while True:
                    block = fin.read(nsize)
                    if not block:
                        break

                    if len(block) == 0:
                        break

                    if len(block) != nsize:
                        raise ValueError(
                            "Encoded file size is not a multiple of nsize "
                            f"({nsize}); file may be truncated"
                        )

                    decoded = self.RS.decode(block)

                    if isinstance(decoded, tuple):
                        msg = decoded[0]
                    else:
                        msg = decoded

                    fout.write(bytes(msg))

            self.output_size = self.decoded_path.stat().st_size
            logger.info(f"Decoded raw size before trimming: {self.output_size} bytes")

            if self.original_size is not None:
                if self.original_size > self.output_size:
                    raise ValueError(
                        f"original_size ({self.original_size}) is larger than "
                        f"the decoded file size ({self.output_size})"
                    )

                if self.original_size < self.output_size:
                    with open(self.decoded_path, "rb+") as f:
                        f.truncate(self.original_size)
                    self.output_size = self.original_size
                    logger.info(
                        f"Truncated decoded file to original size "
                        f"{self.original_size} bytes"
                    )

            logger.info(
                f"Successfully decoded {self.encoded_path} -> {self.decoded_path}"
            )
            logger.info(f"Final decoded size: {self.output_size} bytes")

            self.out_path = self.decoded_path
            return self.decoded_path

        except Exception as e:
            logger.error(f"Decoding failed: {e}")
            try:
                if self.decoded_path.exists():
                    os.remove(self.decoded_path)
            except Exception as cleanup_err:
                logger.error(
                    f"Failed to remove partial decoded file "
                    f"{self.decoded_path}: {cleanup_err}"
                )
            raise RuntimeError(f"Decoding failed for {self.encoded_path}") from e

    def cleanup_intermediate_files(self):
        """
        Delete the transposed input and the un-transposed intermediate.
        """
        for target in (self.in_path, self.encoded_path):
            try:
                if target.exists():
                    target.unlink()
                    logger.info(f"Deleted intermediate file: {target}")
            except Exception as e:
                logger.error(f"Failed to delete file {target}: {e}")

    def run(self) -> Path:

        self.untranspose()
        result = self.decode()
        self.cleanup_intermediate_files()
        return result
