"""
Data format for GBT Intensity Mapping.

.. currentmodule:: gbtim_core.imdata

This module is heavily based on :mod:`caput.memh5` and :mod:`caput.tod`.


Classes
=======

.. autosummary::
   :toctree: generated/

   IMData
   Reader


"""


from caput import tod


class IMData(tod.TOData):
    """GBT Intensity Mapping data.

    Inherits from :class:`caput.tod.TOData`, which inherits most of its
    functionality from :class:`caput.memh5.BasicCont`.

    """


class Reader(tod.Reader):
    """Provides high level reading of GBT Intensity Mapping data.

    Inherits from :class:`caput.tod.Reader`.

    """

    data_class = IMData
