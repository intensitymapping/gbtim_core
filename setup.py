from setuptools import setup, find_packages
import os

from gbtim_core import __version__


REQUIRES = ['caput']

# Don't install requirements if on ReadTheDocs build system.
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    requires = []
else:
    requires = REQUIRES

setup(
    name = 'gbtim_core',
    version = __version__,
    packages = ['gbtim_core', 'gbtim_core.tests'],
    scripts=[],
    install_requires=requires,
    extras_require = {
        },

    # metadata for upload to PyPI
    author = "Kiyo Masui",
    author_email = "kiyo@physics.ubc.ca",
    description = "GBTIM analysis software core",
    license = "GPL v3.0",
    url = "http://github.com/intensitymapping/gbtim_core"
)
