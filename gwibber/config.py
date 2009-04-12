
try: import gconf
except: from gnome import gconf

from . import gwp
import microblog
try:
  gnomekeyring = None
  #import gnomekeyring
except:
  gnomekeyring = None

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
    gwp.create_persistency_link(widget, "%s/%s" % (self.path, key), **args)
    return widget

  def notify(self, key, method):
    GCONF.notify_add("%s/%s" % (self.path, key), method)

class Account(Wrapper):
  def __init__(self, id, path = GCONF_ACCOUNTS_DIR):
    Wrapper.__init__(self, path)
    GCONF.add_dir("%s/%s" % (path, id), gconf.CLIENT_PRELOAD_NONE)
    self.id = id

  def __getitem__(self, key):
    if gnomekeyring and key.startswith("private:"):
      try:
        key = key.replace("private:", "")
        return gnomekeyring.find_items_sync(
          gnomekeyring.ITEM_GENERIC_SECRET,
          {"id": "%s/%s/%s" % (self.path, self.id, key)})[0].secret
      except gnomekeyring.NoMatchError:
        print "Couldn't retrieve GConf value for key: %s" % key
        return Wrapper.__getitem__(self, "%s/%s" % (self.id, key))
    else:
      if key.startswith("private:"):
        key = key.replace("private:", "")
      return Wrapper.__getitem__(self, "%s/%s" % (self.id, key))

  def __setitem__(self, key, value):
    if gnomekeyring and key.startswith("private:"):
      key = key.replace("private:", "")

      try:
        token = gnomekeyring.item_create_sync(
          gnomekeyring.get_default_keyring_sync(),
          gnomekeyring.ITEM_GENERIC_SECRET, "Gwibber preference: %s/%s" % (self.id, self.key),
          {"id": "%s/%s/%s" % (self.path, self.id, key)}, value, True)
        Wrapper.__setitem__(self, "%s/%s" % (self.id, key), ":KEYRING:%s" % token)
      except:
        Wrapper.__setitem__(self, "%s/%s" % (self.id, key), value)
    else:
      key = key.replace("private:", "")
      Wrapper.__setitem__(self, "%s/%s" % (self.id, key), value)

  def clear_values(self):
    for entry in GCONF.all_entries("%s/%s" % (self.path, self.id)):
      GCONF.unset(entry.key)

  def bind(self, widget, key, **args):
    return Wrapper.bind(self, widget, "%s/%s" % (self.id, key), **args)

  def notify(self, key, method):
    Wrapper.notify(self, "%s/%s" % (self.id, key), method)

  def get_protocol(self):
    return microblog.PROTOCOLS[self["protocol"]]

  def get_client(self):
    return self.get_protocol().Client(self)

  def supports(self, feature):
    return feature in self.get_protocol().PROTOCOL_INFO["features"]

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
      a = Account(i)
      if a["protocol"] in microblog.PROTOCOLS:
        yield Account(i)

class Preferences(Wrapper):
  def __init__(self, path = GCONF_PREFERENCES_DIR):
    Wrapper.__init__(self, path)
