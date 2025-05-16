from reedsolo import RSCodec


def read_text_file(file_path: str) -> str:
    """
    Read the entire contents of a UTF-8 text file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
