#!/usr/bin/env python

import dbus, gobject, dbus.glib, os

try:
  notifier = dbus.Interface(dbus.SessionBus().get_object(
    "org.freedesktop.Notifications", "/org/freedesktop/Notifications"),
    "org.freedesktop.Notifications")

  def notify(title, text, icon = None, actions = [], timer = 9000):
    return notifier.Notify("Gwibber", 0, icon, title, text, actions, {}, timer)

  can_notify = True
except: can_notify = False

try:
  import sexy
  SPELLCHECK_ENABLED = True
except:
  SPELLCHECK_ENABLED = False

try:
  import gnome
  def load_url(url): gnome.url_show(url)
except:
  def load_url(url): os.system("xdg-open %s" % url)

def service_is_running(name):
  return name in dbus.Interface(dbus.SessionBus().get_object(
    "org.freedesktop.DBus", "/org/freedesktop/DBus"),
      "org.freedesktop.DBus").ListNames()

def create_tomboy_note(text, display = True):
  obj = dbus.SessionBus().get_object("org.gnome.Tomboy", "/org/gnome/Tomboy/RemoteControl")
  tomboy = dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")
  
  n = tomboy.CreateNote()
  tomboy.SetNoteContents(n, text)
  if display: tomboy.DisplayNote(n)
