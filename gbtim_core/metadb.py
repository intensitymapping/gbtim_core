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

    Allocation
    Session
    ScanSet
    Scan
    GuppiFile

"""


import datetime
import sqlite3
import logging

import peewee as pw


# Global Variables and Constants
# ==============================

logger = logging.getLogger(__name__)

database_proxy = pw.Proxy()


# Peewee setup
# ============

class base_model(pw.Model):
    """Baseclass for all models."""

    class Meta:
        database = database_proxy



# Tables pertaining to the raw data
# =================================

class Target(base_model):
    """Sky source target.

    Attributes
    ----------
    name
    ra
    dec

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

    """

    allocation = pw.ForeignKeyField(Allocation, related_name='sessions')
    number = pw.IntegerField(null=False)


class ScanSet(base_model):
    """A group of associated scans.

    The scans within a scan set are all initiated by the same Astrid call.
    For typical mapping scans, a set is a series of sequential scans at the
    same elevation angle. For calibration scans these can be on-source and
    off-source scans, or the legs of a spider scan.

    Attributes
    ----------
    session
    target
    kind

    """

    session = pw.ForeignKeyField(Session, related_name='scansets')
    target = pw.ForeignKeyField(Target, related_name='scansets')
    kind = pw.CharField(max_length=128)


class Scan(base_model):
    """A telescope scan: a contiguous series of integrations.

    Attributes
    ----------
    scanset
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

    scanset = pw.ForeignKeyField(ScanSet, related_name='scans')
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





