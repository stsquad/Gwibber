
"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import webkit, gintegration, resources
import urllib2, hashlib, os, simplejson
import Image

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5
IMG_CACHE_DIR = "%s/.gwibber/imgcache" % os.path.expanduser("~")

class MapView(webkit.WebView):
  def __init__(self):
    webkit.WebView.__init__(self)
    self.message_store = []
    self.data_retrieval_handler = None
    self.open("file://%s" % resources.get_ui_asset(map.html))

  def load_theme(self, theme):
    self.theme = theme

  def load_messages(self, message_store = None):
    msgs = message_store or self.message_store
    self.execute_script("LoadMap(%s, %s)" % (msgs[0].location_latitude, msgs[0].location_longitude))
    for m in (message_store or self.message_store):
      self.execute_script("AddPin(%s, %s, '%s', '%s', '%s')" % (m.location_latitude, m.location_longitude, m.sender, m.location_fullname, m.image_small))

  def load_preferences(self, preferences):
    pass

class MessageView(webkit.WebView):
  def __init__(self, theme):
    webkit.WebView.__init__(self)
    self.load_externally = True
    self.connect("navigation-requested", self.on_click_link)
    self.load_theme(theme)
    self.message_store = []
    self.data_retrieval_handler = None

  def load_theme(self, theme):
    self.theme = theme
    self.open(os.path.join("file:/", resources.get_theme_path(theme), "theme.html"))

  def load_messages(self, message_store = None):
    msgs = simplejson.dumps([dict(m.__dict__, message_index=n)
      for n, m in enumerate(message_store or self.message_store)],
        indent=4, default=str)
    self.execute_script("addMessages(%s)" % msgs)

  def load_preferences(self, acct_prefs, theme_prefs=None):
    if theme_prefs:
      theme = simplejson.dumps(theme_prefs, indent=4, default=str)
      self.execute_script("setGtkConfig(%s)" % theme)
    
    acct = simplejson.dumps(list(acct_prefs), indent=4, default=str)
    self.execute_script("setAccountConfig(%s)" % acct)

  def on_click_link(self, view, frame, req):
    uri = req.get_uri()
    if uri.startswith("file:///"): return False
    
    if not self.link_handler(uri, self) and self.load_externally:
      gintegration.load_url(uri)
    return self.load_externally

  def link_handler(self, uri):
    pass

def image_cache(url, cache_dir = IMG_CACHE_DIR):
  if not os.path.exists(cache_dir): os.makedirs(cache_dir)
  encoded_url = hashlib.sha1(url).hexdigest()
  if len(encoded_url) > 200: encoded_url = encoded_url[::-1][:200]
  img_path = os.path.join(cache_dir, encoded_url + '.jpg').replace("\n","")

  if not os.path.exists(img_path):
    output = open(img_path, "w+")
    output.write(urllib2.urlopen(url).read())
    output.close()
    try:
        image = Image.open(img_path)
        (x, y) = image.size
        if x != 48 or y != 48:
            image = image.resize((48, 48), Image.ANTIALIAS)
            image.save(img_path)
    except Exception:
        from traceback import format_exc
        print format_exc()

  return img_path
