# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__icon__ = __addon__.getAddonInfo('icon')
__fanart__ = __addon__.getAddonInfo('fanart')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
# from settings import Settings
from settings import log
from database import PinSentryDB


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    MOVIES = 'movies'
    TVSHOWS = 'tvshows'
    MOVIESETS = 'sets'

    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # Display the default list of items in the root menu
    def showRootMenu(self):
        # Movies
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MOVIES})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32201), iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # TV Shows
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.TVSHOWS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32202), iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # TV Shows
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MOVIESETS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32203), iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Show the list of videos in a given set
    def showFolder(self, foldername):
        # Check for the special case of manually defined folders
        if foldername == MenuNavigator.TVSHOWS:
            self._setVideoList('GetTVShows', MenuNavigator.TVSHOWS, 'tvshowid')
        elif foldername == MenuNavigator.MOVIES:
            self._setVideoList('GetMovies', MenuNavigator.MOVIES, 'movieid')
        elif foldername == MenuNavigator.MOVIESETS:
            self._setVideoList('GetMovieSets', MenuNavigator.MOVIESETS, 'setid')

    # Produce the list of videos and flag which ones with securoty details
    def _setVideoList(self, jsonGet, target, dbid):
        videoItems = self._getVideos(jsonGet, target, dbid)
        # Now add the security details to the video list
        videoItems = self._addSecurityFlagToVideos(target, videoItems)

        for videoItem in videoItems:
            # Create the list-item for this video
            li = xbmcgui.ListItem(videoItem['title'], iconImage=videoItem['thumbnail'])

            # Remove the default context menu
            li.addContextMenuItems([], replaceItems=True)
            # Get the title of the video owning the extras
            title = videoItem['title']
            try:
                title = videoItem['title'].encode("utf-8")
            except:
                log("setVideoList: Failed to encode title %s" % title)

            # Record what the new security level will be is selected
            newSecurityLevel = 1
            # Add a tick if security is set
            if videoItem['securityLevel'] > 0:
                li.setInfo('video', {'PlayCount': 1})
                # Next time the item is selected, it will be disabled
                newSecurityLevel = 0

            url = self._build_url({'mode': 'setsecurity', 'level': newSecurityLevel, 'type': target, 'title': title, 'id': videoItem['dbid']})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Do a lookup in the database for the given type of videos
    def _getVideos(self, jsonGet, target, dbid):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": {"properties": ["title", "thumbnail", "fanart"], "sort": { "method": "title" } }, "id": 1}' % jsonGet)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        videolist = []
        if ("result" in json_response) and (target in json_response['result']):
            for item in json_response['result'][target]:
                videoItem = {}
                videoItem['title'] = item['title']

                if item['thumbnail'] is None:
                    item['thumbnail'] = 'DefaultFolder.png'
                else:
                    videoItem['thumbnail'] = item['thumbnail']
                videoItem['fanart'] = item['fanart']

                videoItem['dbid'] = item[dbid]

                videolist.append(videoItem)
        return videolist

    # Adds the current security details to the video items
    def _addSecurityFlagToVideos(self, type, videoItems):
        # Make sure we have some items to append the details to
        if len(videoItems) < 1:
            return videoItems

        # Make the call to the DB to get all the specific security settings
        pinDB = PinSentryDB()

        securityDetails = {}
        if type == MenuNavigator.TVSHOWS:
            securityDetails = pinDB.getAllTvShowsSecurity()
        elif type == MenuNavigator.MOVIES:
            securityDetails = pinDB.getAllMoviesSecurity()
        elif type == MenuNavigator.MOVIESETS:
            securityDetails = pinDB.getAllMovieSetsSecurity()

        for videoItem in videoItems:
            # Default security to 0 (Not Set)
            securityLevel = 0
            if videoItem['title'] in securityDetails:
                title = videoItem['title']
                securityLevel = securityDetails[title]
                log("%s has security level %d" % (title, securityLevel))

            videoItem['securityLevel'] = securityLevel

        del pinDB
        return videoItems

    # Set the security value for a given video
    def setSecurity(self, type, title, id, level):
        log("Setting security for (id:%d) %s" % (id, title))
        if title not in [None, ""]:
            pinDB = PinSentryDB()
            if type == MenuNavigator.TVSHOWS:
                # Set the security level for this title, setting it to zero
                # will result in the entry being removed from the database
                # as the default for an item is unset
                pinDB.setTvShowSecurityLevel(title, id, level)
            elif type == MenuNavigator.MOVIES:
                pinDB.setMovieSecurityLevel(title, id, level)
            elif type == MenuNavigator.MOVIESETS:
                pinDB.setMovieSetSecurityLevel(title, id, level)
                # As well as setting the security on the Movie set, we need
                # to also set it on each movie in the Movie Set
                self._setSecurityOnMoviesInMovieSets(id, level)
            del pinDB

        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    def _setSecurityOnMoviesInMovieSets(self, setid, level):
        log("Setting security for movies in movie set %d" % setid)
        # Get all the movies in the movie set
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSetDetails", "params": { "setid": %d, "properties": ["title"] }, "id": 1}' % setid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        if ("result" in json_response) and ('setdetails' in json_response['result']):
            if 'movies' in json_response['result']['setdetails']:
                for item in json_response['result']['setdetails']['movies']:
                    # Now set the security on the movies in the set
                    self.setSecurity(MenuNavigator.MOVIES, item['label'], item['movieid'], level)
        return

################################
# Main of the PinSentry Plugin
################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("PinSentryPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("PinSentryPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.showRootMenu()
        del menuNav

    elif mode[0] == 'folder':
        log("PinSentryPlugin: Mode is FOLDER")

        # Get the actual folder that was navigated to
        foldername = args.get('foldername', None)

        if (foldername is not None) and (len(foldername) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showFolder(foldername[0])
            del menuNav

    elif mode[0] == 'setsecurity':
        log("PinSentryPlugin: Mode is SET SECURITY")

        # Get the actual details of the selection
        type = args.get('type', None)
        title = args.get('title', None)
        level = args.get('level', None)
        id = args.get('id', None)

        if (type is not None) and (len(type) > 0):
            log("PinSentryPlugin: Type to set security for %s" % type[0])
            secTitle = ""
            if (title is not None) and (len(title) > 0):
                secTitle = title[0]
            secLevel = 0
            if (level is not None) and (len(level) > 0):
                secLevel = int(level[0])
            dbid = 0
            if (id is not None) and (len(id) > 0):
                dbid = int(id[0])

            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.setSecurity(type[0], secTitle, dbid, secLevel)
            del menuNav
