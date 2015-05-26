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


# Feature Options:
# Time Span for when a pin is required
# Different Pins for different priorities (one a subset of the next)
# Setting for each Video
# Setting for each TvShow
# Setting for a Group/Movie Set
# Settings for given Plugins
# Restrictions based on certificate/classification
# Remember the pin after it has been entered once (Forget after screensaver starts)
# Option to have different passwords without the numbers (Remote with no numbers?)


# Our Monitor class so we can find out when a video file has been selected to play
class PinSentryPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        # Only interested if it is playing videos, as they will not be TvTunes
        if not self.isPlayingVideo():
            return

        # Ignore screen saver videos
        if xbmcgui.Window(10000).getProperty("VideoScreensaverRunning"):
            log("Detected VideoScreensaver playing")
            return

        # Check if the Pin is set, as no point prompting if it is not
        if not Settings.isPinSet():
            return

        # Get the information for what is currently playing
        # http://kodi.wiki/view/InfoLabels#Video_player
        tvshowtitle = xbmc.getInfoLabel("VideoPlayer.TVShowTitle")
        dbid = xbmc.getInfoLabel("ListItem.DBID")
        cert = xbmc.getInfoLabel("VideoPlayer.mpaa")
        listmpaa = xbmc.getInfoLabel("ListItem.Mpaa")

        log("*** ROB ***: VideoPlayer.TVShowTitle: %s" % str(tvshowtitle))
        log("*** ROB ***: ListItem.DBID: %s" % str(dbid))
        log("*** ROB ***: VideoPlayer.mpaa: %s" % str(cert))
        log("*** ROB ***: ListItem.Mpaa: %s" % str(listmpaa))

        log("Pausing video to check if OK to play")
        self.pause()

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

    while (not xbmc.abortRequested):
        xbmc.sleep(100)

    log("Stopping Pin Sentry Service")
    del playerMonitor
