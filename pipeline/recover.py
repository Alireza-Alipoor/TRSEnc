from pathlib import Path

from src.encoding.config_reader import read_config
from src.recover.metadata1_remover import Metadata1Remover
from src.recover.metadata2_remover import Metadata2Remover
from src.recover.remove_padding import PaddingRemover
from src.recover.rs_decode import RSDecoder

if __name__ == "__main__":
    input_file = Path(input("file to decode:"))

    configs = read_config("configs/configs.yaml")

    metadata2_remover = Metadata2Remover(configs, input_file)
    metadata, file_after_metadata_removal = metadata2_remover.run()

    padding_remover = PaddingRemover(metadata["padding"], file_after_metadata_removal)
    removed_padding_path, file_without_padding = padding_remover.run()

    decoder = RSDecoder(
        metadata,
        file_without_padding,
    )
    decoded_file_path = decoder.run()

    metadata1_remover = Metadata1Remover(decoded_file_path)
    metadata1_remover.run()
