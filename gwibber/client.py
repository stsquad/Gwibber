"""

Gwibber Client v1.0
SegPhault (Ryan Paul) - 01/05/2008

"""

import time, os, threading, logging, mx.DateTime, hashlib
from . import table
import gtk, gtk.glade, gobject, functools, traceback
import microblog
from . import gwui, config, gintegration, configui, resources
import xdg.BaseDirectory, urllib2, urlparse
import webbrowser
from . import urlshorter

# Setup Pidgin
from . import pidgin
microblog.PROTOCOLS["pidgin"] = pidgin

# i18n magic
import gettext
import locale

# urllib (quoting urls)
import urllib

# Set this way as in setup.cfg we have prefix=/usr/local
LOCALEDIR = "/usr/local/share/locale"
DOMAIN = "gwibber"

locale.setlocale(locale.LC_ALL, "")

for module in gtk.glade, gettext:
  module.bindtextdomain(DOMAIN, LOCALEDIR)
  module.textdomain(DOMAIN)

_ = gettext.lgettext

gtk.gdk.threads_init()

MAX_MESSAGE_LENGTH = 140

VERSION_NUMBER = "1.0.2"

def N_(message): return message

CONFIGURABLE_UI_ELEMENTS = {
  "editor": N_("_Editor"),
  "statusbar": N_("_Statusbar"),
  "tray_icon": N_("Tray _Icon"),
}

CONFIGURABLE_ACCOUNT_ACTIONS = {
  # Translators: these are checkbox
  "receive": N_("_Receive Messages"),
  "send": N_("_Send Messages"),
  "search": N_("Search _Messages")
  }

DEFAULT_PREFERENCES = {
  "version": VERSION_NUMBER,
  "show_notifications": True,
  "refresh_interval": 2,
  "minimize_to_tray": False,
  "hide_taskbar_entry": False,
  "spellcheck_enabled": True,
  "theme": "default",
  "urlshorter": "is.gd",
}

for _i in list(CONFIGURABLE_UI_ELEMENTS.keys()):
  DEFAULT_PREFERENCES["show_%s" % _i] = True

try:
  import indicate
  import wnck
except:
  indicate = None

