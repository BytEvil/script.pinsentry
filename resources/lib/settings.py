# -*- coding: utf-8 -*-
import os
import hashlib
import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__addonid__ = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (__addon__.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join(dir, file):
    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)


##############################
# Stores Various Settings
##############################
class Settings():
    INVALID_PIN_NOTIFICATION_POPUP = 0
    INVALID_PIN_NOTIFICATION_DIALOG = 1
    INVALID_PIN_NOTIFICATION_NONE = 2

    @staticmethod
    def setPinValue(newPin):
        # Before setting the pin, encrypt it
        encryptedPin = Settings.encryptPin(newPin)
        __addon__.setSetting("pinValue", encryptedPin)
        if len(newPin) > 0:
            # This is an internal fudge so that we can display a warning if the pin is not set
            __addon__.setSetting("pinValueSet", "true")
        else:
            __addon__.setSetting("pinValueSet", "false")

    @staticmethod
    def encryptPin(rawValue):
        return hashlib.sha256(rawValue).hexdigest()

    @staticmethod
    def isPinSet():
        pinValue = __addon__.getSetting("pinValue")
        if pinValue not in [None, ""]:
            return True
        return False

    @staticmethod
    def getPinLength():
        return int(float(__addon__.getSetting('pinLength')))

    @staticmethod
    def isPinCorrect(inputPin):
        # First encrypt the pin that has been passed in
        inputPinEncrypt = Settings.encryptPin(inputPin)
        if inputPinEncrypt == __addon__.getSetting('pinValue'):
            return True
        return False

    @staticmethod
    def getInvalidPinNotificationType():
        return int(float(__addon__.getSetting('invalidPinNotificationType')))
