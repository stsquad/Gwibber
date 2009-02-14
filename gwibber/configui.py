
import gtk, config, gtk.glade, microblog, table, gintegration, resources

import gettext

_ = gettext.lgettext

class AccountManager(config.Accounts):
  def __init__(self, path = config.GCONF_ACCOUNTS_DIR):
    self.accounts = self
    self.path = path

  def facebook_authorize(self, account):
    from gwibber.microblog.support import facelib

    glade = gtk.glade.XML(resources.get_ui_asset("preferences.glade"))
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
          _("Keys obtained successfully."))
      else:
        m = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
          _("Failed to obtain key."))

      m.run()
      m.destroy()
    
    glade.get_widget("button_request").connect("clicked",
      lambda *a: gintegration.load_url("http://www.facebook.com/code_gen.php?v=1.0&api_key=%s" % microblog.facebook.APP_KEY))
    
    glade.get_widget("button_authorize").connect("clicked",
      lambda *a: gintegration.load_url("http://www.facebook.com/authorize.php?api_key=%s&v=1.0&ext_perm=status_update" % microblog.facebook.APP_KEY))

    glade.get_widget("button_apply_auth").connect("clicked", on_validate_click)
    glade.get_widget("button_close_facebook_auth").connect("clicked", lambda w: dialog.destroy())

  def show_properties_dialog(self, acct, create = False):
    glade = gtk.glade.XML(resources.get_ui_asset("preferences.glade"))
    dialog = glade.get_widget("dialog_%s" % acct["protocol"])
    dialog.show_all()

    for widget in microblog.PROTOCOLS[acct["protocol"]].PROTOCOL_INFO["config"]:
      w = glade.get_widget("%s_%s" % (acct["protocol"], widget.replace("private:", "")))
      if w:
        if isinstance(w, gtk.ColorButton): acct.bind(w, widget, default="#729FCF")
        else: acct.bind(w, widget)

    glade.get_widget("%s_btnclose" % acct["protocol"]).connect("clicked",
      lambda a: dialog.destroy())

    try:
      lb = glade.get_widget("%s_linkbutton" % acct["protocol"])
      lb.connect("clicked", lambda *a: gintegration.load_url(lb.get_uri()))
    except: pass

    if create:
      glade.get_widget("%s_btndelete" % acct["protocol"]).props.label = gtk.STOCK_CANCEL
      glade.get_widget("%s_btnclose" % acct["protocol"]).props.label = gtk.STOCK_OK
      
    glade.get_widget("%s_btndelete" % acct["protocol"]).connect("clicked",
      lambda a: self.on_account_delete(acct, dialog, create = create))

    if acct["protocol"] == "facebook":
      glade.get_widget("btnAuthorize").connect("clicked",
        lambda a: self.facebook_authorize(acct))

    if create:
      dialog.set_title(_("Create %s account") % acct["protocol"])
    else:
      dialog.set_title(_("Edit %s account") % acct["protocol"])

  def on_account_create(self, w, protocol):
    a = self.accounts.new_account()
    a["protocol"] = protocol
    self.show_properties_dialog(a, create=True)

  def on_account_delete(self, acct, dialog = None, create = False):
    if create:
      msg = _("Are you sure you want to cancel the creation of this account?")
    else:
      msg = _("Are you sure you want to delete this account?")
              
    d = gtk.MessageDialog(dialog, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
      gtk.BUTTONS_YES_NO, msg)
    
    if d.run() == gtk.RESPONSE_YES:
      if dialog: dialog.destroy()
      self.accounts.delete_account(acct)
    
    d.destroy()

  def show_account_list(self):
    manager = gtk.Window()
    manager.set_title(_("Manage Accounts"))
    manager.set_border_width(10)
    manager.resize(390,240)

    def toggle_table_checkbox(cr, i, key, table):
      a = table.tree_store.get_obj(i)
      a[key] = (a[key] and [False] or [True])[0]

    col_receive = gtk.CellRendererToggle()
    col_send = gtk.CellRendererToggle()
    col_search = gtk.CellRendererToggle()

    def generate_account_name(acct):
      if hasattr(acct.get_protocol(), "account_name"):
        return acct.get_protocol().account_name(acct)
      elif acct["username"]: return acct["username"]

    data = table.generate([
      ["username", lambda a: generate_account_name(a), _("Username")],
      ["receive",  (col_receive, {
        "active": lambda a: a["receive_enabled"],
        "visible": lambda a: a.supports(microblog.can.RECEIVE)}), _("Receive")],
      ["send", (col_send, {
        "active": lambda a: a["send_enabled"],
        "visible": lambda a: a.supports(microblog.can.SEND)}), _("Send")],
      ["search", (col_search, {
        "active": lambda a: a["search_enabled"],
        "visible": lambda a: a.supports(microblog.can.SEARCH)}), _("Search")],
      ["protocol", lambda a: a.get_protocol().PROTOCOL_INFO["name"], _("Protocol")],
    ])

    col_receive.connect("toggled", toggle_table_checkbox, "receive_enabled", data)
    col_send.connect("toggled", toggle_table_checkbox, "send_enabled", data)
    col_search.connect("toggled", toggle_table_checkbox, "search_enabled", data)

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
          mi = gtk.MenuItem(microblog.PROTOCOLS[p].PROTOCOL_INFO["name"])
          mi.connect("activate", self.on_account_create, p)
          mac.append(mi)
        mac.show_all()
        mac.popup(None, None, None, 1, 0)

      elif stock == gtk.STOCK_PROPERTIES:
        if isinstance(data.get_selected(), config.Account):
          self.show_properties_dialog(data.get_selected())

      elif stock == gtk.STOCK_DELETE:
        if isinstance(data.get_selected(), config.Account):
          self.on_account_delete(data.get_selected())

    def on_account_change(gc, v, entry, t):
      if len([a for a in self.accounts]) != len(t.tree_store):
        t.tree_store.clear()
        for a in self.accounts: t+= a
    
    config.GCONF.notify_add(self.accounts.path, on_account_change, data)

    for stock in [gtk.STOCK_ADD, gtk.STOCK_PROPERTIES, gtk.STOCK_DELETE, gtk.STOCK_CLOSE]:
      b = gtk.Button(stock=stock)
      b.connect("clicked", on_click_button, stock)
      buttons.pack_start(b)

    vb = gtk.VBox(spacing=5)
    vb.pack_start(scroll)
    vb.pack_start(buttons, False, False)

    manager.add(vb)
    manager.show_all()
