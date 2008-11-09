
"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import webkit, gintegration, microblog, gtk
import urllib2, hashlib, time, os, simplejson

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5
IMG_CACHE_DIR = "%s/.gwibber/imgcache" % os.path.expanduser("~")

class MapView(webkit.WebView):
  def __init__(self, ui_dir):
    webkit.WebView.__init__(self)
    self.ui_dir = ui_dir
    self.message_store = []
    self.data_retrieval_handler = None
    self.open("file://%s/map.html" % self.ui_dir)

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
  def __init__(self, ui_dir, theme):
    webkit.WebView.__init__(self)
    self.ui_dir = ui_dir
    self.load_externally = True
    self.connect("navigation-requested", self.on_click_link)
    self.load_theme(theme)
    self.message_store = []
    self.data_retrieval_handler = None

  def load_theme(self, theme):
    self.theme = theme
    self.open("file://%s/themes/%s/theme.html" % (self.ui_dir, theme))

  def load_messages(self, message_store = None):
    msgs = simplejson.dumps([dict(m.__dict__, message_index=n)
      for n, m in enumerate(message_store or self.message_store)],
        indent=4, default=str)
    self.execute_script("addMessages(%s)" % msgs)

  def load_preferences(self, preferences):
    json = simplejson.dumps(
      list(preferences), indent=4, default=str)
    self.execute_script("setAccountConfig(%s)" % json)

  def on_click_link(self, view, frame, req):
    uri = req.get_uri()
    if uri.startswith("file:///"): return False
    
    if not self.link_handler(uri, self) and self.load_externally:
      gintegration.load_url(uri)
    return self.load_externally

  def link_handler(self, uri):
    pass

class ThemeSelector:
  def __init__(self, ui_dir, theme):
    self.theme = theme

    self.widgets = gtk.VBox()
    self.content = MessageView(ui_dir, theme)
    self.selector = gtk.RadioButton(None, theme.capitalize())

    self.widgets.pack_start(self.content)
    self.widgets.pack_start(self.selector, False, False)

    self.content.set_full_content_zoom(True)
    self.content.set_zoom_level(0.2)

def image_cache(url, cache_dir = IMG_CACHE_DIR):
  if not os.path.exists(cache_dir): os.makedirs(cache_dir)
  encoded_url = hashlib.sha1(url).hexdigest()
  if len(encoded_url) > 200: encoded_url = encoded_url[::-1][:200]
  img_path = os.path.join(cache_dir, encoded_url).replace("\n","")

  if not os.path.exists(img_path):
    output = open(img_path, "w+")
    output.write(urllib2.urlopen(url).read())
    output.close()

  return img_path
