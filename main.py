from reedsolo import RSCodec
import numpy as np

# Reed-Solomon parameters
RS_SYMBOL_SIZE = 255


def read_text_file(file_path: str) -> str:
    """
    Read the entire contents of a UTF-8 text file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def chunk_text_to_matrix(text: str, row_length: int) -> list[str]:
    """
    Chunk the input text into fixed-length rows, padding with null bytes if needed.
    """
    if row_length > RS_SYMBOL_SIZE:
        raise ValueError(
            f"Row length must be ≤ {RS_SYMBOL_SIZE} for RS(255, k) encoding.")

    padding_needed = (row_length - len(text) % row_length) % row_length
    padded_text = text + ('\x00' * padding_needed)

    return [padded_text[i:i + row_length] for i in range(0, len(padded_text), row_length)]


def transpose_matrix(matrix: list[str]) -> np.ndarray:
    """
    Convert list of strings into a NumPy matrix and transpose it.
    """
    byte_matrix = np.array([list(row.encode('utf-8'))
                           for row in matrix], dtype=np.uint8)
    return byte_matrix.T


def encode_rows_with_rs(transposed_matrix: np.ndarray) -> list[bytes]:
    """
    Apply Reed-Solomon encoding to each row of the transposed matrix.
    Uses maximum number of parity bytes (255 - k).
    """
    encoded_rows = []
    for row in transposed_matrix:
        k = len(row)
        rs = RSCodec(RS_SYMBOL_SIZE - k)
        encoded_row = rs.encode(bytes(row))
        encoded_rows.append(encoded_row)
    return encoded_rows


def write_encoded_output(encoded_rows: list[bytes], output_path: str) -> None:
    """
    Write encoded rows to a binary output file.
    """
    with open(output_path, 'wb') as f:
        for row in encoded_rows:
            f.write(row)