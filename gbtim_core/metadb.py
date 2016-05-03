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
import pytz
import sqlite3
import logging
import re
import hashlib
from os import path

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
    db = pw.SqliteDatabase(filename)
    database_proxy.initialize(db)
    db.connect()
    db.create_tables([
        File,
        FileCopy,
        Target,
        Allocation,
        Session,
        ScanSet,
        Scan,
        GuppiFile,
        ], safe=True)


# Tables pertaining to the raw data
# =================================


class File(base_model):
    """Base table for all data files.

    This model exits to tie together variouse 'file' models (such as
    GuppiFile), and the FileCopy model.

    """

    #stuff = pw.CharFieryKeyField()


class FileCopy(base_model):
    """A copy of a file.

    Attributes
    ----------
    file
    directory
    host
    corrupt
    hash : 64 character string
        sha256 hash of the file, in hex.

    """

    file = pw.ForeignKeyField(File, related_name='copies', null=False)
    path = pw.CharField(max_length=128, null=False)
    host = pw.CharField(max_length=128, null=False)
    corrupt = pw.BooleanField(default=False)
    hash = pw.CharField(max_length=64, null=True)


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
        deliminator = '-'
        return 'GBT' + self.term + deliminator + "%03d" % self.number


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

    @property
    def identity(self):
        return self.allocation.name + '.%04d' % self.number


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

    @property
    def session(self):
        return self.scans[0].session


class Scan(base_model):
    """A telescope scan: a contiguous series of integrations.

    Attributes
    ----------
    session
    target
    scanset
    number
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
    target = pw.ForeignKeyField(Target, related_name='scans', null=True)
    number = pw.IntegerField(null=False)     # Can get from file name.
    # This requires the GO fits files
    scanset = pw.ForeignKeyField(ScanSet, related_name='scans', null=True)
    # GUPPI mode.
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

    @property
    def identity(self):
        return self.session.identity + ".%04d" % self.number


class GuppiFile(base_model):
    """A single file of GUPPI data, which may only be a subset of a scan.

    Attributes
    ----------
    scan
    filename

    """

    file = pw.ForeignKeyField(File, null=False)
    scan = pw.ForeignKeyField(Scan, related_name='files', null=False)
    number = pw.IntegerField(null=False)

    @property
    def identity(self):
        return self.scan.identity + ".%04d" % self.number

    @property
    def filecopies(self):
        return self.file.copies



# Meta data retrieval functions
# =============================

def get_guppi_filename_info(filename):
    """Parse filename of GUPPI data to retrieve meta data.

    Note that this information is not enough to uniquly identify a file. For
    that you need the session number, which is in the header.

    Returns
    -------
    info : dict
        Metadata for the file. Keys are listed above.

    """

    info = {}
    filename = path.basename(filename)
    filename_re = "guppi_[0-9]{5}_.*_([0-9]{4})_([0-9]{4}).fits"
    match = re.match(filename_re, filename)
    scan = int(match.group(1))
    number = int(match.group(2))
    info['scan.number'] = scan
    info['file.number'] = number
    return info


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
    #print repr(hdulist[0].header)

    data_len = len(hdulist[1].data)

    info['scan.mode'] = header0['OBS_MODE'].strip()

    session_id = header0['PROJID'].strip()
    session_id_re = "AGBT([0-9]{2}[ABC])_([0-9]*)_([0-9]*)"
    match = re.match(session_id_re, session_id)
    info['allocation.term'] = match.group(1)
    info['allocation.number'] = int(match.group(2))
    info['session.number'] = int(match.group(3))

    info['target.name'] = header0['SRC_NAME'].strip()


    hdulist.close()
    return info


def get_guppi_data_info(filename):
    """Read GUPPI data to retrieve meta data.

    Like :func:`get_guppi_header_info` but also reads the pointing information
    to retrieve *cadence*, *ra_min*, *ra_max*, *dec_min*, *dec_max, *az_min*,
    *az_max*, *el_min*, and *el_max*.

    Returns
    -------
    info : dict
        Metadata for the file. Keys listed above, plus those for
        :func:`get_guppi_header_info`.

    """

    info = {}

    hdulist = fits.open(filename, 'readonly')
    header0 = hdulist[0].header
    header1 = hdulist[1].header
    data = hdulist[1].data

    #print repr(header1)

    info['scan.cadence'] = float(header1['TBIN'])

    start_time = float(data[0]['OFFS_SUB'] - data[0]['TSUBINT'] / 2)
    end_time = float(data[-1]['OFFS_SUB'] + data[-1]['TSUBINT'] / 2)
    start_time += header0['STT_SMJD'] + header0['STT_OFFS']
    end_time += header0['STT_SMJD'] + header0['STT_OFFS']
    unix_offset = _mjd_to_unix(header0['STT_IMJD'])
    start_time += unix_offset
    end_time += unix_offset
    info['scan.start_time'] = start_time
    info['scan.end_time'] = end_time

    for name, fits_name in [('ra', 'RA_SUB'), ('dec', 'DEC_SUB'),
            ('az', 'TEL_AZ'), ('zen', 'TEL_ZEN')]:
        d = data[fits_name]
        d_min = float(min(d))
        d_max = float(max(d))
        info[name + '_min'] = d_min
        info[name + '_max'] = d_max

    zen_min = info.pop('zen_min')
    info['el_max'] = 90 - zen_min
    zen_max = info.pop('zen_max')
    info['el_min'] = 90 - zen_max

    hdulist.close()
    return info


def hashfile(filename):
    block = 1024**2
    hash = hashlib.sha256()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(block), b""):
            hash.update(chunk)
    return hash.hexdigest()


def _mjd_to_unix(mjd):

    mjd_epoch = datetime.datetime(1858, 11, 17, 0, 0, 0, 0)
    date = mjd_epoch + datetime.timedelta(mjd)
    unix_delta = date - datetime.datetime.utcfromtimestamp(0)
    unix_time = unix_delta.total_seconds()
    return unix_time

