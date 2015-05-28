# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings

from numberpad import NumberPad
from database import PinSentryDB


# Feature Options:
# Different Pins for different priorities (one a subset of the next)
# Setting for a Group/Movie Set
# Settings for given Video Plugins
# Option to have the pin requested during navigation (i.e. selecting a TV Show)
# Restrictions based on certificate/classification
# Option to have different passwords without the numbers (Remote with no numbers?)
# Support DVD Directory Structures

# ClLass to store and manage the pin Cache
class PinCache():
    pinLevelCached = 0

    @staticmethod
    def clearPinCached():
        log("PinCache: Clearing Cached pin that was at level %d" % PinCache.pinLevelCached)
        PinCache.pinLevelCached = 0

    @staticmethod
    def setCachedPinLevel(level):
        # Check if the pin cache is enabled, if it is not then the cache level will
        # always remain at 0 (i.e. always need to enter the pin)
        if Settings.isPinCachingEnabled():
            if PinCache.pinLevelCached < level:
                log("PinCache: Updating cached pin level to %d" % level)
                PinCache.pinLevelCached = level

    @staticmethod
    def getCachedPinLevel():
        return PinCache.pinLevelCached


# Class to detect shen something in the system has changed
class PinSentryMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        log("PinSentryMonitor: Notification of settings change received")
        Settings.reloadSettings()

    def onScreensaverActivated(self):
        log("PinSentryMonitor: Screensaver started, clearing cached pin")
        PinCache.clearPinCached()


# Our Monitor class so we can find out when a video file has been selected to play
class PinSentryPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        log("PinSentry: Notification that something started playing")

        # Only interested if it is playing videos, as they will not be TvTunes
        if not self.isPlayingVideo():
            return

        # Ignore screen saver videos
        if xbmcgui.Window(10000).getProperty("VideoScreensaverRunning"):
            log("Detected VideoScreensaver playing")
            return

        # Check if the Pin is set, as no point prompting if it is not
        if (not Settings.isPinSet()) or (not Settings.isPinActive()):
            return

        # Get the information for what is currently playing
        # http://kodi.wiki/view/InfoLabels#Video_player
        tvshowtitle = xbmc.getInfoLabel("VideoPlayer.TVShowTitle")
        dbid = xbmc.getInfoLabel("ListItem.DBID")
        cert = xbmc.getInfoLabel("VideoPlayer.mpaa")
        listmpaa = xbmc.getInfoLabel("ListItem.Mpaa")

        log("*** ROB ***: ListItem.DBID: %s" % str(dbid))
        log("*** ROB ***: VideoPlayer.mpaa: %s" % str(cert))
        log("*** ROB ***: ListItem.Mpaa: %s" % str(listmpaa))

        securityLevel = 0
        # If it is a TvShow, then check to see if it is enabled for this one
        if tvshowtitle not in [None, ""]:
            log("PinSentry: VideoPlayer.TVShowTitle: %s" % tvshowtitle)
            pinDB = PinSentryDB()
            securityLevel = pinDB.getTvShowSecurityLevel(tvshowtitle)
            if securityLevel < 1:
                log("PinSentry: No security enabled for %s" % tvshowtitle)
                return
        else:
            # Not a TvShow, so check for the Movie Title
            title = xbmc.getInfoLabel("VideoPlayer.Title")
            if title not in [None, ""]:
                log("PinSentry: VideoPlayer.Title: %s" % title)
                pinDB = PinSentryDB()
                securityLevel = pinDB.getMovieSecurityLevel(title)
                if securityLevel < 1:
                    log("PinSentry: No security enabled for %s" % title)
                    return
            else:
                # Not a TvShow or Movie - so allow the user to continue
                # without entering a pin code
                log("PinSentry: No security enabled, no title available")
                return

        # Check if we have already cached the pin number and at which level
        if PinCache.getCachedPinLevel() >= securityLevel:
            log("PinSentry: Already cached pin at level %d, allowing access" % PinCache.getCachedPinLevel())
            return

        # Pause the video so that we can prompt for the Pin to be entered
        self.pause()
        log("Pausing video to check if OK to play")

        numberpad = NumberPad.createNumberPad()
        numberpad.doModal()

        # Get the code that the user entered
        enteredPin = numberpad.getPin()
        del numberpad

        # Check to see if the pin entered is correct
        if Settings.isPinCorrect(enteredPin):
            log("OK To Continue")
            # Pausing again will start the video playing again
            self.pause()

            # Check if we are allowed to cache the pin level
            PinCache.setCachedPinLevel(securityLevel)
        else:
            log("Do not want to continue")
            self.stop()
            # Invalid Key Notification: Dialog, Popup Notification, None
            notifType = Settings.getInvalidPinNotificationType()
            if notifType == Settings.INVALID_PIN_NOTIFICATION_POPUP:
                cmd = 'XBMC.Notification("{0}", "{1}", 5, "{2}")'.format(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'), __icon__)
                xbmc.executebuiltin(cmd)
            elif notifType == Settings.INVALID_PIN_NOTIFICATION_DIALOG:
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'))
            # Remaining option is to not show any error


##################################
# Main of the PinSentry Service
##################################
if __name__ == '__main__':
    log("Starting Pin Sentry Service")

    playerMonitor = PinSentryPlayer()
    systemMonitor = PinSentryMonitor()

    while (not xbmc.abortRequested):
        xbmc.sleep(100)

    log("Stopping Pin Sentry Service")
    del playerMonitor
    del systemMonitor
