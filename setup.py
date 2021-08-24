import setuptools
import sys

    
with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'requests>=2.20',
    'xmltodict>=0.12',
    'pydantic>=1.8'
]



setuptools.setup(
    name="envoy-client",
    version="0.1.1",
    author="BSGIP",
    description="2030.5 DER Client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bsgip/envoy-client",
    packages=setuptools.find_packages(),
    classifiers=[
    ],
    python_requires='>=3.6',
    install_requires=install_requires,
)
