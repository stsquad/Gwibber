#!/usr/bin/env python

"""

Gwibber Client v1.0
SegPhault (Ryan Paul) - 01/05/2008

"""

import sys, time, operator, os, threading, datetime
import gtk, gtk.glade, gobject, dbus
import twitter, jaiku, facebook, digg, flickr
import gwui, config, gintegration, webbrowser

gtk.gdk.threads_init()

MAX_MESSAGE_LENGTH = 140

CONFIGURABLE_UI_ELEMENTS = ["editor", "statusbar", "messages"]
CONFIGURABLE_UI_SETTINGS = ["background_color", "background_image"]
IMAGE_CACHE_DIR = "%s/.gwibber/imgcache" % os.path.expanduser("~")
VERSION_NUMBER = 0.7

DEFAULT_PREFERENCES = {
  "version": VERSION_NUMBER,
  "link_color": "darkblue",
  "foreground_color": "black",
  "background_color": "white",
  "text_shadow_color": "black",
  "background_image": "",
  "message_drawing_transparency": 100,
  "message_drawing_gradients": True,
  "message_drawing_radius": 15,
  "message_text_shadow": False,
  "show_notifications": True,
  "refresh_interval": 2,
}

PROTOCOLS = {
  "jaiku": jaiku,
  "digg": digg,
  "twitter": twitter,
  "facebook": facebook,
  "flickr": flickr  
}

