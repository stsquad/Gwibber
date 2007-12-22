#!/usr/bin/env python

import dbus, gobject, dbus.glib

def service_is_running(name):
  return name in dbus.Interface(dbus.SessionBus().get_object(
    "org.freedesktop.DBus", "/org/freedesktop/DBus"), "org.freedesktop.DBus").ListNames()
