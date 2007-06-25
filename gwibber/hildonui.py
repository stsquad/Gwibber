#!/usr/bin/env python

"""

Gwibber Client
SegPhault (Ryan Paul) - 06/24/2007

Experimental Hildon Port

"""

import sys, gtk, gtk.glade, hildon, gwui, dbus, time
from service import twitter, jaiku, facebook

TWITTER_USERNAME = "segphault"
TWITTER_PASSWORD = ""
TWITTER_UPDATE_INTERVAL = 5

class GwibberClient(hildon.Program):
  def __init__(self, ui_file):
    hildon.Program.__init__(self)
    self.window = hildon.Window()
    self.window.set_title("Gwibber")
    self.window.connect("destroy", gtk.main_quit)

    menu = gtk.Menu()

    self.glade = gtk.glade.XML(ui_file)
    for child in self.glade.get_widget("menubar").get_children():
      child.reparent(menu)

    self.window.set_menu(menu)
    
    btnRefresh = gtk.ToolButton("gtk-refresh")
    btnPrefs = gtk.ToolButton("gtk-preferences")
    btnSend = gtk.ToolButton(None, "Send")

    txtInput = gtk.Entry()
    txtInputItem = gtk.ToolItem()
    txtInputItem.set_expand(True)
    txtInputItem.add(txtInput)

    toolbar = gtk.Toolbar()
    toolbar.insert(btnRefresh, -1)
    toolbar.insert(btnPrefs, -1)
    toolbar.insert(txtInputItem, -1)
    toolbar.insert(btnSend, -1)
    
    self.container = gtk.ScrolledWindow()
    self.container.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    
    vb = gtk.VBox()
    vb.pack_start(self.container)
    self.window.add_toolbar(toolbar)
    # vb.pack_start(toolbar, False, False)

    self.window.add(vb)
    self.window.show_all()

    self.updater = gwui.UpdateManager(twitter.Client(
      TWITTER_USERNAME, TWITTER_PASSWORD))

    self.updater.connect("twitter-update-finished", self.on_update)
    self.updater.connect("twitter-update-failed", self.on_error)
    self.updater.connect("twitter-update-change", self.on_change)

    self.updater.set_interval(TWITTER_UPDATE_INTERVAL * (1000 * 60))
    # self.updater.update()

  def on_change(self, updater, new_messages):
    print "New messgaes received"

  def on_update(self, updater, data):
    status = gwui.StatusList(data)
    status.show_all()
    if self.container.get_child():
      self.container.remove(self.container.get_child())
    self.container.add_with_viewport(status)

  def on_error(self, *a):
    import sys
    print sys.exc_info()
