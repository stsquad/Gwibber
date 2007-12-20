#!/usr/bin/env python

"""

Gwibber Client v0.01
SegPhault (Ryan Paul) - 05/26/2007

TODO:

  setup default value for timeline_display

"""

import sys, gtk, gtk.glade, gwui, gaw, dbus, time
from service import twitter, jaiku, facebook, pidgin



try:
  import gconf
except:
  from gnome import gconf

try:
  import pynotify
except:
  class pynotify:
    @classmethod
    def init(self, app):
      return False

try:
  import sexy
  SPELLCHECK_ENABLED = False #True
except:
  SPELLCHECK_ENABLED = False


GCONF_DIR = "/apps/gwibber2/preferences"

class GwibberClient:
  def __init__(self, ui_file):
    self.glade = gtk.glade.XML(ui_file)

    self.container = self.glade.get_widget("container")
    self.statusbar = self.glade.get_widget("statusbar")

    if SPELLCHECK_ENABLED:
      input = sexy.SpellEntry()
      input.set_max_length(self.glade.get_widget("input").get_max_length())
      input.connect("activate", self.on_input_activate)
      input.connect("changed", self.on_input_change)
      input.show_all()
      
      inputbox = self.glade.get_widget("inputbox")
      inputbox.remove(self.glade.get_widget("input"))
      inputbox.pack_start(input)

    self.setup_signals()
    self.setup_gconf()
    self.setup_updater()
    self.sync_gconf_and_menu()
    self.sync_timeline_widgets()
    self.sync_gconf_and_prefs()
    self.setup_tray_icon()
    self.updater.update()

  def setup_signals(self):
    self.glade.signal_autoconnect({
      "on_quit": gtk.main_quit,
      "on_refresh": lambda w: self.updater.update(),
      "on_hide_dialog": lambda w,a: w.hide(),
      "on_preferences": lambda w: self.glade.get_widget("windowPreferences").run(),
      "on_about": lambda w: self.glade.get_widget("windowAbout").run(),
      "on_input_activate": self.on_input_activate,
      "on_input_change": self.on_input_change,
      "on_timeline_change": self.on_timeline_change})

  def setup_gconf(self):
    self.gconf = gconf.client_get_default()
    self.gconf.add_dir(GCONF_DIR, gconf.CLIENT_PRELOAD_NONE)
    self.gconf.notify_add(GCONF_DIR + "/timeline_display", self.sync_timeline_widgets)
    self.gconf.notify_add(GCONF_DIR + "/twitter_username", self.sync_twitter_login)
    self.gconf.notify_add(GCONF_DIR + "/twitter_password", self.sync_twitter_login)

  def sync_twitter_login(self, *args):
    self.updater.twitter = twitter.Client(
      self.gconf.get_string(GCONF_DIR + "/twitter_username"),
      self.gconf.get_string(GCONF_DIR + "/twitter_password"))

  def setup_updater(self):
    if self.gconf.get_string(GCONF_DIR + "/twitter_username"):
      self.updater = gwui.UpdateManager(twitter.Client(
        self.gconf.get_string(GCONF_DIR + "/twitter_username"),
        self.gconf.get_string(GCONF_DIR + "/twitter_password")))
    else:
      self.updater = gwui.UpdateManager(None)
    self.updater.connect("twitter-update-finished", self.on_update)
    self.updater.connect("twitter-update-failed", self.on_error)
    self.updater.connect("twitter-update-change", self.on_change)
    self.updater.set_interval(self.gconf.get_int(
      GCONF_DIR + "/twitter_update_interval") * (1000 * 60))
    self.container.show_all()

  def setup_tray_icon(self):
    self.status = gtk.status_icon_new_from_icon_name("gwibber")
    self.status.connect("activate", self.on_toggle_window_visibility)
    self.status.connect("popup-menu", self.on_tray_popup, self.glade.get_widget("menu_tray"))
    self.gconf.notify_add(GCONF_DIR + "/tray_enabled", self.on_toggle_tray_visibility)

  def on_tray_popup(self, widget, button, time, menu):
    if button == 3:
      menu.show_all()
      menu.popup(None, None, None, 3, time)

  def on_toggle_tray_visibility(self, client, id, entry, data):
    self.status.set_visible(entry.value.get_bool())
 
  def submit_message(self, text):
    for s in ["twitter", "jaiku", "facebook"]:
      if self.gconf.get_bool(GCONF_DIR + "/%s_enabled" % s):
        sys.modules["gwibber.service.%s" % s].Client(
          self.gconf.get_string(GCONF_DIR + "/%s_username" % s),
          self.gconf.get_string(GCONF_DIR + "/%s_password" % s)).update_status(text)

    if self.gconf.get_bool(GCONF_DIR + "/pidgin_enabled"):
      pidgin.update_status(text)

  def on_toggle_window_visibility(self, widget):
    window = self.glade.get_widget("windowGwibberClient")
    if window.get_property("visible"): window.hide()
    else: window.show_all()

  def on_input_activate(self, widget):
    if widget.get_text().strip():
      self.submit_message(widget.get_text())
      widget.set_text("")

  def on_input_change(self, widget):
    self.statusbar.pop(1)
    if len(widget.get_text()) > 0:
      self.statusbar.push(1, 
        "Characters remaining: %s" % (widget.get_max_length() - len(widget.get_text())))

  def sync_gconf_and_menu(self):
    for x in ["statusbar", "toolbar", "inputbox"]:
      gaw.data_toggle_button(self.glade.get_widget("menu_toggle_%s" % x), GCONF_DIR + "/show_%s" % x,
        self.glade.get_widget("menu_toggle_%s" % x).set_active(self.gconf.get_bool(GCONF_DIR + "/show_%s" % x)))
      self.glade.get_widget(x).set_property("visible", self.gconf.get_bool(GCONF_DIR + "/show_%s" % x))
      self.gconf.notify_add(GCONF_DIR + "/show_%s" % x, self.on_gconf_toggle_widget)
  
  def on_gconf_toggle_widget(self, client, id, entry, data):
    self.glade.get_widget(entry.get_key().split("_")[-1]).set_property("visible", entry.value.get_bool())

  def sync_gconf_and_prefs(self):
    settings = [
      "txt_twitter_username", "txt_twitter_password", "toggle_twitter_enabled", "menu_twitter_enabled", "popupmenu_twitter_enabled",
      "txt_jaiku_username", "txt_jaiku_password", "toggle_jaiku_enabled", "menu_jaiku_enabled", "popupmenu_jaiku_enabled",
      "txt_facebook_username", "txt_facebook_password", "toggle_facebook_enabled", "menu_facebook_enabled", "popupmenu_facebook_enabled",
      "check_tweet_notify", "menu_tweet_notify", "popupmenu_tweet_notify", "spin_twitter_update_interval",
      "toggle_pidgin_enabled", "menu_pidgin_enabled", "popupmenu_pidgin_enabled", "menu_tray_enabled", "check_tray_enabled"]
    
    for w in settings:
      gfn = {"txt": gaw.data_entry, "check": gaw.data_toggle_button, "popupmenu": gaw.data_toggle_button,
             "spin": gaw.data_spin_button, "toggle": gaw.data_toggle_button,
             "menu": gaw.data_toggle_button}[w.split("_")[0]]
      gfn(self.glade.get_widget(w), GCONF_DIR + "/%s" % "_".join(w.split("_")[1:]))

  def sync_timeline_widgets(self, *args):
    self.sync = True
    self.updater.timeline = self.gconf.get_string(GCONF_DIR + "/timeline_display")
    if not self.updater.timeline:
      self.updater.timeline = "friends"
      self.gconf.set_string(GCONF_DIR + "/timeline_display", "friends")
    self.glade.get_widget("combo_timeline").set_active(
      ["public", "friends", "user"].index(self.updater.timeline))
    
    for x in self.glade.get_widget("menu_timeline").get_submenu().get_children():
      x.set_active(self.updater.timeline == x.get_name().split("_")[-1])
    self.sync = False

  def on_timeline_change(self, widget):
    if not self.sync:
      if isinstance(widget, gtk.ComboBox):
        self.gconf.set_string(GCONF_DIR + "/timeline_display", widget.get_active_text().lower())
      else:
        if widget.get_active():
          self.gconf.set_string(GCONF_DIR + "/timeline_display", widget.get_name().split("_")[-1])

  def on_update(self, updater, data):
    status = gwui.StatusList(data)
    status.show_all()
    if self.container.get_child():
      self.container.remove(self.container.get_child())
    self.container.add_with_viewport(status)
    self.statusbar.pop(0)
    self.statusbar.push(0, "Last update: %s" % time.strftime("%I:%M:%S %p"))

  def on_change(self, updater, new_messages):
    if pynotify.init("Gwibber"):
      for user, message in new_messages:
        n = pynotify.Notification(user["name"], message["text"])
        n.set_icon_from_pixbuf(gwui.UserIcon(user).get_pixbuf())
        n.show()
    else: print "Notification failed."
  
  def on_error(self, *a):
    import sys
    print sys.exc_info()
