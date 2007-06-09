#!/usr/bin/env python

import dbus, dbus.glib, dbus.decorators

bus = dbus.SessionBus()
obj = bus.get_object("im.pidgin.purple.PurpleService", "/im/pidgin/purple/PurpleObject")
purple = dbus.Interface(obj, "im.pidgin.purple.PurpleInterface")

def update_status(msg, kind = purple.PurpleSavedstatusGetType(purple.PurpleSavedstatusGetDefault()), title = "Gwibber"):
  if not purple.PurpleSavedstatusFind(title):
    purple.PurpleSavedstatusNew(title, kind)
  
  status = purple.PurpleSavedstatusFind(title)
  purple.PurpleSavedstatusSetMessage(status, msg)
  purple.PurpleSavedstatusSetType(status, kind)
  purple.PurpleSavedstatusActivate(status)
