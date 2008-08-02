#!/usr/bin/env python

"""

Gwibber Client v1.0
SegPhault (Ryan Paul) - 01/05/2008

"""

import sys, time, os, threading, datetime
import gtk, gtk.glade, gobject, table, webkit
import microblog, gwui, config, gintegration

gtk.gdk.threads_init()

MAX_MESSAGE_LENGTH = 140

CONFIGURABLE_UI_ELEMENTS = ["editor", "statusbar", "messages", "tray_icon"]
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
  "show_notifications": True,
  "refresh_interval": 2,
}

class GwibberClient(gtk.Window):
  def __init__(self, ui_dir="ui"):
    gtk.Window.__init__(self)
    self.set_title("Gwibber")
    self.resize(300, 300)
    config.GCONF.add_dir(config.GCONF_PREFERENCES_DIR, config.gconf.CLIENT_PRELOAD_NONE)
    self.preferences = config.Preferences()
    self.ui_dir = ui_dir
    self.last_update = None
    layout = gtk.VBox()

    self.accounts = config.Accounts()
    self.client = microblog.Client(self.accounts)
    self.client.handle_error = self.handle_error
    self.client.post_process_message = self.post_process_message

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

    self.connect("destroy", gtk.main_quit)

    for key, value in DEFAULT_PREFERENCES.items():
      if self.preferences[key] == None: self.preferences[key] = value

    self.timer = gobject.timeout_add(60000 * int(self.preferences["refresh_interval"]), self.update)
    self.preferences.notify("refresh_interval", self.on_refresh_interval_changed)

    self.content = gwui.MessageView("file://%s/default.html" % ui_dir)
    self.content.link_handler = self.on_link_clicked
    
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

    for i in CONFIGURABLE_UI_ELEMENTS:
      config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/show_%s" % i,
        lambda *a: self.apply_ui_element_settings())

    for i in CONFIGURABLE_UI_SETTINGS:
      config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/%s" % i,
        lambda *a: self.apply_ui_drawing_settings())
    
    self.apply_ui_element_settings()
    self.apply_ui_drawing_settings()
    self.show_all()

    self.cancel_button.hide()
    self.update()

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

  def apply_ui_drawing_settings(self):
    bgcolor = self.preferences["background_color"]
    bgimage = self.preferences["background_image"]

  def apply_ui_element_settings(self):
    for i in CONFIGURABLE_UI_ELEMENTS:
      if hasattr(self, i):
        getattr(self, i).set_property(
          "visible", self.preferences["show_%s" % i])

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

    for widget in \
      ["foreground_color",
       "link_color",
       "show_notifications",
       "refresh_interval",
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
      acct.bind(glade.get_widget("%s_%s" % (acct["protocol"], widget)), widget)

    glade.get_widget("%s_btnclose" % acct["protocol"]).connect("clicked",
      lambda a: dialog.destroy())

    glade.get_widget("%s_btndelete" % acct["protocol"]).connect("clicked",
      lambda a: self.on_account_delete(acct, dialog))

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
          gintegration.notify.init("Gwibber")
        
        for message in data:
          if message.is_new and can_notify:
            if hasattr(message, "image_path"):
              gintegration.notify.Notification(message.sender,
                message.text, message.image_path).show()
            else: gintegration.notify.Notification(message.sender, message.text).show()
        
        self.content.clear()
        for message in data: self.content.add(message)

        self.statusbar.pop(0)
        self.statusbar.push(0, "Last update: %s" % time.strftime("%I:%M:%S %p"))
        self.last_update = datetime.datetime.utcnow()
        
      finally: gobject.idle_add(self.throbber.clear)
    
    t = threading.Thread(target=process)
    t.setDaemon(True)
    t.start()

    return True

if __name__ == '__main__':
  w = GwibberClient()
  w.connect("destroy", gtk.main_quit)
  gtk.main()

