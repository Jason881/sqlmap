#!/usr/bin/env python

"""
Copyright (c) 2006-2021 sqlmap developers (http://sqlmap.org/)
See the file 'LICENSE' for copying permission
"""

import sqlite3

from lib.core.common import getSafeExString
from lib.core.common import unsafeSQLIdentificatorNaming
from lib.core.exception import SqlmapConnectionException
from lib.core.exception import SqlmapGenericException
from lib.core.exception import SqlmapValueException
from lib.core.settings import UNICODE_ENCODING
from lib.utils.safe2bin import safechardecode

class Replication(object):
    """
    This class holds all methods/classes used for database
    replication purposes.
    """

    def __init__(self, dbpath):
        try:
            self.dbpath = dbpath
            self.connection = sqlite3.connect(dbpath)
            self.connection.isolation_level = None
            self.cursor = self.connection.cursor()
        except sqlite3.OperationalError as ex:
            errMsg = "error occurred while opening a replication "
            errMsg += f"file '{dbpath}' ('{getSafeExString(ex)}')"
            raise SqlmapConnectionException(errMsg)

    class DataType(object):
        """
        Using this class we define auxiliary objects
        used for representing sqlite data types.
        """

        def __init__(self, name):
            self.name = name

        def __str__(self):
            return self.name

        def __repr__(self):
            return f"<DataType: {self}>"

    class Table(object):
        """
        This class defines methods used to manipulate table objects.
        """

        def __init__(self, parent, name, columns=None, create=True, typeless=False):
            self.parent = parent
            self.name = unsafeSQLIdentificatorNaming(name)
            self.columns = columns
            if create:
                try:
                    self.execute(f'DROP TABLE IF EXISTS "{self.name}"')
                    if not typeless:
                        self.execute(
                            f"""CREATE TABLE "{self.name}" ({','.join(f'"{unsafeSQLIdentificatorNaming(colname)}" {coltype}' for colname, coltype in self.columns)})"""
                        )
                    else:
                        self.execute(
                            f"""CREATE TABLE "{self.name}" ({','.join(f'"{unsafeSQLIdentificatorNaming(colname)}"' for colname in self.columns)})"""
                        )
                except Exception as ex:
                    errMsg = f"problem occurred ('{getSafeExString(ex, UNICODE_ENCODING)}') while initializing the sqlite database "
                    errMsg += f"located at '{self.parent.dbpath}'"
                    raise SqlmapGenericException(errMsg)

        def insert(self, values):
            """
            This function is used for inserting row(s) into current table.
            """

            if len(values) == len(self.columns):
                self.execute(
                    f"""INSERT INTO "{self.name}" VALUES ({','.join(['?'] * len(values))})""",
                    safechardecode(values),
                )
            else:
                errMsg = "wrong number of columns used in replicating insert"
                raise SqlmapValueException(errMsg)

        def execute(self, sql, parameters=None):
            try:
                self.parent.cursor.execute(sql, parameters or [])
            except sqlite3.OperationalError as ex:
                errMsg = f"problem occurred ('{getSafeExString(ex, UNICODE_ENCODING)}') while accessing sqlite database "
                errMsg += f"located at '{self.parent.dbpath}'. Please make sure that "
                errMsg += "it's not used by some other program"
                raise SqlmapGenericException(errMsg)

        def beginTransaction(self):
            """
            Great speed improvement can be gained by using explicit transactions around multiple inserts.
            Reference: http://stackoverflow.com/questions/4719836/python-and-sqlite3-adding-thousands-of-rows
            """
            self.execute('BEGIN TRANSACTION')

        def endTransaction(self):
            self.execute('END TRANSACTION')

        def select(self, condition=None):
            """
            This function is used for selecting row(s) from current table.
            """
            _ = f'SELECT * FROM {self.name}'
            if condition:
                _ += f'WHERE {condition}'
            return self.execute(_)

    def createTable(self, tblname, columns=None, typeless=False):
        """
        This function creates Table instance with current connection settings.
        """
        return Replication.Table(parent=self, name=tblname, columns=columns, typeless=typeless)

    def __del__(self):
        self.cursor.close()
        self.connection.close()

    # sqlite data types
    NULL = DataType('NULL')
    INTEGER = DataType('INTEGER')
    REAL = DataType('REAL')
    TEXT = DataType('TEXT')
    BLOB = DataType('BLOB')