class GwibberClient(gtk.Window):
  def __init__(self, ui_dir="ui"):
    gtk.Window.__init__(self)
    self.set_title("Gwibber")
    self.resize(300, 300)
    config.GCONF.add_dir(config.GCONF_PREFERENCES_DIR, config.gconf.CLIENT_PRELOAD_NONE)
    self.preferences = config.Preferences()
    self.ui_dir = ui_dir
    self.accounts = config.Accounts()
    self.last_update = None 
    layout = gtk.VBox()

    self.connect("destroy", gtk.main_quit)

    for key, value in DEFAULT_PREFERENCES.items():
      if self.preferences[key] == None: self.preferences[key] = value

    self.timer = gobject.timeout_add(60000 * int(self.preferences["refresh_interval"]), self.update)
    self.preferences.notify("refresh_interval", self.on_refresh_interval_changed)

    self.content = gtk.VBox(spacing=5)
    self.content.set_border_width(5)
    
    self.background = gtk.EventBox()
    self.background.add(self.content)

    self.messages = gtk.ScrolledWindow()
    self.messages.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.messages.add_with_viewport(self.background)

    if gintegration.SPELLCHECK_ENABLED:
      self.input = gintegration.sexy.SpellEntry()
    else: self.input = gtk.Entry()
    self.input.connect("populate-popup", self.on_input_context_menu)
    self.input.connect("activate", self.on_input_activate)
    self.input.connect("changed", self.on_input_change)
    self.input.set_max_length(140)

    self.editor = gtk.HBox()
    self.editor.pack_start(self.input)
    
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.messages, True, True)
    vb.pack_start(self.editor, False, False)
    vb.set_border_width(5)
    
    self.statusbar = gtk.Statusbar()

    layout.pack_start(self.setup_menus(), False)
    layout.pack_start(vb, True, True)
    layout.pack_start(self.statusbar, False)
    self.add(layout)

    for i in CONFIGURABLE_UI_ELEMENTS:
      config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/show_%s" % i,
        lambda *a: self.apply_ui_element_settings())

    for i in CONFIGURABLE_UI_SETTINGS:
      config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/%s" % i,
        lambda *a: self.apply_ui_drawing_settings())
    
    self.show_all()
    self.apply_ui_element_settings()
    self.apply_ui_drawing_settings()
    self.update()

  def apply_ui_drawing_settings(self):
    bgcolor = self.preferences["background_color"]
    bgimage = self.preferences["background_image"]

    style = self.background.get_style().copy()

    if bgimage and os.path.exists(bgimage):
      pb = gtk.gdk.pixbuf_new_from_file(bgimage)
      pm, mask = pb.render_pixmap_and_mask(255);
      style.bg_pixmap[gtk.STATE_NORMAL] = pm
    else:
      style.bg_pixmap[gtk.STATE_NORMAL] = None
      if bgcolor:
        style.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse(bgcolor)

    self.background.set_style(style)

  def apply_ui_element_settings(self):
    for i in CONFIGURABLE_UI_ELEMENTS:
      if hasattr(self, i):
        getattr(self, i).set_property("visible",
          self.preferences["show_%s" % i])

  def on_refresh_interval_changed(self, *a):
    gobject.source_remove(self.timer)
    self.timer = gobject.timeout_add(60000 * int(self.preferences["refresh_interval"]), self.update)

  def on_message_context_menu(self, e, w, message):
    menu = gtk.Menu()
    mi = gtk.MenuItem("_Reply")
    mi.connect("activate", lambda m: self.reply(message))
    menu.append(mi)

    if hasattr(message, "url"):
      mi = gtk.MenuItem("Open in browser")
      mi.connect("activate", lambda m: webbrowser.open(message.url))
      menu.append(mi)

    if gintegration.service_is_running("org.gnome.Tomboy"):
      mi = gtk.MenuItem("Copy to _Tomboy")
      mi.connect("activate", lambda m: self.copy_to_tomboy(message))
      menu.append(mi)

    menu.show_all()
    menu.attach_to_widget(w, None)
    menu.popup(None, None, None, 3, 0)

  def copy_to_tomboy(self, message):
    gintegration.create_tomboy_note("%s message from %s at %s\n\n%s" % (
      message.account["protocol"].capitalize(),
      message.sender, message.time, message.text))
  
  def reply(self, message):
    self.input.grab_focus()
    self.input.set_text("@%s: " % message.sender_nick)
    self.input.set_position(-1)
    for acct in self.accounts:
      if acct["username"] != message.account["username"] and \
        acct["protocol"] != message.account["protocol"]:
        acct["send_enabled"] = False

  def on_link_clicked(self, e, w, message, link):
    webbrowser.open(link)

  def on_profile_image_clicked(self, e, w, message):
    webbrowser.open(message.profile_url)

  def on_input_context_menu(self, obj, menu):
    menu.append(gtk.SeparatorMenuItem())
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys():
        if PROTOCOLS[acct["protocol"]].Client(acct).can_send():
          mi = gtk.CheckMenuItem("%s (%s)" % (acct["username"], acct["protocol"]))
          acct.bind(mi, "send_enabled")
          menu.append(mi)

    menu.show_all()

  def on_input_change(self, widget):
    self.statusbar.pop(1)
    if len(widget.get_text()) > 0:
      self.statusbar.push(1,
        "Characters remaining: %s" % (widget.get_max_length() - len(widget.get_text())))

  def setup_menus(self):
    menuGwibber = gtk.Menu()
    menuView = gtk.Menu()
    menuAccounts = gtk.Menu()
    menuHelp = gtk.Menu()

    menuGwibberRefresh = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
    menuGwibberRefresh.connect("activate", self.on_refresh)
    menuGwibber.append(menuGwibberRefresh)

    menuGwibberPreferences = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
    menuGwibberPreferences.connect("activate", self.on_preferences)
    menuGwibber.append(menuGwibberPreferences)

    menuGwibberQuit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
    menuGwibberQuit.connect("activate", self.on_quit)
    menuGwibber.append(menuGwibberQuit)

    menuGwibberAbout = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
    menuGwibberAbout.connect("activate", self.on_about)
    menuHelp.append(menuGwibberAbout)

    for i in CONFIGURABLE_UI_ELEMENTS:
      mi = gtk.CheckMenuItem("_%s" % i.capitalize())
      self.preferences.bind(mi, "show_%s" % i)
      menuView.append(mi)

    menuGwibberItem = gtk.MenuItem("_Gwibber")
    menuGwibberItem.set_submenu(menuGwibber)

    menuViewItem = gtk.MenuItem("_View")
    menuViewItem.set_submenu(menuView)

    menuAccountsItem = gtk.MenuItem("_Accounts")
    menuAccountsItem.set_submenu(menuAccounts)
    menuAccountsItem.connect("select", self.on_accounts_menu)

    menuHelpItem = gtk.MenuItem("_Help")
    menuHelpItem.set_submenu(menuHelp)

    self.throbber = gtk.Image()
    menuSpinner = gtk.ImageMenuItem("")
    menuSpinner.set_right_justified(True)
    menuSpinner.set_sensitive(False)
    menuSpinner.set_image(self.throbber)
    
    menubar = gtk.MenuBar()
    menubar.append(menuGwibberItem)
    menubar.append(menuViewItem)
    menubar.append(menuAccountsItem)
    menubar.append(menuHelpItem)
    menubar.append(menuSpinner)
    return menubar

  def on_quit(self, mi):
    gtk.main_quit()

  def on_refresh(self, mi):
    self.update()

  def on_about(self, mi):
    glade = gtk.glade.XML("%s/preferences.glade" % self.ui_dir)
    dialog = glade.get_widget("about_dialog")
    dialog.set_version(str(VERSION_NUMBER))
    dialog.connect("response", lambda *a: dialog.hide())

    dialog.show_all()

  def on_preferences(self, mi):
    glade = gtk.glade.XML("%s/preferences.glade" % self.ui_dir)
    dialog = glade.get_widget("pref_dialog")
    dialog.show_all()

    for widget in \
      ["foreground_color",
       "link_color",
       "message_drawing_radius",
       "message_drawing_transparency",
       "message_drawing_gradients",
       "show_notifications",
       "refresh_interval",
       "message_text_shadow",
       "text_shadow_color",
       "background_color"]:
        self.preferences.bind(glade.get_widget(widget), widget)

    def setbgimg(*a):
      self.preferences["background_image"] = glade.get_widget("background_image").get_filename() or ""
    
    glade.get_widget("background_image").set_filename(self.preferences["background_image"])
    glade.get_widget("background_image").connect("selection-changed", setbgimg)
    glade.get_widget("background_image_clear").connect("clicked",
      lambda *a: glade.get_widget("background_image").set_uri(""))


    glade.get_widget("button_close").connect("clicked", lambda *a: dialog.destroy())

  
  def on_accounts_menu(self, amenu):
    amenu.emit_stop_by_name("select")
    menu = amenu.get_submenu()
    for c in menu: menu.remove(c)
    
    menuAccountsManage = gtk.MenuItem("_Manage")
    menu.append(menuAccountsManage)
   
    menuAccountsCreate = gtk.MenuItem("_Create")
    menu.append(menuAccountsCreate)
    mac = gtk.Menu()

    for p in PROTOCOLS.keys():
      mi = gtk.MenuItem("%s" % p.capitalize())
      mi.connect("activate", self.on_account_create, p)
      mac.append(mi)

    menuAccountsCreate.set_submenu(mac)
    menu.append(gtk.SeparatorMenuItem())
    
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys():
        sm = gtk.Menu()
        
        for i in ["receive", "send"]:
          if getattr(PROTOCOLS[acct["protocol"]].Client(acct), "can_%s" % i)():
            mi = gtk.CheckMenuItem("_%s Messages" % i.capitalize())
            acct.bind(mi, "%s_enabled" % i)
            sm.append(mi)
        
        sm.append(gtk.SeparatorMenuItem())
        
        mi = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        mi.connect("activate", self.on_account_properties, acct)
        sm.append(mi)

        mi = gtk.MenuItem("%s (%s)" % (acct["username"] or "None", acct["protocol"]))
        mi.set_submenu(sm)
        menu.append(mi)
    menu.show_all()
    amenu.set_submenu(menu)

  def on_account_properties(self, w, acct):
    c = PROTOCOLS[acct["protocol"]].ConfigPanel(acct, self.preferences)
    
    w = gtk.Window()
    w.set_title("Manage Acccount")
    w.set_resizable(False)
    w.set_border_width(10)
    
    buttons = gtk.HButtonBox()
    bc = gtk.Button(stock=gtk.STOCK_CLOSE)
    bd = gtk.Button(stock=gtk.STOCK_DELETE)
    bc.connect("clicked", lambda a: w.destroy())
    bd.connect("clicked", lambda a: self.on_account_delete(acct, w))
    buttons.pack_start(bd)
    buttons.pack_start(bc)

    vb = gtk.VBox(spacing=5)
    vb.pack_start(c.build_ui())
    vb.pack_start(gtk.HSeparator())
    vb.pack_start(buttons)
    
    w.add(vb)
    w.show_all()

  def on_account_create(self, w, protocol):
    a = self.accounts.new_account()
    a["protocol"] = protocol
    self.on_account_properties(w, a)

  def on_account_delete(self, acct, dialog = None):
    d = gtk.MessageDialog(dialog, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
      gtk.BUTTONS_YES_NO, "Are you sure you want to delete this account?")
    
    if d.run() == gtk.RESPONSE_YES:
      if dialog: dialog.destroy()
      self.accounts.delete_account(acct)
    
    d.destroy()

  def generate_message_list(self):
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys():
        client = PROTOCOLS[acct["protocol"]].Client(acct)
        if client.receive_enabled():
          for message in client.get_messages():
            yield message

  def draw_messages(self):
    for i in self.content: self.content.remove(i)

    for message in self.data:
      m = PROTOCOLS[message.account["protocol"]].StatusMessage(message, self.preferences)
      if hasattr(m, "messagetext"):
        m.messagetext.connect("link-clicked", self.on_link_clicked)
        m.messagetext.connect("right-clicked", self.on_message_context_menu)
      if hasattr(m, "icon_frame") and hasattr(message, "profile_url"):
        m.icon_frame.connect("button-release-event", self.on_profile_image_clicked, message)
      self.content.pack_start(m)

    self.content.show_all()      

  def on_input_activate(self, e):
    if self.input.get_text().strip():
      for acct in self.accounts:
        if acct["protocol"] in PROTOCOLS.keys():
          c = PROTOCOLS[acct["protocol"]].Client(acct)
          if c.can_send() and c.send_enabled():
            c.transmit_status(self.input.get_text().strip())
      self.input.set_text("")

  def update(self):
    self.throbber.set_from_animation(gtk.gdk.PixbufAnimation("%s/progress.gif" % self.ui_dir))
    #while gtk.events_pending(): gtk.main_iteration()

    def process():
      try:
        self.data = list(self.generate_message_list())
        self.data.sort(key=operator.attrgetter("time"), reverse=True)

        gtk.gdk.threads_enter()

        if self.last_update and self.preferences["show_notifications"]:
          for m in self.data:
            if m.time > self.last_update and gintegration.notify.init("Gwibber"):
              gintegration.notify.Notification(m.sender, m.text,
                gwui.image_cache(m.image, IMAGE_CACHE_DIR)).show()

        if self.last_update:
          for count, m in enumerate(self.content):
            if len(self.data) < count or m.message.text != self.data[count].text:
              self.draw_messages()
              break
        else: self.draw_messages()
        
        self.statusbar.pop(0)
        self.statusbar.push(0, "Last update: %s" % time.strftime("%I:%M:%S %p"))
        self.last_update = datetime.datetime.utcnow()
        
        gtk.gdk.threads_leave()
      finally: gobject.idle_add(self.throbber.clear)
    
    t = threading.Thread(target=process)
    t.setDaemon(True)
    t.start()

    return True
    
if __name__ == '__main__':
  w = GwibberClient()
  w.connect("destroy", gtk.main_quit)
  gtk.main()

