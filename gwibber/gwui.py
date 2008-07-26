#!/usr/bin/env python

"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import gtk, pango, gobject, gintegration, config
import webkit, webbrowser, simplejson
import urllib2, base64, time, datetime, os, re

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5

class WebRender(webkit.WebView):
  def __init__(self, theme):
    webkit.WebView.__init__(self)
    self.open(theme)
    self.connect("navigation-requested", self.on_click_link)
    self.load_externally = True

  def on_click_link(self, view, frame, req):
    uri = req.get_uri()
    if not self.link_handler(uri) and self.load_externally:
      webbrowser.open(uri)
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
    self.execute_script("addMessage(%s)" % simplejson.dumps(
      message.__dict__, indent=4, default=str))

  def clear(self):
    self.execute_script("clearMessages()")
    self.messages = [None]
