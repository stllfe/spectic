from setuptools import setup, find_packages

setup(
    name="spectic",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "spectic": ["py.typed", "**/*.pyi"],
    },
    python_requires=">=3.9",
    install_requires=[
        "msgspec>=0.18.0",
    ],
    extras_require={
        "yaml": ["pyyaml>=6.0"],
        "dev": [
            "pytest>=7.0.0",
            "ruff>=0.0.260",
        ],
    },
    description="Data validation, serialization, and parsing library with a simple API",
    long_description=open("readme.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
)
