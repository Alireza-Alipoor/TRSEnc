from pathlib import Path

from src.config_reader import read_config
from src.metadata1_appender import Metadata1Appender
from src.metadata2_adder import Metadata2Adder
from src.padding_prepend import PaddingAdder
from src.rs_encoding import RSEncoding

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
