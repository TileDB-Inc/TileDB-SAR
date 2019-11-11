"""Setup."""

from setuptools import setup, find_packages

with open("insar/__init__.py") as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue


with open("README.md") as f:
    readme = f.read()

# Runtime requirements.
inst_reqs = [
    "click",
    "rasterio",
    "numpy"
]

extra_reqs = {
    "test": ["pytest"],
    "dev": ["pytest"]
}

setup(
    name="insar",
    version=version,
    description=u"Interferometric SAR processing using TileDB.",
    long_description=readme,
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords="SAR INSAR TileDB",
    author=u"TileDB Inc",
    url="https://github.com/TileDB-Inc/TileDB-SAR",
    license="MIT",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    install_requires=inst_reqs,
    extras_require=extra_reqs,
    entry_points="""
      [rasterio.rio_plugins]
      stack-sar=insar.scripts.cli:stack_sar
      process-stack=insar.scripts.cli:process_stack
      flight-path=insar.scripts.flight:flight_path
      """,
)
