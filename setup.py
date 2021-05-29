"""Install deepthought."""

from setuptools import setup
from setuptools import find_packages

VERSION = "0.0.1"
PROJECT_URL = "https://github.com/ndsystems/deepthought"
DOWNLOAD_URL = "{}/releases/tag/v{}".format(PROJECT_URL, VERSION)

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

# Had to change versions of some libs and also removed version requirements for some others. 
INSTALL_REQUIRES = [
    "rpyc==5.0.1",
    "tifffile>=2020.9.3",
    "cellpose==0.6",
    "numpy>=1.19.4",
    "scikit-image>=0.17.2",
    "ophyd==1.6.0",
    "bluesky==1.6.7",
    "databroker==1.2.0",
    "magicgui",
    "PyQt5>=5.12.3,!=5.15.0",
    "napari",
]
DOCS = [
    "recommonmark",
    "sphinx",
]
# OTHERS = [ ]
# TESTS = [ ]
# ALL = DOCS + OTHERS + TESTS
ALL = DOCS

setup(name="deepthought",
      version=VERSION,
      description="DESCRIPTION GOES HERE",
      long_description=LONG_DESCRIPTION,
      long_description_content_type="text/markdown",
      author="Kesavan Subburam",
      author_email="pskeshu@gmail.com",
      url=PROJECT_URL,
      download_url=DOWNLOAD_URL,
      license="MIT",
      install_requires=INSTALL_REQUIRES,
      extras_require={
          "docs": DOCS,
          # "others": OTHERS,
          # "tests": TESTS,
          "all": ALL,
      },
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Environment :: Console",
          "Intended Audience :: Developers",
          "Intended Audience :: Education",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: MIT License",
          "Natural Language :: English",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Operating System :: OS Independent",
          "Topic :: Scientific/Engineering :: Artificial Intelligence",
          "Topic :: Software Development :: Libraries",
          "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      packages=find_packages())
