"""
from setuptools import setup
from pathlib import Path

long_description = (Path(__file__).parent / 'README.md').read_text()

setup(
    name='lilliepy-dir-router',
    version='0.1',
    packages=['lilliepy_dir_router'],
    install_requires=[
        'reactpy',
        'reactpy-router',
    ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    description='file based router for reactpy or lilliepy framework',
    keywords=["lilliepy", "lilliepy-dir-router", "reactpy", "router", "file router", "file based router", "file-router", "file-based-router"]
)
"""

from lilliepy_dir_router import FileRouter

FileRouter("test", True)
