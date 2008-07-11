#!/usr/bin/env python

"""
Digg interface for Gwibber
SegPhault (Ryan Paul) - 01/06/2008
"""

import urllib2, urllib, base64, simplejson, re
import time, datetime, config, gtk, gwui
from xml.dom import minidom
from gwui import StatusMessage

LINK_PARSE =  re.compile("<a[^>]+href=\"(https?://[^\"]+)\">[^<]+</a>")

def parse_time(t):
  return datetime.datetime.strptime(t,"%a, %d %b %Y %H:%M:%S %Z")

def sanitize_text(t):
  return LINK_PARSE.sub("\\1", t.strip())

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    self.title = data.getElementsByTagName("title")[0].firstChild.nodeValue
    self.sender = data.getElementsByTagName("author")[0].firstChild.nodeValue
    self.sender_nick = self.sender
    self.sender_id = self.sender.replace(" ","_")
    self.time = parse_time(data.getElementsByTagName("pubDate")[0].firstChild.nodeValue)
    self.text = sanitize_text(data.getElementsByTagName("description")[0].firstChild.nodeValue)
    self.pango_markup = "<big><b>%s</b></big><small> (%s)</small>\n<b>%s</b>\n%s" % (
      self.sender, gwui.generate_time_string(self.time), self.title, self.text)
    self.image = "http://digg.com/users/%s/l.png" % self.sender_nick
    self.bgcolor = "digg_color"
    self.url = data.getElementsByTagName("link")[0].firstChild.nodeValue
    self.profile_url = "http://digg.com/users/%s" % self.sender

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

class Digg(Message):
  def __init__(self, client, data):
    Message.__init__(self, client, data)
    self.title = "%s dugg %s" % (self.sender_nick,    
      data.getElementsByTagName("title")[0].firstChild.nodeValue)
    self.bgcolor = "comment_color"

class Client:
  def __init__(self, acct):
    self.account = acct

  def can_send(self): return False
  def can_receive(self): return True

  def send_enabled(self): return False

  def receive_enabled(self):
    return self.account["receive_enabled"] and \
      self.account["username"] != None

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(url, data)).read()

  def get_data(self):
    return minidom.parseString(self.connect(
      "http://digg.com/users/%s/friends/comments.rss" %
        self.account["username"])).getElementsByTagName("item")

  def get_diggs(self):
    return minidom.parseString(self.connect(
      "http://digg.com/users/%s/friends/diggs.rss" %
        self.account["username"])).getElementsByTagName("item")

  def get_messages(self):
    for data in self.get_data()[0:10]:
      yield Message(self, data)

    for data in self.get_diggs()[0:10]:
      yield Digg(self, data)

class ConfigPanel(gwui.ConfigPanel):
  def ui_account_info(self):
    f = gwui.ConfigFrame("Account Information")
    t = gtk.Table()
    t.set_col_spacings(5)
    t.set_row_spacings(5)

    t.attach(gtk.Label("Username:"), 0, 1, 0, 1, gtk.SHRINK)
    t.attach(self.account.bind(gtk.Entry(), "username"), 1, 2, 0, 1)
    f.add(t)
    return f

  def ui_account_status(self):
    f = gwui.ConfigFrame("Account Status")
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.account.bind(gtk.CheckButton("Receive Messages"), "receive_enabled"))
    f.add(vb)
    return f

  def ui_appearance(self):
    f = gwui.ConfigFrame("Appearance")
    t = gtk.Table()
    t.attach(gtk.Label("Digg color:"), 0, 1, 0, 1, gtk.SHRINK)
    t.attach(self.account.bind(gtk.ColorButton(), "digg_color"), 1, 2, 0, 1)
    t.attach(gtk.Label("Comment color:"), 0, 1, 1, 2, gtk.SHRINK)
    t.attach(self.account.bind(gtk.ColorButton(), "comment_color"), 1, 2, 1, 2)
    f.add(t)
    return f

