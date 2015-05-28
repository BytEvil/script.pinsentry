# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcvfs
import sqlite3
import xbmcgui

__addon__ = xbmcaddon.Addon(id='script.pinsentry')

# Import the common settings
from settings import log
from settings import os_path_join


#################################
# Class to handle database access
#################################
class PinSentryDB():
    def __init__(self):
        # Start by getting the database location
        self.configPath = xbmc.translatePath(__addon__.getAddonInfo('profile'))
        self.databasefile = os_path_join(self.configPath, "pinsentry_database.db")
        log("PinSentryDB: Database file location = %s" % self.databasefile)
        # Make sure that the database exists if this is the first time
        self.createDatabase()

    # Removes the database if it exists
    def cleanDatabase(self):
        msg = "%s%s" % (__addon__.getLocalizedString(32113), "?")
        isYes = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32001), msg)
        if isYes:
            # If the database file exists, delete it
            if xbmcvfs.exists(self.databasefile):
                xbmcvfs.delete(self.databasefile)
                log("PinSentryDB: Removed database: %s" % self.databasefile)
            else:
                log("PinSentryDB: No database exists: %s" % self.databasefile)

    # Creates the database if the file does not already exist
    def createDatabase(self):
        # Make sure the database does not already exist
        if not xbmcvfs.exists(self.databasefile):
            # Get a connection to the database, this will create the file
            conn = sqlite3.connect(self.databasefile)
            conn.text_factory = str
            c = conn.cursor()

            # Create the version number table, this is a simple table
            # that just holds the version details of what created it
            # It should make upgrade later easier
            c.execute('''CREATE TABLE version (version text primary key)''')

            # Insert a row for the version
            versionNum = "1"

            # Run the statement passing in an array with one value
            c.execute("INSERT INTO version VALUES (?)", (versionNum,))

            # Create a table that will be used to store each Video and its access level
            # The "id" will be auto-generated as the primary key
            # Note: Index will automatically be created for "unique" values, so no
            # need to manually create them
            c.execute('''CREATE TABLE TvShows (id integer primary key, name text unique, dbid integer unique, level integer)''')
            c.execute('''CREATE TABLE Movies (id integer primary key, name text unique, dbid integer unique, level integer)''')
            c.execute('''CREATE TABLE MovieSets (id integer primary key, name text unique, dbid integer unique, level integer)''')

            # Save (commit) the changes
            conn.commit()

            # We can also close the connection if we are done with it.
            # Just be sure any changes have been committed or they will be lost.
            conn.close()
# No Need to check the version, as there is only one version
#         else:
#             # Check if this is an upgrade
#             conn = sqlite3.connect(self.databasefile)
#             c = conn.cursor()
#             c.execute('SELECT * FROM version')
#             log("PinSentryDB: Current version number in DB is: %s" % c.fetchone()[0])
#             conn.close()

    # Get a connection to the current database
    def getConnection(self):
        conn = sqlite3.connect(self.databasefile)
        conn.text_factory = str
        return conn

    # Set the security value for a given TvShow
    def setTvShowSecurityLevel(self, showName, dbid, level=1):
        ret = -1
        if level > 0:
            ret = self._insertOrUpdate("TvShows", showName, dbid, level)
        else:
            self._deleteSecurityDetails("TvShows", showName)
        return ret

    # Set the security value for a given Movie
    def setMovieSecurityLevel(self, movieName, dbid, level=1):
        ret = -1
        if level > 0:
            ret = self._insertOrUpdate("Movies", movieName, dbid, level)
        else:
            self._deleteSecurityDetails("Movies", movieName)
        return ret

    # Set the security value for a given Movie Set
    def setMovieSetSecurityLevel(self, movieSetName, dbid, level=1):
        ret = -1
        if level > 0:
            ret = self._insertOrUpdate("MovieSets", movieSetName, dbid, level)
        else:
            self._deleteSecurityDetails("MovieSets", movieSetName)
        return ret

    # Insert or replace an entry in the database
    def _insertOrUpdate(self, tableName, name, dbid, level=1):
        log("PinSentryDB: Adding %s %s (id:%d) at level %d" % (tableName, name, dbid, level))

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()

        insertData = (name, dbid, level)
        cmd = 'INSERT OR REPLACE INTO %s (name, dbid, level) VALUES (?,?,?)' % tableName
        c.execute(cmd, insertData)

        rowId = c.lastrowid
        conn.commit()
        conn.close()

        return rowId

    # Delete an entry from the database
    def _deleteSecurityDetails(self, tableName, name):
        log("PinSentryDB: delete %s for %s" % (tableName, name))

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Delete any existing data from the database
        cmd = 'delete FROM %s where name = ?' % tableName
        c.execute(cmd, (name,))
        conn.commit()

        log("PinSentryDB: delete for %s removed %d rows" % (name, conn.total_changes))

        conn.close()

    # Get the security value for a given TvShow
    def getTvShowSecurityLevel(self, showName):
        return self._getSecurityLevel("TvShows", showName)

    # Get the security value for a given Movie
    def getMovieSecurityLevel(self, movieName):
        return self._getSecurityLevel("Movies", movieName)

    # Get the security value for a given Movie Set
    def getMovieSetSecurityLevel(self, movieSetName):
        return self._getSecurityLevel("MovieSets", movieSetName)

    # Select the security entry from the database
    def _getSecurityLevel(self, tableName, name):
        log("PinSentryDB: select %s for %s" % (tableName, name))

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        cmd = 'SELECT * FROM %s where name = ?' % tableName
        c.execute(cmd, (name,))
        row = c.fetchone()

        securityLevel = 0
        if row is None:
            log("PinSentryDB: No entry found in the database for %s" % name)
            # Not stored in the database so return 0 for no pin required
        else:
            log("PinSentryDB: Database info: %s" % str(row))

            # Return will contain
            # row[0] - Unique Index in the DB
            # row[1] - Name of the TvShow
            # row[2] - Security Level
            securityLevel = row[2]

        conn.close()
        return securityLevel

    # Select all TvShow entries from the database
    def getAllTvShowsSecurity(self):
        return self._getAllSecurityDetails("TvShows")

    # Select all Movie entries from the database
    def getAllMoviesSecurity(self):
        return self._getAllSecurityDetails("Movies")

    # Select all Movie Set entries from the database
    def getAllMovieSetsSecurity(self):
        return self._getAllSecurityDetails("MovieSets")

    # Select all security details from a given table in the database
    def _getAllSecurityDetails(self, tableName):
        log("PinSentryDB: select all %s" % tableName)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        cmd = 'SELECT * FROM %s' % tableName
        c.execute(cmd)
        rows = c.fetchall()

        resultDict = {}
        if rows is None:
            # No data
            log("PinSentryDB: No entry found in TvShow database")
        else:
            log("PinSentryDB: Database info: %s" % str(rows))

            # Return will contain
            # row[0] - Unique Index in the DB
            # row[1] - Name of the TvShow/Movie/MusicVideo
            # row[2] - Security Level
            for row in rows:
                name = row[1]
                resultDict[name] = row[2]

        conn.close()
        return resultDict
