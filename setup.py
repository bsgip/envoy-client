import setuptools
import sys

    
with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'requests',
    'xmltodict'
]



setuptools.setup(
    name="envoy-client",
    version="0.1",
    author="BSGIP",
    description="2030.5 DER Client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=None,
    packages=setuptools.find_packages(),
    classifiers=[
    ],
    python_requires='>=3.6',
    install_requires=install_requires,
)