class GwibberClient(gtk.Window):
  def __init__(self):

    self.dbus = gintegration.DBusManager(self)

    gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
    self.set_title(_("Gwibber"))
    self.set_default_size(330, 500)
    config.GCONF.add_dir(config.GCONF_PREFERENCES_DIR, config.gconf.CLIENT_PRELOAD_NONE)
    self.preferences = config.Preferences()
    self.last_update = None
    self.last_focus_time = None
    self.last_clear = None
    self._reply_acct = None
    self.indicator_items = {}
    layout = gtk.VBox()

    gtk.rc_parse_string("""
    style "tab-close-button-style" {
      GtkWidget::focus-padding = 0
      GtkWidget::focus-line-width = 0
      xthickness = 0
      ythickness = 0
     }
     widget "*.tab-close-button" style "tab-close-button-style"
     """)

    self.accounts = configui.AccountManager()
    self.client = microblog.Client(self.accounts)
    self.client.handle_error = self.handle_error
    self.client.post_process_message = self.post_process_message

    self.notification_bubbles = {}
    self.message_target = None

    self.errors = table.generate([
      ["date", lambda t: t.time.strftime("%x")],
      ["time", lambda t: t.time.strftime("%X")],
      ["username"],
      ["protocol"],
      ["message", (gtk.CellRendererText(), {
        "markup": lambda t: t.message})]
    ])

    self.connect("delete-event", self.on_window_close)
    self.connect("focus-out-event", self.on_focus_out)
    self.connect("focus-in-event", self.on_focus)

    for key, value in list(DEFAULT_PREFERENCES.items()):
      if self.preferences[key] == None: self.preferences[key] = value

    self.preferences["version"] = VERSION_NUMBER

    self.timer = gobject.timeout_add(60000 * int(self.preferences["refresh_interval"]), self.update)
    self.preferences.notify("refresh_interval", self.on_refresh_interval_changed)
    self.preferences.notify("theme", self.on_theme_change)

    gtk.icon_theme_add_builtin_icon("gwibber", 22,
      gtk.gdk.pixbuf_new_from_file_at_size(
        resources.get_ui_asset("gwibber.svg"), 24, 24))

    self.set_icon_name("gwibber")
    self.tray_icon = gtk.status_icon_new_from_icon_name("gwibber")
    self.tray_icon.connect("activate", self.on_toggle_window_visibility)

    self.tabs = gtk.Notebook()
    self.tabs.set_property("homogeneous", False)
    self.tabs.set_scrollable(True)
    self.messages_view = self.add_msg_tab(self.client.receive, _("Messages"), show_icon = "go-home")
    self.add_msg_tab(self.client.responses, _("Replies"), show_icon = "mail-reply-all", add_indicator=True)

    saved_position = config.GCONF.get_list("%s/%s" % (config.GCONF_PREFERENCES_DIR, "saved_position"), config.gconf.VALUE_INT)
    if saved_position:
      self.move(*saved_position)

    saved_size = config.GCONF.get_list("%s/%s" % (config.GCONF_PREFERENCES_DIR, "saved_size"), config.gconf.VALUE_INT)
    if saved_size:
      self.resize(*saved_size)

    saved_queries = config.GCONF.get_list("%s/%s" % (config.GCONF_PREFERENCES_DIR, "saved_searches"),
      config.gconf.VALUE_STRING)

    if saved_queries:
      for query in saved_queries:
        # XXX: suggest refactor of below code to avoid duplication of on_search code
        if query.startswith("#"):
          self.add_msg_tab(functools.partial(self.client.tag, query),
            query.replace("#", ""), True, gtk.STOCK_INFO, False, query)
        elif microblog.support.LINK_PARSE.match(query):
          self.add_msg_tab(functools.partial(self.client.search_url, query),
            urlparse.urlparse(query)[1], True, gtk.STOCK_FIND, True, query)
        elif len(query) > 0:
          title = _("Search") + " '" + query[:12] + "...'"
          self.add_msg_tab(functools.partial(self.client.search, query),
            title, True, gtk.STOCK_FIND, False, query)

    #self.add_map_tab(self.client.friend_positions, "Location")

    if gintegration.SPELLCHECK_ENABLED:
      self.input = gintegration.sexy.SpellEntry()
      self.input.set_checked(self.preferences["spellcheck_enabled"])
    else: self.input = gtk.Entry()
    self.input.connect("insert-text", self.on_add_text)
    self.input.connect("populate-popup", self.on_input_context_menu)
    self.input.connect("activate", self.on_input_activate)
    self.input.connect("changed", self.on_input_change)
    self.input.set_max_length(MAX_MESSAGE_LENGTH)

    self.cancel_button = gtk.Button(_("Cancel"))
    self.cancel_button.connect("clicked", self.on_cancel_reply)

    self.editor = gtk.HBox()
    self.editor.pack_start(self.input)
    self.editor.pack_start(self.cancel_button, False)

    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.tabs, True, True)
    vb.pack_start(self.editor, False, False)
    vb.set_border_width(5)

    warning_icon = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)
    self.status_icon = gtk.EventBox()
    self.status_icon.add(warning_icon)
    self.status_icon.connect("button-press-event", self.on_errors_show)

    self.statusbar = gtk.Statusbar()
    self.statusbar.pack_start(self.status_icon, False, False)

    layout.pack_start(self.setup_menus(), False)
    layout.pack_start(vb, True, True)
    layout.pack_start(self.statusbar, False)
    self.add(layout)

    if gintegration.can_notify:
      # FIXME: Move this to DBusManager
      import dbus

      # http://galago-project.org/specs/notification/0.9/x408.html#signal-notification-closed
      def on_notify_close(nId, reason = 1):
        if nId in self.notification_bubbles:
          del self.notification_bubbles[nId]

      def on_notify_action(nId, action):
        if action == "reply":
          self.reply(self.notification_bubbles[nId])
          self.window.show()
          self.present()

      bus = dbus.SessionBus()
      bus.add_signal_receiver(on_notify_close,
        dbus_interface="org.freedesktop.Notifications",
        signal_name="NotificationClosed")

      bus.add_signal_receiver(on_notify_action,
        dbus_interface="org.freedesktop.Notifications",
        signal_name="ActionInvoked")

    if indicate:
      self.indicate = indicate.indicate_server_ref_default()
      self.indicate.set_type("message.gwibber")
      self.indicate.set_desktop_file(resources.get_desktop_file())
      self.indicate.connect("server-display", self.on_toggle_window_visibility)
      self.indicate.show()

    for i in list(CONFIGURABLE_UI_ELEMENTS.keys()):
      config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/show_%s" % i,
        lambda *a: self.apply_ui_element_settings())

    config.GCONF.notify_add("/apps/gwibber/accounts", self.on_account_change)

    self.preferences.notify("hide_taskbar_entry",
      lambda *a: self.apply_ui_element_settings())

    self.preferences.notify("spellcheck_enabled",
      lambda *a: self.apply_ui_element_settings())

    #for i in CONFIGURABLE_UI_SETTINGS:
    #  config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/%s" % i,
    #    lambda *a: self.apply_ui_drawing_settings())

    def on_key_press(w, e):
      if e.keyval == gtk.keysyms.F5:
        self.update()
        return True
      if e.keyval == gtk.keysyms.Tab and e.state & gtk.gdk.CONTROL_MASK:
        if len(self.tabs) == self.tabs.get_current_page() + 1:
          self.tabs.set_current_page(0)
        else: self.tabs.next_page()
        return True
      elif e.keyval in [ord(str(x)) for x in range(10)] and e.state & gtk.gdk.MOD1_MASK:
        self.tabs.set_current_page(int(gtk.gdk.keyval_name(e.keyval))-1)
        return True
      elif e.keyval == gtk.keysyms.T and e.state & gtk.gdk.CONTROL_MASK:
        self.on_theme_change()
        return True
      else:
        return False

      #else:
      #  if not self.input.is_focus():
      #    self.input.grab_focus()
      #    self.input.set_position(-1)
      #  return False

    self.connect("key_press_event", on_key_press)

    self.show_all()
    self.apply_ui_element_settings()
    self.cancel_button.hide()
    self.status_icon.hide()

    if not self.preferences["inhibit_startup_refresh"]:
      self.update()

  def on_add_text(self, entry, text, txtlen, pos):
    if self.preferences["shorten_urls"]:
      if text and text.startswith("http") and not " " in text \
          and len(text) > 20:
        # verify url is not already shortened
        for us in urlshorter.PROTOCOLS.keys():
          if text.startswith(urlshorter.PROTOCOLS[us].PROTOCOL_INFO["fqdn"]):
            return
        if text.startswith('http://twitpic.com'):
          return

        entry.stop_emission("insert-text")
        try:
          if not self.preferences["urlshorter"]:
            self.preferences["urlshorter"] = "is.gd"
          self.urlshorter = urlshorter.PROTOCOLS[self.preferences["urlshorter"]].URLShorter()
          short = self.urlshorter.short(text)
        except:
          # Translators: this message appears in the Errors dialog
          # Indicates with which action the error happened
          self.handle_error({"username": "None", "protocol": urlshorter.PROTOCOLS[self.preferences["urlshorter"]].PROTOCOL_INFO["name"]},
            traceback.format_exc(), _("Failed to shorten URL"))
          self.preferences["shorten_urls"] = False
          self.add_url(entry, text)
          self.preferences["shorten_urls"] = True
        else:
          self.add_url(entry, short)

  def add_url(self, entry, text):
    # check if current text is longer than MAX_MESSAGE_LENGTH
    c_text_len=(len(unicode(entry.get_text(), "utf-8")) + len(text))
    # if so increase input.max_length and allow insertion
    if c_text_len > MAX_MESSAGE_LENGTH:
       self.input.set_max_length(c_text_len)
    entry.insert_text(text, entry.get_position())
    gobject.idle_add(lambda: entry.set_position(entry.get_position() + len(text)))

  def on_focus(self, w, change):
    for key, item in self.indicator_items.items():
      #self.indicate.remove_indicator(item)
      item.hide()
    self.indicator_items = {}

  def on_focus_out(self, widget, event):
    if self.last_update:
      self.last_focus_time = self.last_update
    else:
      self.last_focus_time= mx.DateTime.gmt()
    return True

  def on_search(self, *a):
    dialog = gtk.MessageDialog(None,
      gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION,
      gtk.BUTTONS_OK_CANCEL, None)

    entry = gtk.Entry()
    entry.connect("activate", lambda *a: dialog.response(gtk.RESPONSE_OK))

    dialog.set_markup(_("Enter a search query:"))
    dialog.vbox.pack_end(entry, True, True, 0)
    dialog.show_all()
    ret = dialog.run()
    dialog.hide()

    if ret == gtk.RESPONSE_OK:
      query = entry.get_text()
      view = None
      if query.startswith("#"):
        view = self.add_msg_tab(functools.partial(self.client.tag, query),
          query.replace("#", ""), True, gtk.STOCK_INFO, True, query)
      elif microblog.support.LINK_PARSE.match(query):
        view = self.add_msg_tab(functools.partial(self.client.search_url, query),
          urlparse.urlparse(query)[1], True, gtk.STOCK_FIND, True, query)
      elif len(query) > 0:
        title = _("Search") + " '" + query[:12] + "...'"
        view = self.add_msg_tab(functools.partial(self.client.search, query),
          title, True, gtk.STOCK_FIND, True, query)

      if view:
        self.update([view.get_parent()])

  def add_scrolled_parent(self, view, text, show_close=False, show_icon=None, make_active=False, save=None):
    scroll = gtk.ScrolledWindow()
    scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scroll.add(view)
    scroll.saved_query = save

    img = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)

    btn = gtk.Button()
    btn.set_image(img)
    btn.set_relief(gtk.RELIEF_NONE)
    btn.set_name("tab-close-button")

    hb = gtk.HBox(spacing=2)
    if show_icon:
      hb.pack_start(gtk.image_new_from_icon_name(show_icon, gtk.ICON_SIZE_MENU))
    hb.pack_start(gtk.Label(text))
    if show_close: hb.pack_end(btn, False, False)
    hb.show_all()

    self.tabs.append_page(scroll, hb)
    self.tabs.set_tab_reorderable(scroll, True)
    self.tabs.show_all()
    if make_active: self.tabs.set_current_page(self.tabs.page_num(scroll))

    btn.connect("clicked", self.on_tab_close, scroll)

  def add_msg_tab(self, data_handler, text, show_close=False, show_icon=None, make_active=False, save=None, add_indicator=False):
    view = gwui.MessageView(self.preferences["theme"])
    view.link_handler = self.on_link_clicked
    view.data_retrieval_handler = data_handler
    view.config_retrieval_handler = self.get_account_config
    view.add_indicator = add_indicator

    self.add_scrolled_parent(view, text, show_close, show_icon, make_active, save)
    return view

  def add_user_tab(self, data_handler, text, show_close=False, show_icon=None, make_active=False, save=None):
    view = gwui.UserView(self.preferences["theme"])
    view.link_handler = self.on_link_clicked
    view.data_retrieval_handler = data_handler
    view.config_retrieval_handler = self.get_account_config
    view.add_indicator = False

    self.add_scrolled_parent(view, text, show_close, show_icon, make_active, save)
    return view

  def add_map_tab(self, data_handler, text, show_close = True, show_icon = "applications-internet"):
    view = gwui.MapView()
    view.link_handler = self.on_link_clicked
    view.data_retrieval_handler = data_handler
    view.config_retrieval_handler = self.get_account_config
    view.add_indicator = False

    self.add_scrolled_parent(view, text, show_close, show_icon, make_active, save)
    return view

  def on_tab_close(self, w, e):
    pagenum = self.tabs.page_num(e)
    self.tabs.remove_page(pagenum)
    e.destroy()

  def on_tab_close_btn(self, w, *args):
    n = self.tabs.get_current_page()
    if (n > 1):
      self.on_tab_close(w, self.tabs.get_nth_page(n))

  def on_account_change(self, client, junk, entry, *args):
    if "color" in entry.get_key():
      for tab in self.tabs.get_children():
        view = tab.get_child()
        view.load_preferences(self.get_account_config(), self.get_gtk_theme_prefs())

  def on_window_close(self, w, e):
    if self.preferences["minimize_to_tray"]:
      self.preferences["show_tray_icon"] = True
      self.on_toggle_window_visibility(w)
      return True
    else: self.on_quit()

  def on_window_close_btn(self, w, *args):
    self.on_window_close(w, None)

  def on_cancel_reply(self, w, *args):
    self.cancel_button.hide()
    self.message_target = None
    self._reply_acct = None
    self.input.set_text("")

  def on_toggle_window_visibility(self, w):
    if self.get_property("visible"):
      self.last_position = self.get_position()
      self.hide()
    else:
      self.present()
      self.move(*self.last_position)

  def on_indicator_activate(self, w):
    tab_num = w.get_property("gwibber_tab")
    if tab_num is not None:
      self.tabs.set_current_page(int(tab_num))
    visible = self.get_property("visible")
    self.present()
    if not visible:
      self.move(*self.last_position)

  def external_invoke(self):
    logging.info("Invoked by external")
    if not self.get_property("visible"):
      logging.debug("Not visible..")
      self.present()
      self.move(*self.last_position)

  def apply_ui_element_settings(self):
    for i in list(CONFIGURABLE_UI_ELEMENTS.keys()):
      if hasattr(self, i):
        getattr(self, i).set_property(
          "visible", self.preferences["show_%s" % i])

    self.set_property("skip-taskbar-hint",
      self.preferences["hide_taskbar_entry"])

    if gintegration.SPELLCHECK_ENABLED:
      self.input.set_checked(self.preferences["spellcheck_enabled"])

  def on_refresh_interval_changed(self, *a):
    gobject.source_remove(self.timer)
    self.timer = gobject.timeout_add(
      60000 * int(self.preferences["refresh_interval"]), self.update)

  def copy_to_tomboy(self, message):
    gintegration.create_tomboy_note(_("%s message from %s at %s\n\n%s") % (
      message.account["protocol"].capitalize(),
      message.sender, message.time, message.text))

  def reply(self, message):
    acct = message.account
    # store which account we replied to first so we know when not to allow further replies
    if not self._reply_acct:
        self._reply_acct = acct
    if acct.supports(microblog.can.REPLY) and acct==self._reply_acct:
      self.input.grab_focus()
      if hasattr(message, 'is_private') and message.is_private:
        self.input.set_text("d %s " % (message.sender_nick))
      else:
        # Allow replying to more than one person by clicking on the reply button.
        current_text = self.input.get_text()
        # If the current text ends with ": ", strip the ":", it's only taking up space
        text = current_text[:-2] + " " if current_text.endswith(": ") else current_text
        # do not add the nick if it's already in the list
        if not text.count("@%s" % message.sender_nick):
          self.input.set_text("%s@%s%s" % (text, message.sender_nick, self.preferences['reply_append_colon'] and ': ' or ' '))

      self.input.set_position(-1)
      self.message_target = message
      self.cancel_button.show()

    """
    if acct["protocol"] in microblog.PROTOCOLS.keys():
      if hasattr(message.client, "can_reply"):
        view = self.add_msg_tab(lambda: self.client.thread(message), "Jaiku Replies", True)
        view.load_messages()
        view.load_preferences(self.get_account_config())
    """

  def on_link_clicked(self, uri, view):
    if uri.startswith("gwibber:"):
      if uri.startswith("gwibber:reply"):
        self.reply(view.message_store[int(uri.split("/")[-1])])
        return True
      elif uri.startswith("gwibber:search"):
        query = uri.split("/")[-1]
        view = self.add_msg_tab(lambda: self.client.search(query), query, True, gtk.STOCK_FIND, True, query)
        self.update([view.get_parent()])
        return True
      elif uri.startswith("gwibber:tag"):
        query = uri.split("/")[-1]
        view = self.add_msg_tab(lambda: self.client.tag(query),
          query, True, gtk.STOCK_INFO, True, query)
        self.update([view.get_parent()])
        return True
      elif uri.startswith("gwibber:group"):
        query = uri.split("/")[-1]
        view = self.add_msg_tab(lambda: self.client.group(query),
          query, True, gtk.STOCK_INFO, True, query)
        self.update([view.get_parent()])
        return True
      elif uri.startswith("gwibber:thread"):
        msg = view.message_store[int(uri.split("/")[-1])]
        if hasattr(msg, "original_title"): tab_label = msg.original_title
        else: tab_label = msg.text
        t = self.add_msg_tab(lambda: self.client.thread(msg),
          microblog.support.truncate(tab_label), True, "mail-reply-all", True)
        self.update([t.get_parent()])
        return True
      elif uri.startswith("gwibber:user"):
        query = uri.split("/")[-1]
        account_id = uri.split("/")[-2]
        view = self.add_user_tab(lambda: self.client.user_messages(query, account_id),
          query, True, gtk.STOCK_INFO, True)
        self.update([view.get_parent()])
        return True
      elif uri.startswith("gwibber:read"):
        msg = view.message_store[int(uri.split("/")[-1])]
        acct = msg.account
        if acct.supports(microblog.can.READ):
          if(msg.client.read_message(msg)):
            self.update([view.get_parent()])
        else:
          webbrowser.open (msg.url)
        return True
    else: return False

  def on_input_context_menu(self, obj, menu):
    menu.append(gtk.SeparatorMenuItem())
    for acct in self.accounts:
      if acct["protocol"] in list(microblog.PROTOCOLS.keys()):
        if acct.supports(microblog.can.SEND):
          mi = gtk.CheckMenuItem("%s (%s)" % (acct["username"],
            acct.get_protocol().PROTOCOL_INFO["name"]))
          acct.bind(mi, "send_enabled")
          menu.append(mi)

    menu.show_all()

  def on_input_change(self, widget):
    self.statusbar.pop(1)
    if len(widget.get_text()) > 0:
      # get current text length
      i_textlen=len(unicode(widget.get_text(), "utf-8"))
      # if current text is longer than MAX_MESSAGE_LENGTH
      if i_textlen > MAX_MESSAGE_LENGTH:
        # count chars above MAX_MESSAGE_LENGTH
        chars=i_textlen - MAX_MESSAGE_LENGTH
        self.statusbar.push(1, _("Characters remaining: %s" % -chars))
      else:
        # if current input.max_length if bigger then MAX_MESSAGE_LENGTH
        # can reset back to MAX_MESSAGE_LENGTH to prevent typing
        if self.input.get_max_length() > MAX_MESSAGE_LENGTH:
          self.input.set_max_length(MAX_MESSAGE_LENGTH)
        self.statusbar.push(1, _("Characters remaining: %s") % (
        self.input.get_max_length() - i_textlen))

  def on_theme_change(self, *args):
    def on_load_finished(view, frame):
      if len(view.message_store) > 0:
        view.load_messages()
        view.load_preferences(self.get_account_config())

    for tab in self.tabs:
      view = tab.get_child()
      view.connect("load-finished", on_load_finished)
      view.load_theme(self.preferences["theme"])

  def get_themes(self):
    for base in xdg.BaseDirectory.xdg_data_dirs:
      theme_root = os.path.join(base, "gwibber", "ui", "themes")
      if os.path.exists(theme_root):

        for p in os.listdir(theme_root):
          if not p.startswith('.'):
            theme_dir = os.path.join(theme_root, p)
            if os.path.isdir(theme_dir):
              yield theme_dir

  def on_accounts_menu(self, amenu):
    amenu.emit_stop_by_name("select")
    menu = amenu.get_submenu()
    for c in menu: menu.remove(c)

    menuAccountsManage = gtk.MenuItem(_("_Manage"))
    menuAccountsManage.connect("activate", lambda *a: self.accounts.show_account_list())
    menu.append(menuAccountsManage)

    menuAccountsCreate = gtk.MenuItem(_("_Create"))
    menu.append(menuAccountsCreate)
    mac = gtk.Menu()

    for p in list(microblog.PROTOCOLS.keys()):
      mi = gtk.MenuItem("%s" % microblog.PROTOCOLS[p].PROTOCOL_INFO["name"])
      mi.connect("activate", self.accounts.on_account_create, p)
      mac.append(mi)

    menuAccountsCreate.set_submenu(mac)
    menu.append(gtk.SeparatorMenuItem())

    for acct in self.accounts:
      if acct["protocol"] in list(microblog.PROTOCOLS.keys()):
        sm = gtk.Menu()

        for key in list(CONFIGURABLE_ACCOUNT_ACTIONS.keys()):
          if acct.supports(getattr(microblog.can, key.upper())):
            mi = gtk.CheckMenuItem(_(CONFIGURABLE_ACCOUNT_ACTIONS[key]))
            acct.bind(mi, "%s_enabled" % key)
            sm.append(mi)

        sm.append(gtk.SeparatorMenuItem())

        mi = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        mi.connect("activate", lambda w, a: self.accounts.show_properties_dialog(a), acct)
        sm.append(mi)

        if hasattr(acct.get_protocol(), "account_name"):
          aname = acct.get_protocol().account_name(acct)
        elif acct["username"]: aname = acct["username"]
        else: aname = None

        mi = gtk.MenuItem("%s (%s)" % (aname, acct.get_protocol().PROTOCOL_INFO["name"]))
        mi.set_submenu(sm)
        menu.append(mi)
    menu.show_all()
    amenu.set_submenu(menu)

  def setup_menus(self):
    menuGwibber = gtk.Menu()
    menuView = gtk.Menu()
    menuAccounts = gtk.Menu()
    menuHelp = gtk.Menu()

    accelGroup = gtk.AccelGroup()
    self.add_accel_group(accelGroup)

    key, mod = gtk.accelerator_parse("Escape")
    accelGroup.connect_group(key, mod, gtk.ACCEL_VISIBLE, self.on_cancel_reply)

    def create_action(name, accel, stock, fn, parent = menuGwibber):
      mi = gtk.Action("gwibber%s" % name, "%s" % name, None, stock)
      gtk.accel_map_add_entry("<Gwibber>/%s" % name, *gtk.accelerator_parse(accel))
      mi.set_accel_group(accelGroup)
      mi.set_accel_path("<Gwibber>/%s" % name)
      mi.connect("activate", fn)
      parent.append(mi.create_menu_item())
      return mi

    actRefresh = create_action(_("_Refresh"), "<ctrl>R", gtk.STOCK_REFRESH, self.on_refresh)
    actSearch = create_action(_("_Search"), "<ctrl>F", gtk.STOCK_FIND, self.on_search)
    # XXX: actCloseWindow should be disabled (greyed out) when false self.preferences['minimize_to_tray'] as it is the same as quitting
    actCloseWindow = create_action(_("_Close Window"), "<ctrl><shift>W", None, self.on_window_close_btn)
    actCloseTab = create_action(_("_Close Tab"), "<ctrl>W", gtk.STOCK_CLOSE, self.on_tab_close_btn)
    menuGwibber.append(gtk.SeparatorMenuItem())
    actClear = create_action(_("C_lear"), "<ctrl>L", gtk.STOCK_CLEAR, self.on_clear)
    menuGwibber.append(gtk.SeparatorMenuItem())
    actPreferences = create_action(_("_Preferences"), "<ctrl>P", gtk.STOCK_PREFERENCES, self.on_preferences)
    menuGwibber.append(gtk.SeparatorMenuItem())
    actQuit = create_action(_("_Quit"), "<ctrl>Q", gtk.STOCK_QUIT, self.on_quit)

    #actThemeTest = gtk.Action("gwibberThemeTest", "_Theme Test", None, gtk.STOCK_PREFERENCES)
    #actThemeTest.connect("activate", self.theme_preview_test)
    #menuHelp.append(actThemeTest.create_menu_item())

    actHelpOnline = gtk.Action("gwibberHelpOnline", _("Get Help Online..."), None, None)
    actHelpOnline.connect("activate", lambda *a: gintegration.load_url("https://answers.launchpad.net/gwibber"))
    actTranslate = gtk.Action("gwibberTranslate", _("Translate This Application..."), None, None)
    actTranslate.connect("activate", lambda *a: gintegration.load_url("https://translations.launchpad.net/gwibber"))
    actReportProblem = gtk.Action("gwibberReportProblem", _("Report a Problem"), None, None)
    actReportProblem.connect("activate", lambda *a: gintegration.load_url("https://bugs.launchpad.net/gwibber/+filebug"))
    actAbout = gtk.Action("gwibberAbout", _("_About"), None, gtk.STOCK_ABOUT)
    actAbout.connect("activate", self.on_about)

    menuHelp.append(actHelpOnline.create_menu_item())
    menuHelp.append(actTranslate.create_menu_item())
    menuHelp.append(actReportProblem.create_menu_item())
    menuHelp.append(gtk.SeparatorMenuItem())
    menuHelp.append(actAbout.create_menu_item())

    for w, n in list(CONFIGURABLE_UI_ELEMENTS.items()):
      mi = gtk.CheckMenuItem(_(n))
      self.preferences.bind(mi, "show_%s" % w)
      menuView.append(mi)

    if gintegration.SPELLCHECK_ENABLED:
      mi = gtk.CheckMenuItem(_("S_pellcheck"), True)
      self.preferences.bind(mi, "spellcheck_enabled")
      menuView.append(mi)

    mi = gtk.MenuItem(_("E_rrors"))
    mi.connect("activate", self.on_errors_show)
    menuView.append(gtk.SeparatorMenuItem())
    menuView.append(mi)

    menuGwibberItem = gtk.MenuItem(_("_Gwibber"))
    menuGwibberItem.set_submenu(menuGwibber)

    menuViewItem = gtk.MenuItem(_("_View"))
    menuViewItem.set_submenu(menuView)

    menuAccountsItem = gtk.MenuItem(_("_Accounts"))
    menuAccountsItem.set_submenu(menuAccounts)
    menuAccountsItem.connect("select", self.on_accounts_menu)

    menuHelpItem = gtk.MenuItem(_("_Help"))
    menuHelpItem.set_submenu(menuHelp)

    self.throbber = gtk.Image()
    menuSpinner = gtk.ImageMenuItem("")
    menuSpinner.set_right_justified(True)
    menuSpinner.set_sensitive(False)
    menuSpinner.set_image(self.throbber)

    actDisplayBubbles = gtk.CheckMenuItem(_("Display bubbles"))
    self.preferences.bind(actDisplayBubbles, "show_notifications")
    menuTray = gtk.Menu()
    menuTray.append(actDisplayBubbles)
    menuTray.append(actRefresh.create_menu_item())
    menuTray.append(gtk.SeparatorMenuItem())
    menuTray.append(actPreferences.create_menu_item())
    menuTray.append(actAbout.create_menu_item())
    menuTray.append(gtk.SeparatorMenuItem())
    menuTray.append(actQuit.create_menu_item())
    menuTray.show_all()

    self.tray_icon.connect("popup-menu", lambda i, b, a: menuTray.popup(
      None, None, gtk.status_icon_position_menu, b, a, self.tray_icon))

    menubar = gtk.MenuBar()
    menubar.append(menuGwibberItem)
    menubar.append(menuViewItem)
    menubar.append(menuAccountsItem)
    menubar.append(menuHelpItem)
    menubar.append(menuSpinner)
    return menubar

  def on_quit(self, *a):
    config.GCONF.set_list("%s/%s" % (config.GCONF_PREFERENCES_DIR, "saved_position"),
       config.gconf.VALUE_INT, list(self.get_position()))
    config.GCONF.set_list("%s/%s" % (config.GCONF_PREFERENCES_DIR, "saved_size"),
       config.gconf.VALUE_INT, list(self.get_size()))
    config.GCONF.set_list("%s/%s" % (config.GCONF_PREFERENCES_DIR, "saved_searches"),
      config.gconf.VALUE_STRING, [t.saved_query for t in self.tabs if t.saved_query])
    gtk.main_quit()

  def on_refresh(self, *a):
    self.update()

  def on_about(self, mi):
    glade = gtk.glade.XML(resources.get_ui_asset("preferences.glade"))
    dialog = glade.get_widget("about_dialog")
    dialog.set_version(str(VERSION_NUMBER))
    dialog.connect("response", lambda *a: dialog.hide())
    dialog.show_all()

  def on_clear(self, mi):
    self.last_clear = mx.DateTime.gmt()
    for tab in self.tabs.get_children():
      view = tab.get_child()
      view.execute_script("clearMessages()")

  def on_errors_show(self, *args):
    self.status_icon.hide()
    errorwin = gtk.Window()
    errorwin.set_title(_("Errors"))
    errorwin.set_border_width(10)
    errorwin.resize(600, 300)

    def on_row_activate(tree, path, col):
      w = gtk.Window()
      w.set_title(_("Debug Output"))
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
    glade = gtk.glade.XML(resources.get_ui_asset("preferences.glade"))
    dialog = glade.get_widget("pref_dialog")
    dialog.show_all()

    for widget in ["show_notifications", "refresh_interval", "minimize_to_tray", "hide_taskbar_entry", "shorten_urls", "reply_append_colon"]:
      self.preferences.bind(glade.get_widget("pref_%s" % widget), widget)

    self.preferences.bind(glade.get_widget("show_tray_icon"), "show_tray_icon")

    theme_selector = gtk.combo_box_new_text()
    for theme_name in sorted(resources.get_themes()): theme_selector.append_text(theme_name)
    glade.get_widget("containerThemeSelector").pack_start(theme_selector, True, True)

    # reset theme to default if no longer available
    if self.preferences['theme'] not in resources.get_themes():
        config.GCONF.set_string("%s/%s" % (config.GCONF_PREFERENCES_DIR, "theme"),
                config.gconf.VALUE_STRING, 'default')

    self.preferences.bind(theme_selector, "theme")
    theme_selector.show_all()

    # add combo box with url shorter services
    urlshorter_selector = gtk.combo_box_new_text()
    for us in sorted(urlshorter.PROTOCOLS.keys()):
      urlshorter_name = urlshorter.PROTOCOLS[us].PROTOCOL_INFO["name"]
      urlshorter_selector.append_text(urlshorter_name)
    glade.get_widget("containerURLShorterSelector").pack_start(urlshorter_selector, True, True)
    self.preferences.bind(urlshorter_selector, "urlshorter")
    urlshorter_selector.show_all()

    glade.get_widget("button_close").connect("clicked", lambda *a: dialog.destroy())

  def handle_error(self, acct, err, msg = None):
    self.status_icon.show()
    self.errors += {
      "time": mx.DateTime.gmt(),
      "username": acct["username"],
      "protocol": acct["protocol"],
      "message": "%s\n<i><span foreground='red'>%s</span></i>" % (msg, microblog.support.xml_escape(err.split("\n")[-2])),
      "error": err,
    }

  def on_input_activate(self, e):
    text = self.input.get_text().strip()
    if text:
      # don't allow submission if text length is greater than allowed
      if len(text) > MAX_MESSAGE_LENGTH:
         return
      # check if reply and target accordingly
      if self.message_target:
        account = self.message_target.account
        if account:
          # temporarily send_enable the account to allow reply to be posted
          is_send_enabled = account["send_enabled"]
          account["send_enabled"] = True
          if account.supports(microblog.can.THREAD_REPLY) and hasattr(self.message_target, "id"):
            result = self.client.send_thread(text, self.message_target, [account["protocol"]])
          else:
            result = self.client.reply(text, [account["protocol"]])
          # restore send_enabled choice after replying
          account["send_enabled"] = is_send_enabled
      # else standard post
      else:
        result = self.client.send(text, list(microblog.PROTOCOLS.keys()))

      # Strip empties out of the result
      result = [x for x in result if x]

      # if we get returned message info for the posts we should be able
      # to display them to the user immediately
      if result:
        for msg in result:
          if hasattr(msg, 'text'):
            self.post_process_message(msg)
            msg.is_new = msg.is_unread = False
        self.flag_duplicates(result)
        self.messages_view.message_store = result + self.messages_view.message_store
        self.messages_view.load_messages()
        self.messages_view.load_preferences(self.get_account_config(), self.get_gtk_theme_prefs())

      self.on_cancel_reply(None)

  def post_process_message(self, message):
    if hasattr(message, "image"):
      message.image_url = message.image
      message.image_path = gwui.image_cache(message.image_url)
      message.image = "file://%s" % message.image_path

    def remove_url(s):
      return ' '.join([x for x in s.strip('.').split()
        if not x.startswith('http://') and not x.startswith("https://") ])

    if message.text.strip() == "": message.gId = None
    else: message.gId = hashlib.sha1(remove_url(message.text)[:140]).hexdigest()

    message.aId = message.account.id

    if self.last_focus_time:
      message.is_unread = (message.time > self.last_focus_time) or (hasattr(message, "is_unread") and message.is_unread)

    if self.last_update:
      message.is_new = message.time > self.last_update
    else: message.is_new = False

    message.time_string = microblog.support.generate_time_string(message.time)

    if not hasattr(message, "html_string"):
      message.html_string = '<span class="text">%s</span>' % \
        microblog.support.LINK_PARSE.sub('<a href="\\1">\\1</a>', message.text)

    message.can_reply = message.account.supports(microblog.can.REPLY)
    return message

  def get_account_config(self):
    for acct in self.accounts:
      if acct["protocol"] in microblog.PROTOCOLS:
        data = {"id": acct.id, "username": acct["username"], "protocol": acct["protocol"]}
        for c in acct.get_protocol().PROTOCOL_INFO["config"]:
          if "color" in c:
            if acct[c]: color = gtk.gdk.color_parse(acct[c])
            else: color = gtk.gdk.color_parse("#72729f9fcfcf")
            data[c] = {"red": color.red//255, "green": color.green//255, "blue": color.blue//255}
        yield data

  def color_to_dict(self, c):
    color = gtk.gdk.color_parse(c)
    return {"red": color.red//255, "green": color.green//255, "blue": color.blue//255}

  def get_gtk_theme_prefs(self):
    d = {}

    for i in ["base", "text", "fg", "bg"]:
      d[i] = self.color_to_dict(
        getattr(self.get_style(), i)[gtk.STATE_NORMAL].to_string())

      d["%s_selected" % i] = self.color_to_dict(
        getattr(self.get_style(), i)[gtk.STATE_SELECTED].to_string())

    return d

  def show_notification_bubbles(self, messages):
    new_messages = []
    for message in messages:
      if message.is_new and self.preferences["show_notifications"] and \
        message.first_seen and gintegration.can_notify and \
          message.username != message.sender_nick:
          new_messages.append(message)

    new_messages.reverse()
    gtk.gdk.threads_enter()
    if len(new_messages) > 0:
        for index, message in enumerate(new_messages):
            body = microblog.support.xml_escape(message.text)
            image = hasattr(message, "image_path") and message.image_path or ''
            expire_timeout = 5000 + (index*2000) # default to 5 second timeout and increase by 2 second for each notification
            n = gintegration.notify(message.sender, body, image, ["reply", "Reply"], expire_timeout)
            self.notification_bubbles[n] = message
    gtk.gdk.threads_leave()

  def flag_duplicates(self, data):
    seen = []
    for message in data:
      if hasattr(message, "gId"):
        message.is_duplicate = message.gId in seen
        message.first_seen = False
        if not message.is_duplicate:
          message.first_seen = True
          seen.append(message.gId)

  def is_gwibber_active(self):
    screen = wnck.screen_get_default()
    screen.force_update()
    return self.window.xid == screen.get_active_window().get_xid()

  def manage_indicator_items(self, data, tab_num=None):
    if not self.is_gwibber_active():
      for msg in data:
        if hasattr(msg, "first_seen") and msg.first_seen and \
            hasattr(msg, "is_unread") and msg.is_unread and \
            hasattr(msg, "gId") and msg.gId not in self.indicator_items:
          indicator = indicate.IndicatorMessage()
          indicator.set_property("subtype", "im")
          indicator.set_property("sender", msg.sender_nick)
          indicator.set_property("body", msg.text)
          indicator.set_property_time("time", msg.time.gmticks())
          if hasattr(msg, "image_path"):
            pb = gtk.gdk.pixbuf_new_from_file(msg.image_path)
            indicator.set_property_icon("icon", pb)

          if tab_num is not None:
            indicator.set_property("gwibber_tab", str(tab_num))
          indicator.connect("user-display", self.on_indicator_activate)

          self.indicator_items[msg.gId] = indicator
          indicator.show()

  def update(self, tabs = None):
    self.throbber.set_from_animation(
      gtk.gdk.PixbufAnimation(resources.get_ui_asset("progress.gif")))
    self.target_tabs = tabs

    def process():
      try:
        next_update = mx.DateTime.gmt()
        if not self.target_tabs:
          self.target_tabs = self.tabs.get_children()

        for tab in self.target_tabs:
          view = tab.get_child()
          if view:
            view.message_store = [m for m in
              view.data_retrieval_handler() if not self.last_clear or m.time > self.last_clear
              and m.time <= mx.DateTime.gmt()]
            self.flag_duplicates(view.message_store)
            gtk.gdk.threads_enter()
            view.load_messages()
            view.load_preferences(self.get_account_config(), self.get_gtk_theme_prefs())

            if indicate and hasattr(view, "add_indicator") and view.add_indicator:
              self.manage_indicator_items(view.message_store, tab_num=self.tabs.page_num(tab))

            gtk.gdk.threads_leave()
            self.show_notification_bubbles(view.message_store)

        self.statusbar.pop(0)
        self.statusbar.push(0, _("Last update: %s") % time.strftime("%X"))
        self.last_update = next_update

      finally: gobject.idle_add(self.throbber.clear)

    t = threading.Thread(target=process)
    t.setDaemon(True)
    t.start()

    return True

if __name__ == '__main__':
  w = GwibberClient()
  gtk.main()

