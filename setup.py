import pathlib
from setuptools import setup, find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name="qscache",
    version="0.2.11",
    description="A package to cache Django querysets.s",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/MojixCoder/qscache",
    author="Mojix Coder",
    author_email="mojixcoder@gmail.com",
    license="BSD",
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    packages=find_packages(exclude=["venv", ".idea"]),
    install_requires=[
        "Django >= 3.0.12,<4.0.0",
        "django-redis == 5.0",
    ],
)
