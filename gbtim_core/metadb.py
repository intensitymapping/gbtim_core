"""
Database of metadata.

.. currentmodule:: gbtim_core.metadb

Module for interacting with the index of the GBTIM data. The module is based on
the `peewee` python module and each table in the relational database is
represented by a class with instances of the class representing rows of the
table.

Classes
=======

.. autosummary::
   :toctree: generated/

    Target
    Allocation
    Session
    ScanSet
    Scan
    GuppiFile


Functions
=========

.. autosummary::
   :toctree: generated/

    connect_db
    read_guppi_header_info
    read_guppi_data_info


Constants
=========

DATAFILE_PATTERN : string
    Regular expression that matches data GUPPI psrfits file names.

"""


import datetime
import sqlite3
import logging
import re

import peewee as pw
from astropy.io import fits


# Global Variables and Constants
# ==============================

logger = logging.getLogger(__name__)

database_proxy = pw.Proxy()

# Regex for filenames that match our data files.
DATAFILE_PATTERN = "guppi_[0-9]{5}_.*_[0-9]{4}_[0-9]{4}.fits"


# Peewee setup
# ============

class base_model(pw.Model):
    """Baseclass for all models."""

    class Meta:
        database = database_proxy


def connect_db(filename):
    """Connect to an SQLite database given by its filename."""

    logger.info("Connecting to database %s" % filename)
    database_proxy.initialize(pw.SqliteDatabase(filename))


# Tables pertaining to the raw data
# =================================

class Target(base_model):
    """Sky source target.

    Attributes
    ----------
    name
    ra
    dec
    scans

    """

    name = pw.CharField(max_length=128, null=False)
    ra = pw.DoubleField(null=True)
    dec = pw.DoubleField(null=True)


class Allocation(base_model):
    """Telescope allocation or project number.

    Attributes
    ----------
    term
    number
    name

    """

    term = pw.CharField(max_length=16, null=False)
    number = pw.IntegerField(null=False)

    @property
    def name(self):
        """Allocation name, as derived from *term* and *number*.

        eg. "GBT10B-036"

        """
        return 'GBT' + self.semester + deliminator + "%03d" % self.number


class Session(base_model):
    """Observing session, usually a night of observing.

    Attributes
    ----------
    allocation
    number
    scans

    """

    allocation = pw.ForeignKeyField(Allocation, related_name='sessions')
    number = pw.IntegerField(null=False)


class ScanSet(base_model):
    """A group of associated scans.

    The scans within a scan set are all initiated by the same Astrid call.
    For typical mapping scans, a set is a series of sequential scans at the
    same elevation angle. For calibration scans these can be on-source and
    off-source scans, or the legs of a spider scan.

    This is the only field that cannot be filled from the raw GUPPI data files,
    and requires inspecting the GBT GO fits files.

    Attributes
    ----------
    kind
    scans

    """

    kind = pw.CharField(max_length=128)


class Scan(base_model):
    """A telescope scan: a contiguous series of integrations.

    Attributes
    ----------
    session
    target
    scanset
    mode
    cadence
    ra_min
    ra_max
    dec_min
    dec_max
    az_min
    az_max
    el_min
    el_max
    start_time
    end_time

    """

    session = pw.ForeignKeyField(Session, related_name='scans')
    target = pw.ForeignKeyField(Target, related_name='scans')
    scanset = pw.ForeignKeyField(ScanSet, related_name='scans', null=True)
    mode = pw.CharField(max_length=16, null=True)
    cadence = pw.DoubleField(null=True)
    ra_min = pw.DoubleField(null=True)
    ra_max = pw.DoubleField(null=True)
    dec_min = pw.DoubleField(null=True)
    dec_max = pw.DoubleField(null=True)
    az_min = pw.DoubleField(null=True)
    az_max = pw.DoubleField(null=True)
    el_min = pw.DoubleField(null=True)
    el_max = pw.DoubleField(null=True)
    start_time = pw.DoubleField(null=True)
    end_time = pw.DoubleField(null=True)


class GuppiFile(base_model):
    """A single file of data, which may only be a subset of a scan.

    Attributes
    ----------
    scan
    filename
    md5sum

    """

    scan = pw.ForeignKeyField(Scan, related_name='files')
    filename = pw.CharField(max_length=128, null=False)
    md5sum = pw.CharField(max_length=32)



# Meta data retrieval functions
# =============================

def get_guppi_header_info(filename):
    """Read header of GUPPI data to retrieve meta data.

    Given a GUPPI file name, this function retrieves the *allocation.term*,
    *allocation.number*, *session*, *target*, *mode*, *cadence*, *start_time*,
    and *end_time* of the data. These parameters are stored in the header and
    do not require reading a significant portion of the file.

    Returns
    -------
    info : dict
        Metadata for the file. Keys are listed above.

    """

    info = {}

    hdulist = fits.open(filename, 'readonly')
    header0 = hdulist[0].header
    header1 = hdulist[1].header
    data_len = len(hdulist[1].data)

    info['mode'] = header0['OBS_MODE'].strip()

    session_id = header0['PROJID'].strip()
    session_id_re = "AGBT([0-9]{2}[ABC])_([0-9]*)_([0-9]*)"
    match = re.match(session_id_re, session_id)
    info['allocation.term'] = match.group(1)
    info['allocation.number'] = int(match.group(2))
    info['session'] = int(match.group(3))

    hdulist.close()
    return info

def get_guppi_data_info(filename, md5=False):
    """Read GUPPI data to retrieve meta data.

    Like :func:`get_guppi_header_info` but also reads the pointing information
    to retrieve *ra_min*, *ra_max*, *dec_min*, *dec_max, *az_min*, *az_max*,
    *el_min*, and *el_max*. Optionally perform an md5sum on the file (*md5*).

    Returns
    -------
    info : dict
        Metadata for the file. Keys listed above, plus those for
        :func:`get_guppi_header_info`.

    """

    info = get_guppi_header_info(filename)

    hdulist = fits.open(filename, 'readonly')

    hdulist.close()
    return info

