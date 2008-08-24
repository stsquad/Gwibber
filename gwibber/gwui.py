#!/usr/bin/env python

"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import webkit, gintegration, microblog
import urllib2, hashlib, time, os

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5
IMG_CACHE_DIR = "%s/.gwibber/imgcache" % os.path.expanduser("~")

class WebRender(webkit.WebView):
  def __init__(self, theme):
    webkit.WebView.__init__(self)
    self.open(theme)
    self.connect("navigation-requested", self.on_click_link)
    self.load_externally = True

  def on_click_link(self, view, frame, req):
    uri = req.get_uri()
    if not self.link_handler(uri) and self.load_externally:
      gintegration.load_url(uri)
    return self.load_externally

  def link_handler(self, uri):
    pass

class MessageView(WebRender):
  def __init__(self, theme):
    WebRender.__init__(self, theme)
    self.messages = [None]

  def add(self, message):
    message.message_index = len(self.messages)
    self.messages += [message]
    self.execute_script("addMessage(%s)" % microblog.support.simplejson.dumps(
      message.__dict__, indent=4, default=str))

  def clear(self):
    self.execute_script("clearMessages()")
    self.messages = [None]

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
