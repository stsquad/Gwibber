#!/usr/bin/env python

"""

Gwibber Client
SegPhault (Ryan Paul) - 06/24/2007

Experimental Hildon Port

"""

import hildon, gtk, gtk.glade
from client import GwibberClient

class GwibberClient(hildon.Program, GwibberClient):
  def __init__(self, ui_file):
    hildon.Program.__init__(self)
    self.glade = gtk.glade.XML(ui_file)
    self.statusbar = self.glade.get_widget("statusbar")
    self.glade.get_widget("windowGwibberClient").hide()

    self.window = hildon.Window()
    self.window.set_title("Gwibber")
    self.window.connect("destroy", gtk.main_quit)
    
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
    self.window.add_toolbar(toolbar)
    self.window.add(self.container)

    btnPrefs.connect("clicked", lambda w: self.glade.get_widget("windowPreferences").run())
    btnSend.connect("clicked", self.on_input_activate)
    btnRefresh.connect("clicked", lambda w: self.updater.update())

    self.setup_signals()
    self.setup_gconf()
    self.setup_updater()
    self.sync_gconf_and_menu()
    self.sync_timeline_widgets()
    self.sync_gconf_and_prefs()

    menu = gtk.Menu()
    for child in self.glade.get_widget("menubar").get_children():
      child.reparent(menu)
    self.window.set_menu(menu)

    self.window.show_all()

    widgets_to_hide = [
      "menu_tweet_notify", "menu_tray_enabled", "status_separator1", 
      "menu_toggle_toolbar", "menu_toggle_statusbar", "menu_toggle_inputbox",
      "vbox3", "label27"]

    for w in widgets_to_hide:
      i = self.glade.get_widget(w)
      if i: i.hide()
