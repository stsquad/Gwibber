#!/usr/bin/env python

try: import gconf
except: from gnome import gconf

import gtk, gwp

GCONF_DIR = "/apps/gwibber"
GCONF_PREFERENCES_DIR = GCONF_DIR + "/preferences"
GCONF_ACCOUNTS_DIR = GCONF_DIR + "/accounts"
GCONF = gconf.client_get_default()

class Wrapper:
  def __init__(self, path):
    self.path = path

  def __getitem__(self, key):
    value = GCONF.get("%s/%s" % (self.path, key))

    if value:
      return {
        "string": value.get_string,
        "int": value.get_int,
        "float": value.get_float,
        "bool": value.get_bool}[value.type.value_nick]()
    else:
      return None

  def __setitem__(self, key, value):
    { "str": GCONF.set_string,
      "int": GCONF.set_int,
      "float": GCONF.set_float,
      "bool": GCONF.set_bool}[type(value).__name__](
        "%s/%s" % (self.path, key), value)

  def bind(self, widget, key, **args):
    gwp.create_persistency_link(widget, "%s/%s" % (self.path, key))
    return widget

  def notify(self, key, method):
    GCONF.notify_add("%s/%s" % (self.path, key), method)

class Account(Wrapper):
  def __init__(self, id, path = GCONF_ACCOUNTS_DIR):
    Wrapper.__init__(self, path)
    GCONF.add_dir("%s/%s" % (path, id), gconf.CLIENT_PRELOAD_NONE)
    self.id = id

  def __getitem__(self, key):
    return Wrapper.__getitem__(self, "%s/%s" % (self.id, key))

  def __setitem__(self, key, value):
    Wrapper.__setitem__(self, "%s/%s" % (self.id, key), value)

  def clear_values(self):
    for entry in GCONF.all_entries("%s/%s" % (self.path, self.id)):
      GCONF.unset(entry.key)

  def bind(self, widget, key, **args):
    return Wrapper.bind(self, widget, "%s/%s" % (self.id, key), **args)

  def notify(self, key, method):
    Wrapper.notify(self, "%s/%s" % (self.id, key), method)

class Accounts:
  def __init__(self, path = GCONF_ACCOUNTS_DIR):
    self.path = path

  def new_account(self):
    id = gconf.unique_key()
    index = GCONF.get_list("%s/index" % self.path, gconf.VALUE_STRING)
    index.append(id)
    GCONF.set_list("%s/index" % self.path, gconf.VALUE_STRING, index)

    return Account(id, self.path)

  def delete_account(self, arg):
    index = GCONF.get_list("%s/index" % self.path, gconf.VALUE_STRING)
    index.remove(isinstance(arg, Account) and arg.id or arg)
    GCONF.set_list("%s/index" % self.path, gconf.VALUE_STRING, index)
    
    if isinstance(arg, Account): arg.clear_values()
    else: Account(id, self.path).clear_values()

  def __iter__(self):
    for i in GCONF.get_list("%s/index" % self.path, gconf.VALUE_STRING):
      yield Account(i)

class Preferences(Wrapper):
  def __init__(self, path = GCONF_PREFERENCES_DIR):
    Wrapper.__init__(self, path)

if __name__ == "__main__":
  import gtk, twitter

  acct = [a for a in Accounts() if a["protocol"] == "twitter"][0]
 
  c = twitter.ConfigPanel(acct, Preferences())

  w = gtk.Window()
  w.set_border_width(10)
  w.connect("destroy", gtk.main_quit)
  w.add(c.build_ui())
  w.show_all()

  gtk.main()

  """
  u = gtk.Entry()
  acct.bind(u, "username")

  c = gtk.CheckButton("Receive")
  acct.bind(c, "receive_enabled")

  vb = gtk.VBox()
  vb.pack_start(u)
  vb.pack_start(c)
  
  w = gtk.Window()
  w.connect("destroy", gtk.main_quit)
  w.add(vb)
  w.show_all()

  gtk.main()
  """


  #w = Wrapper("/apps/gwibber2/preferences")
  #w["message_drawing_radius"] = 15
  #w["show_messages"] = True

  #v = gconf.value_new_from_string(get_gconf_type(5), str(5))
  #print eval(v.to_string())

  #for a in Accounts(): print a["username"]
  #a = Accounts().new_account()
  #a["username"] = "segphault"
  #a["protocol"] = "digg"

  #x = [a for a in Accounts() if a["username"] == "test"][0]
  #Accounts().delete_account(x.id)
  # Preferences()["last_update"] = "Sat Dec 22 19:36:38 2007"
