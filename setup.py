from setuptools import setup, find_packages

setup(
    name="cheat-sheet-creator",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "Pillow",
        "reportlab",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
        ],
    },
) 