from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="TRSEnc",
    version="0.1.0",
    author="Alireza Alipoor,Aryan Shapasand",
    packages=find_packages(),
    install_requires=requirements,
)
