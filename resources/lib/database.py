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

            # Create a table that will be used to store each TvShow and its access level
            # The "id" will be auto-generated as the primary key
            # Note: Index will automatically be created for "unique" values, so no
            # need to manually create them
            c.execute('''CREATE TABLE TvShows (id integer primary key, name text unique, level integer)''')
            c.execute('''CREATE TABLE Movies (id integer primary key, name text unique, level integer)''')
            c.execute('''CREATE TABLE MusicVideo (id integer primary key, name text unique, level integer)''')

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

    def setTvShowSecurityLevel(self, showName, level=1):
        return self.insertOrUpdateTvShow(showName, level)

    # Insert or replace an entry in the database
    def insertOrUpdateTvShow(self, showName, level=1):
        log("PinSentryDB: Adding TvShow %s at level %d" % (showName, level))

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()

        insertData = (showName, level)
        c.execute('''INSERT OR REPLACE INTO TvShows(name, level) VALUES (?,?)''', insertData)

        rowId = c.lastrowid
        conn.commit()
        conn.close()

        return rowId

    # Get the security value for a given TvShow
    def getTvShowSecurityLevel(self, showName):
        return self._getSecurityLevel("TvShows", showName)

    # Get the security value for a given Movie
    def getMovieSecurityLevel(self, movieName):
        return self._getSecurityLevel("Movies", movieName)

    # Get the security value for a given Music Video
    def getMusicVideoSecurityLevel(self, musicVideoName):
        return self._getSecurityLevel("MusicVideo", musicVideoName)

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
    def selectTvShows(self):
        log("PinSentryDB: select all TvShow")

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Select any existing data from the database
        c.execute('SELECT * FROM TvShows')
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

    # Delete an entry from the database
    def deleteTvShow(self, showName):
        log("PinSentryDB: delete TvShow for %s" % showName)

        # Get a connection to the DB
        conn = self.getConnection()
        c = conn.cursor()
        # Delete any existing data from the database
        c.execute('delete FROM TvShows where name = ?', (showName,))
        conn.commit()

        log("PinSentryDB: delete for %s removed %d rows" % (showName, conn.total_changes))

        conn.close()
