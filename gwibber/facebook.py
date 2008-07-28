#!/usr/bin/env python

"""
Facebook interface for Gwibber
SegPhault (Ryan Paul) - 12/22/2007
"""

import urllib2, urllib, base64, simplejson, re, webbrowser
import time, datetime, config, gtk, gwui, facelib
from xml.dom import minidom

from gwui import StatusMessage

APP_KEY = "71b85c6d8cb5bbb9f1a3f8bbdcdd4b05"
SECRET_KEY = "41e43c90f429a21e55c7ff67aa0dc201"
LINK_PARSE =  re.compile("<a[^>]+href=\"(https?://[^\"]+)\">[^<]+</a>")

def sanitize_text(t):
  return LINK_PARSE.sub("\\1", t.strip()).replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")

def parse_time(t):
  return datetime.datetime.strptime(
    " ".join(t.split(" ")[0:-1]), "%a, %d %b %Y %H:%M:%S") + \
      datetime.timedelta(hours=int(t.split()[-1][2]))

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    self.sender = data.getElementsByTagName("author")[0].firstChild.nodeValue
    self.sender_nick = self.sender
    self.sender_id = self.sender.replace(" ","_")
    self.time = parse_time(data.getElementsByTagName("pubDate")[0].firstChild.nodeValue)
    self.text = sanitize_text(data.getElementsByTagName("title")[0].firstChild.nodeValue)
    self.url = data.getElementsByTagName("link")[0].firstChild.nodeValue
    self.bgcolor = "message_color"
    
    if self.client.profile_images.has_key(self.sender):
      self.image = self.client.profile_images[self.sender]
    else: self.image = "http://digg.com/img/udl.png"

    self.profile_url = "http://www.facebook.com"

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

class Client:
  def __init__(self, acct):
    self.account = acct
    self.profile_images = {}
    
    self.facebook = facelib.Facebook(APP_KEY, SECRET_KEY)
    self.facebook.session_key = self.account["session_key"]
    self.facebook.secret = self.account["secret_key"]

  def get_images(self):
    friends = self.facebook.users.getInfo(self.facebook.friends.get(), ['name', 'pic_square'])
    return dict((f["name"], f["pic_square"]) for f in friends if f["pic_square"])

  def can_send(self): return True
  def can_receive(self): return True

  def send_enabled(self):
    return self.account["send_enabled"] and \
      self.account["session_key"] != None and \
      self.account["secret_key"] != None

  def receive_enabled(self):
    return self.account["receive_enabled"] and \
      self.account["feed_url"] != None

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(url, data)).read()

  def get_data(self):
    return minidom.parseString(self.connect(
      self.account["feed_url"])).getElementsByTagName("item")

  def get_messages(self):
    self.profile_images = self.get_images()
    for data in self.get_data():
      yield Message(self, data)

  def transmit_status(self, message):
    self.facebook.users.setStatus(message, False)


class ConfigPanel(gwui.ConfigPanel):
  def authorize(self):
    glade = gtk.glade.XML("%s/preferences.glade" % self.ui_dir)
    dialog = glade.get_widget("facebook_config")
    dialog.show_all()

    def on_validate_click(w):
      fb = facelib.Facebook(APP_KEY, SECRET_KEY,
        glade.get_widget("entry_auth_token").get_text().strip())

      data = fb.auth.getSession()
      if data and data.has_key("session_key"):
        self.account["secret_key"] = str(data["secret"])
        self.account["session_key"] = str(data["session_key"])
        
        m = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "Keys obtained successfully.")
      else:
        m = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to obtain key.") 

      m.run()
      m.destroy()

    glade.get_widget("button_request").connect("clicked",
      lambda *a: webbrowser.open("http://www.facebook.com/code_gen.php?v=1.0&api_key=%s" % APP_KEY))
    
    glade.get_widget("button_authorize").connect("clicked",
      lambda *a: webbrowser.open("http://www.facebook.com/authorize.php?api_key=%s&v=1.0&ext_perm=status_update" % APP_KEY))

    glade.get_widget("button_apply_auth").connect("clicked", on_validate_click)
    glade.get_widget("button_close_facebook_auth").connect("clicked", lambda w: dialog.destroy())

  def ui_account_info(self):
    f = gwui.ConfigFrame("Account Information")
    t = gtk.Table()
    t.set_col_spacings(5)
    t.set_row_spacings(5)

    auth_start = gtk.Button("Authorize Gwibber")
    auth_start.connect("clicked", lambda *a: self.authorize())

    t.attach(auth_start, 0, 2, 0, 1)
    t.attach(gtk.Label("Feed URL:"), 0, 1, 1, 2, gtk.SHRINK)
    t.attach(self.account.bind(gtk.Entry(), "feed_url"), 1, 2, 1, 2)
    f.add(t)
    return f
