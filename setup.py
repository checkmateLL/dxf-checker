from setuptools import setup, find_packages
import os

# Read version from __init__.py
def get_version():
    with open(os.path.join("dxf_checker", "__init__.py"), "r") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.0.0"

# Read README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="checkmatell-dxf-checker",
    version=get_version(),
    author="Juliya Lehka",
    author_email="juliya.legkaya@gmail.com",
    description="A tool for validating DXF segment integrity",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/checkmateLL/dxf-checker",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: CAD",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "ezdxf>=1.0.2",
    ],
    entry_points={
        "console_scripts": [
            "dxf-checker=dxf_checker.main:main",
        ],
    },
)