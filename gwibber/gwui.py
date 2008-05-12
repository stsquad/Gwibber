#!/usr/bin/env python

"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import gtk, pango, gobject, gintegration, config
import urllib2, base64, time, datetime, os, re

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5
LINK_PARSE = re.compile("(https?://[^ )\n]+)")
IMG_CACHE_DIR = "%s/.gwibber/imgcache" % os.path.expanduser("~")

class StatusMessage:
  pass

def generate_time_string(t):
  d = datetime.datetime(*time.gmtime()[0:6]) - t

  if d.seconds < 60: return "%d seconds ago" % d.seconds
  elif d.seconds < (60 * 60):  return "%d minutes ago" % (d.seconds / 60)
  elif d.seconds < (60 * 60 * 2): return "1 hour ago"
  elif d.days < 1: return "%d hours ago" % (d.seconds / 60 / 60)
  elif d.days == 1: return "1 day ago"
  elif d.days > 0: return "%d days ago" % d.days
  else: return "BUG: %s" % str(d)

def linkify(t):
  return LINK_PARSE.sub('<a href="\\1">\\1</a>', t)

def image_cache(url, cache_dir = IMG_CACHE_DIR):
  if not os.path.exists(cache_dir): os.makedirs(cache_dir)
  img_path = os.path.join(cache_dir, base64.encodestring(url)[:-1]).replace("\n","")

  if not os.path.exists(img_path):
    output = open(img_path, "w+")
    output.write(urllib2.urlopen(url).read())
    output.close()

  return img_path

def props(w, **args):
  for k,v in args.items(): w.set_property(k,v)
  return w

class ConfigFrame(gtk.Frame):
  def __init__(self, caption=""):
    gtk.Frame.__init__(self)
    self.set_shadow_type(gtk.SHADOW_NONE)
    self.set_property("label-xalign", 0)
    self.label = gtk.Label()
    self.label.set_markup("<b>%s</b>" % caption)
    self.set_label_widget(self.label)
    self.alignment = gtk.Alignment(0.50, 0.50, 1, 1)
    self.alignment.set_padding(5, 0, 12, 0)
    gtk.Frame.add(self, self.alignment)

  def add(self, w): self.alignment.add(w)

class ConfigPanel(gtk.VBox):
  def __init__(self, acct, prefs):
    self.account = acct
    self.preferences = prefs

  def build_ui(self):
    ui = gtk.VBox(spacing=15)
    ui.pack_start(self.ui_account_info())
    ui.pack_start(self.ui_account_status())
    ui.pack_start(self.ui_appearance())
    return self.customize_ui(ui)

  def customize_ui(self, ui):
    return ui

  def ui_account_info(self):
    f = ConfigFrame("Account Information")
    t = gtk.Table()
    t.set_col_spacings(5)
    t.set_row_spacings(5)

    p = gtk.Entry()
    p.set_visibility(False)
    self.account.bind(p, "password")

    t.attach(gtk.Label("Username:"), 0, 1, 0, 1, gtk.SHRINK)
    t.attach(self.account.bind(gtk.Entry(), "username"), 1, 2, 0, 1)
    t.attach(gtk.Label("Password:"), 0, 1, 1, 2, gtk.SHRINK)
    t.attach(p, 1, 2, 1, 2)
    f.add(t)
    return f

  def ui_account_status(self):
    f = ConfigFrame("Account Status")
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.account.bind(gtk.CheckButton("Receive Messages"), "receive_enabled"))
    vb.pack_start(self.account.bind(gtk.CheckButton("Send Messages"), "send_enabled"))
    f.add(vb)
    return f

  def ui_appearance(self):
    f = ConfigFrame("Appearance")
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.account.bind(gtk.ColorButton(), "message_color", default = "#8e8eb1b1dcdc"))
    f.add(vb)
    return f
