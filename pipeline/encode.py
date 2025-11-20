from pathlib import Path

from src.encoding.config_reader import read_config
from src.encoding.metadata1_appender import Metadata1Appender
from src.encoding.metadata2_adder import Metadata2Adder
from src.encoding.padding_prepend import PaddingAdder
from src.encoding.rs_encoding import RSEncoding

if __name__ == "__main__":

    configs = read_config("configs/configs.yaml")

    input_file = Path(input("file to encode:"))

    metadata1append = Metadata1Appender(configs, input_file)
    input_file_path = metadata1append.run()

    rs_encode = RSEncoding(configs, input_file_path)
    rs_encoded_file = rs_encode.run()

    padding = PaddingAdder(configs, rs_encoded_file)
    padded_file = padding.run()

    Metadata2Adde = Metadata2Adder(configs, padded_file)
    Metadata2Adde.run()
