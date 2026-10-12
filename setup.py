from setuptools import setup, find_packages

setup(
    name="skillforge",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "rich>=13.7.0",
        "click>=8.1.7",
        "jsonschema>=4.21.0",
    ],
    entry_points={
        "console_scripts": [
            "skillforge=skillforge.cli:main",
        ],
    },
)
