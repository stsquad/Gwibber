#!/usr/bin/env python

"""

Gwibber Client v1.0
SegPhault (Ryan Paul) - 01/05/2008

"""

import sys, time, os, threading, mx.DateTime, hashlib
import gtk, gtk.glade, gobject, table, webkit
import microblog, gwui, config, gintegration

gtk.gdk.threads_init()

MAX_MESSAGE_LENGTH = 140

CONFIGURABLE_UI_ELEMENTS = ["editor", "statusbar", "messages", "tray_icon"]
#CONFIGURABLE_UI_SETTINGS = ["background_color", "background_image"]
IMAGE_CACHE_DIR = "%s/.gwibber/imgcache" % os.path.expanduser("~")
VERSION_NUMBER = 0.7

DEFAULT_PREFERENCES = {
  "version": VERSION_NUMBER,
  "show_notifications": True,
  "refresh_interval": 2,
  "minimize_to_tray": False,
  "hide_taskbar_entry": False,
  
#  "link_color": "darkblue",
#  "foreground_color": "black",
#  "background_color": "white",
#  "text_shadow_color": "black",
#  "background_image": "",
}

for i in CONFIGURABLE_UI_ELEMENTS:
  DEFAULT_PREFERENCES["show_%s" % i] = True

class GwibberClient(gtk.Window):
  def __init__(self, ui_dir="ui"):
    gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
    self.set_title("Gwibber")
    self.set_default_size(330, 500)
    config.GCONF.add_dir(config.GCONF_PREFERENCES_DIR, config.gconf.CLIENT_PRELOAD_NONE)
    self.preferences = config.Preferences()
    self.ui_dir = ui_dir
    self.last_update = None
    layout = gtk.VBox()

    self.accounts = config.Accounts()
    self.client = microblog.Client(self.accounts)
    self.client.handle_error = self.handle_error
    self.client.post_process_message = self.post_process_message

    self.notification_bubbles = {}
    self.message_store = []
    self.message_target = None
    
    self.errors = table.generate([
      ["date", lambda t: t.time.strftime("%Y-%m-%d")],
      ["time", lambda t: t.time.strftime("%I:%M:%S %p")],
      ["username"],
      ["protocol"],
      ["message", (gtk.CellRendererText(), {
        "markup": lambda t: t.message})]
    ])

    self.connect("delete-event", self.on_window_close)

    for key, value in DEFAULT_PREFERENCES.items():
      if self.preferences[key] == None: self.preferences[key] = value

    self.timer = gobject.timeout_add(60000 * int(self.preferences["refresh_interval"]), self.update)
    self.preferences.notify("refresh_interval", self.on_refresh_interval_changed)

    self.content = gwui.MessageView("file://%s/default.html" % ui_dir)
    self.content.link_handler = self.on_link_clicked
    
    gtk.icon_theme_add_builtin_icon("gwibber", 22,
      gtk.gdk.pixbuf_new_from_file_at_size("%s/gwibber.svg" % ui_dir, 24, 24))

    self.set_icon_name("gwibber")
    self.tray_icon = gtk.status_icon_new_from_icon_name("gwibber")
    self.tray_icon.connect("activate", self.on_toggle_window_visibility)

    self.messages = gtk.ScrolledWindow()
    self.messages.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.messages.add(self.content)

    if gintegration.SPELLCHECK_ENABLED:
      self.input = gintegration.sexy.SpellEntry()
    else: self.input = gtk.Entry()
    self.input.connect("populate-popup", self.on_input_context_menu)
    self.input.connect("activate", self.on_input_activate)
    self.input.connect("changed", self.on_input_change)
    self.input.set_max_length(140)

    self.cancel_button = gtk.Button("Cancel")
    self.cancel_button.connect("clicked", self.on_cancel_reply)

    self.editor = gtk.HBox()
    self.editor.pack_start(self.input)
    self.editor.pack_start(self.cancel_button, False)
    
    
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.messages, True, True)
    vb.pack_start(self.editor, False, False)
    vb.set_border_width(5)
    
    self.statusbar = gtk.Statusbar()

    layout.pack_start(self.setup_menus(), False)
    layout.pack_start(vb, True, True)
    layout.pack_start(self.statusbar, False)
    self.add(layout)

    if gintegration.can_notify:
      import dbus

      def on_notify_close(nId):
        if self.notification_bubbles.has_key(nId):
          del self.notification_bubbles[nId]

      def on_notify_action(nId, action):
        if action == "reply":
          self.reply(self.notification_bubbles[nId])
          self.window.show()
          self.present()
      
      bus = dbus.SessionBus()
      bus.add_signal_receiver(on_notify_close,
        dbus_interface="org.freedesktop.Notifications",
        signal_name="CloseNotification")
      
      bus.add_signal_receiver(on_notify_action,
        dbus_interface="org.freedesktop.Notifications",
        signal_name="ActionInvoked")

    for i in CONFIGURABLE_UI_ELEMENTS:
      config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/show_%s" % i,
        lambda *a: self.apply_ui_element_settings())
    
    self.preferences.notify("hide_taskbar_entry",
      lambda *a: self.apply_ui_element_settings())

    #for i in CONFIGURABLE_UI_SETTINGS:
    #  config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/%s" % i,
    #    lambda *a: self.apply_ui_drawing_settings())
    
    self.show_all()
    self.apply_ui_element_settings()
    self.cancel_button.hide()
    #self.update()

  def on_window_close(self, w, e):
    if self.preferences["minimize_to_tray"]:
      self.preferences["show_tray_icon"] = True
      self.on_toggle_window_visibility(w)
      return True
    else: gtk.main_quit()
  
  def on_cancel_reply(self, w):
    self.cancel_button.hide()
    self.message_target = None
    self.input.set_text("")

  def on_toggle_window_visibility(self, w):
    if self.get_property("visible"):
      self.last_position = self.get_position()
      self.hide()
    else:
      self.show()
      self.move(*self.last_position)

  def apply_ui_element_settings(self):
    for i in CONFIGURABLE_UI_ELEMENTS:
      if hasattr(self, i):
        getattr(self, i).set_property(
          "visible", self.preferences["show_%s" % i])
    
    self.set_property("skip-taskbar-hint",
      self.preferences["hide_taskbar_entry"])

  def on_refresh_interval_changed(self, *a):
    gobject.source_remove(self.timer)
    self.timer = gobject.timeout_add(
      60000 * int(self.preferences["refresh_interval"]), self.update)

  def copy_to_tomboy(self, message):
    gintegration.create_tomboy_note("%s message from %s at %s\n\n%s" % (
      message.account["protocol"].capitalize(),
      message.sender, message.time, message.text))
  
  def handle_at_reply(self, message, protocol):
    self.input.grab_focus()
    self.input.set_text("@%s: " % message.sender_nick)
    self.input.set_position(-1)

    self.message_target = message.account
    self.cancel_button.show()

  def reply(self, message):
    acct = message.account

    if acct["protocol"] == "twitter" or acct["protocol"] == "identica":
      self.handle_at_reply(message, acct["protocol"])
      return

    if acct["protocol"] in microblog.PROTOCOLS.keys():
      client = microblog.PROTOCOLS[acct["protocol"]].Client(acct)

      if hasattr(client, "can_reply"):
        reply = gtk.Window()
        reply.set_title("Reply")
        reply.set_border_width(5)
        reply.resize(390, 240)

        def on_load_finished(view, frame):
          for m in client.get_replies(message):
            content.add(self.post_process_message(m))

        content = gwui.MessageView("file://%s/default.html" % self.ui_dir)
        content.connect("load-finished", on_load_finished)

        def on_reply_send(e):
          if e.get_text().strip():
            c = microblog.PROTOCOLS[acct["protocol"]].Client(acct)
            if c.can_send():
              c.transmit_reply(message, e.get_text().strip())
              e.set_text("")
        
        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.add(content)

        input = gtk.Entry()
        input.connect("activate", on_reply_send)

        vb = gtk.VBox(spacing=5)
        vb.pack_start(scroll)
        vb.pack_start(input, False, False)

        reply.add(vb)
        reply.show_all()
    
  def on_link_clicked(self, uri):
    if uri.startswith("gwibber:"):
      if uri.startswith("gwibber:reply"):
        self.reply(self.content.messages[int(uri.split("/")[-1])])
        return True
    else: return False

  def on_input_context_menu(self, obj, menu):
    menu.append(gtk.SeparatorMenuItem())
    for acct in self.accounts:
      if acct["protocol"] in microblog.PROTOCOLS.keys():
        if microblog.PROTOCOLS[acct["protocol"]].Client(acct).can_send():
          mi = gtk.CheckMenuItem("%s (%s)" % (acct["username"], acct["protocol"]))
          acct.bind(mi, "send_enabled")
          menu.append(mi)

    menu.show_all()

  def on_input_change(self, widget):
    self.statusbar.pop(1)
    if len(widget.get_text()) > 0:
      self.statusbar.push(1, "Characters remaining: %s" % (
        widget.get_max_length() - len(widget.get_text())))

  def setup_menus(self):
    menuGwibber = gtk.Menu()
    menuView = gtk.Menu()
    menuAccounts = gtk.Menu()
    menuHelp = gtk.Menu()
    menuTray = gtk.Menu()

    actRefresh = gtk.Action("gwibberRefresh", "_Refresh", None, gtk.STOCK_REFRESH)
    actRefresh.connect("activate", self.on_refresh)
    menuGwibber.append(actRefresh.create_menu_item())

    actPreferences = gtk.Action("gwibberPreferences", "_Preferences", None, gtk.STOCK_PREFERENCES)
    actPreferences.connect("activate", self.on_preferences)
    menuGwibber.append(actPreferences.create_menu_item())

    actQuit  = gtk.Action("gwibberQuit", "_Quit", None, gtk.STOCK_QUIT)
    actQuit.connect("activate", self.on_quit)
    menuGwibber.append(actQuit.create_menu_item())

    actAbout = gtk.Action("gwibberAbout", "_About", None, gtk.STOCK_ABOUT)
    actAbout.connect("activate", self.on_about)
    menuHelp.append(actAbout.create_menu_item())

    for i in CONFIGURABLE_UI_ELEMENTS:
      mi = gtk.CheckMenuItem("_%s" % " ".join(i.split("_")).capitalize())
      self.preferences.bind(mi, "show_%s" % i)
      menuView.append(mi)

    mi = gtk.MenuItem("_Errors")
    mi.connect("activate", self.on_errors_show)
    menuView.append(gtk.SeparatorMenuItem())
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

    menuTray.append(actRefresh.create_menu_item())
    menuTray.append(actPreferences.create_menu_item())
    menuTray.append(actQuit.create_menu_item())

    self.tray_icon.connect("popup-menu", lambda i,b,a: menuTray.popup(
      None, None, gtk.status_icon_position_menu, b, a, self.tray_icon))
    
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
  
  def on_errors_show(self, mi):
    errorwin = gtk.Window()
    errorwin.set_title("Errors")
    errorwin.set_border_width(10)
    errorwin.resize(600, 300)

    def on_row_activate(tree, path, col):
      w = gtk.Window()
      w.set_title("Debug Output")
      w.resize(800, 800)
      
      text = gtk.TextView()
      text.get_buffer().set_text(tree.get_selected().error)

      scroll = gtk.ScrolledWindow()
      scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
      scroll.add_with_viewport(text)

      w.add(scroll)
      w.show_all()

    errors = table.View(self.errors.tree_style,
      self.errors.tree_store, self.errors.tree_filter)
    errors.connect("row-activated", on_row_activate)

    scroll = gtk.ScrolledWindow()
    scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scroll.add_with_viewport(errors)

    buttons = gtk.HButtonBox()
    buttons.set_layout(gtk.BUTTONBOX_END)

    def on_click_button(w, stock):
      if stock == gtk.STOCK_CLOSE:
        errorwin.destroy()
      elif stock == gtk.STOCK_CLEAR:
        self.errors.tree_store.clear()

    for stock in [gtk.STOCK_CLEAR, gtk.STOCK_CLOSE]:
      b = gtk.Button(stock=stock)
      b.connect("clicked", on_click_button, stock)
      buttons.pack_start(b)
    
    vb = gtk.VBox(spacing=5)
    vb.pack_start(scroll)
    vb.pack_start(buttons, False, False)

    errorwin.add(vb)
    errorwin.show_all()

  def on_preferences(self, mi):
    glade = gtk.glade.XML("%s/preferences.glade" % self.ui_dir)
    dialog = glade.get_widget("pref_dialog")
    dialog.show_all()

    for widget in ["show_notifications", "refresh_interval", "minimize_to_tray", "hide_taskbar_entry"]:
      self.preferences.bind(glade.get_widget("pref_%s" % widget), widget)

    glade.get_widget("button_close").connect("clicked", lambda *a: dialog.destroy())
  
  def on_accounts_menu(self, amenu):
    amenu.emit_stop_by_name("select")
    menu = amenu.get_submenu()
    for c in menu: menu.remove(c)
    
    menuAccountsManage = gtk.MenuItem("_Manage")
    menuAccountsManage.connect("activate", self.on_accounts_manage)
    menu.append(menuAccountsManage)
   
    menuAccountsCreate = gtk.MenuItem("_Create")
    menu.append(menuAccountsCreate)
    mac = gtk.Menu()

    for p in microblog.PROTOCOLS.keys():
      mi = gtk.MenuItem("%s" % p.capitalize())
      mi.connect("activate", self.on_account_create, p)
      mac.append(mi)

    menuAccountsCreate.set_submenu(mac)
    menu.append(gtk.SeparatorMenuItem())
    
    for acct in self.accounts:
      if acct["protocol"] in microblog.PROTOCOLS.keys():
        sm = gtk.Menu()
        
        for i in ["receive", "send"]:
          if getattr(microblog.PROTOCOLS[acct["protocol"]].Client(acct), "can_%s" % i)():
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
    glade = gtk.glade.XML("%s/preferences.glade" % self.ui_dir)
    dialog = glade.get_widget("dialog_%s" % acct["protocol"])
    dialog.show_all()
    
    for widget in microblog.PROTOCOLS[acct["protocol"]].CONFIG:
      w = glade.get_widget("%s_%s" % (acct["protocol"], widget))
      if isinstance(w, gtk.ColorButton): acct.bind(w, widget, default="#729FCF")
      else: acct.bind(w, widget)

    glade.get_widget("%s_btnclose" % acct["protocol"]).connect("clicked",
      lambda a: dialog.destroy())

    glade.get_widget("%s_btndelete" % acct["protocol"]).connect("clicked",
      lambda a: self.on_account_delete(acct, dialog))

    if acct["protocol"] == "facebook":
      glade.get_widget("btnAuthorize").connect("clicked",
        lambda a: self.facebook_authorize(acct))

  def facebook_authorize(self, account):
    from gwibber.microblog.support import facelib

    glade = gtk.glade.XML("%s/preferences.glade" % self.ui_dir)
    dialog = glade.get_widget("facebook_config")
    dialog.show_all()

    def on_validate_click(w):
      fb = facelib.Facebook(microblog.facebook.APP_KEY, microblog.facebook.SECRET_KEY,
        glade.get_widget("entry_auth_token").get_text().strip())

      data = fb.auth.getSession()
      if data and data.has_key("session_key"):
        account["secret_key"] = str(data["secret"])
        account["session_key"] = str(data["session_key"])
        
        m = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
          "Keys obtained successfully.")
      else:
        m = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
          "Failed to obtain key.") 

      m.run()
      m.destroy()
    
    glade.get_widget("button_request").connect("clicked",
      lambda *a: gintegration.load_url("http://www.facebook.com/code_gen.php?v=1.0&api_key=%s" % microblog.facebook.APP_KEY))
    
    glade.get_widget("button_authorize").connect("clicked",
      lambda *a: gintegration.load_url("http://www.facebook.com/authorize.php?api_key=%s&v=1.0&ext_perm=status_update" % microblog.facebook.APP_KEY))

    glade.get_widget("button_apply_auth").connect("clicked", on_validate_click)
    glade.get_widget("button_close_facebook_auth").connect("clicked", lambda w: dialog.destroy())



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

  def on_accounts_manage(self, mi):
    manager = gtk.Window()
    manager.set_title("Manage Accounts")
    manager.set_border_width(10)
    manager.resize(390,240)

    def can_toggle(a, key):
      c = microblog.PROTOCOLS[a["protocol"]].Client(a)
      if getattr(c, "can_%s" % key)(): return True

    def toggle_table_checkbox(cr, i, key, table):
      a = table.tree_store.get_obj(i)
      a[key] = (a[key] and [False] or [True])[0]

    col_receive = gtk.CellRendererToggle()
    col_send = gtk.CellRendererToggle()

    data = table.generate([
      ["username", lambda a: a["username"] or "None"],
      ["Receive", (col_receive, {
        "active": lambda a: a["receive_enabled"],
        "visible": lambda a: can_toggle(a, "receive")})],
      ["Send", (col_send, {
        "active": lambda a: a["send_enabled"],
        "visible": lambda a: can_toggle(a, "send")})],
      ["protocol", lambda a: a["protocol"].capitalize()],
    ])

    col_receive.connect("toggled", toggle_table_checkbox, "receive_enabled", data)
    col_send.connect("toggled", toggle_table_checkbox, "send_enabled", data)

    for a in self.accounts: data += a
    
    scroll = gtk.ScrolledWindow()
    scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scroll.add_with_viewport(data)
    data.set_property("rules-hint", True)

    buttons = gtk.HButtonBox()
    buttons.set_layout(gtk.BUTTONBOX_END)

    def on_click_button(w, stock):
      if stock == gtk.STOCK_CLOSE:
        manager.destroy()

      elif stock == gtk.STOCK_ADD:
        mac = gtk.Menu()
        for p in microblog.PROTOCOLS.keys():
          mi = gtk.MenuItem("%s" % p.capitalize())
          mi.connect("activate", self.on_account_create, p)
          mac.append(mi)
        mac.show_all()
        mac.popup(None, None, None, 1, 0)

      elif stock == gtk.STOCK_PROPERTIES:
        if isinstance(data.get_selected(), config.Account):
          self.on_account_properties(w, data.get_selected())

      elif stock == gtk.STOCK_DELETE:
        if isinstance(data.get_selected(), config.Account):
          self.on_account_delete(data.get_selected())

    def on_account_change(gc, v, entry, t):
      # handle account color change here

      if len([a for a in self.accounts]) != len(t.tree_store):
        t.tree_store.clear()
        for a in self.accounts: t+= a
    
    config.GCONF.notify_add("/apps/gwibber/accounts", on_account_change, data)

    for stock in [gtk.STOCK_ADD, gtk.STOCK_PROPERTIES, gtk.STOCK_DELETE, gtk.STOCK_CLOSE]:
      b = gtk.Button(stock=stock)
      b.connect("clicked", on_click_button, stock)
      buttons.pack_start(b)

    vb = gtk.VBox(spacing=5)
    vb.pack_start(scroll)
    vb.pack_start(buttons, False, False)

    manager.add(vb)
    manager.show_all()

  def handle_error(self, acct, err, msg = None):
    print acct, err, msg
    return
    self.errors += {
      "time": datetime.datetime.now(),
      "username": acct["username"],
      "protocol": acct["protocol"],
      "message": "%s\n<i><span foreground='red'>%s</span></i>" % (msg, err.split("\n")[-2]),
      "error": err,
    }

  def on_input_activate(self, e):
    if self.input.get_text().strip():
      if self.message_target:
        protocols = [self.message_target["protocol"]]
      else: protocols = microblog.PROTOCOLS.keys()
    
      self.client.transmit_status(self.input.get_text().strip(), protocols)
      self.on_cancel_reply(None)

      self.input.set_text("")

  def post_process_message(self, message):
    color = gtk.gdk.color_parse(message.account[message.bgcolor])
    message.hexbg = message.account[message.bgcolor][1:3] + message.account[message.bgcolor][5:7] + message.account[message.bgcolor][9:11]
    message.bgstyle = "rgba(%s,%s,%s,0.6)" % (color.red/255, color.green/255, color.blue/255)
    message.image_url = message.image
    message.image_path = gwui.image_cache(message.image_url)
    message.image = "file://%s" % message.image_path

    message.gId = hashlib.sha1(message.text[:128].strip(".")).hexdigest()

    if self.last_update:
      message.is_new = message.time > self.last_update
    else: message.is_new = False
    
    message.time_string = microblog.support.generate_time_string(message.time)

    if not hasattr(message, "html_string"):
      message.html_string = '<span class="text">%s</span>' % \
        microblog.support.LINK_PARSE.sub('<a href="\\1">\\1</a>', message.text)

    return message

  def update(self):
    self.throbber.set_from_animation(gtk.gdk.PixbufAnimation("%s/progress.gif" % self.ui_dir))

    def process():
      try:
        data = self.client.get_messages()

        can_notify = self.preferences["show_notifications"] and \
          gintegration.can_notify

        seen = []
        
        for message in data:
          message.is_duplicate = message.gId in seen
          if not message.is_duplicate: seen.append(message.gId)

          if message.is_new and can_notify:
            gtk.gdk.threads_enter()
            n = gintegration.notify(message.sender, message.text, hasattr(message,
              "image_path") and message.image_path or None, ["reply", "Reply"])
            gtk.gdk.threads_leave()

            self.notification_bubbles[n] = message

        gtk.gdk.threads_enter()
        self.content.clear()
        for message in data: self.content.add(message)
        gtk.gdk.threads_leave()

        self.statusbar.pop(0)
        self.statusbar.push(0, "Last update: %s" % time.strftime("%I:%M:%S %p"))
        self.last_update = mx.DateTime.gmt()
        
      finally: gobject.idle_add(self.throbber.clear)
    
    t = threading.Thread(target=process)
    t.setDaemon(True)
    t.start()

    return True

if __name__ == '__main__':
  w = GwibberClient()
  w.connect("destroy", gtk.main_quit)
  gtk.main()

