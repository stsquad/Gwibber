#!/usr/bin/env python

"""

Jaiku interface for Gwibber
SegPhault (Ryan Paul) - 01/05/2008

"""

import urllib2, urllib, base64, simplejson
import time, datetime, config, gtk, gwui

from gwui import StatusMessage

def parse_time(t):
  return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S %Z")

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.data = data
    self.sender = "%s %s" % (data["user"]["first_name"], data["user"]["last_name"])
    self.sender_nick = data["user"]["nick"]
    self.sender_id = data["user"]["nick"]
    self.time = parse_time(data["created_at"])
    self.text = data["title"].replace('"', "&quot;").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    self.image = data["user"]["avatar"]
    self.bgcolor = "message_color"
    self.url = data["url"]
    self.profile_url = "http://%s.jaiku.com" % data["user"]["nick"]
    if data.has_key("icon") and data["icon"] != "": self.icon = data["icon"]

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

class Comment(Message):
  def __init__(self, client, data):
    Message.__init__(self, client, data)
    self.text = data["content"]
    self.bgcolor = "comment_color"

class Client:
  def __init__(self, acct):
    self.account = acct

  def can_send(self): return True
  def can_receive(self): return True

  def send_enabled(self):
    return self.account["send_enabled"] and \
      self.account["username"] != None and \
      self.account["password"] != None

  def receive_enabled(self):
    return self.account["receive_enabled"] and \
      self.account["username"] != None and \
      self.account["password"] != None

  def get_data(self):
    return simplejson.loads(urllib2.urlopen(urllib2.Request(
      "http://%s.jaiku.com/contacts/feed/json" % self.account["username"],
        urllib.urlencode({"user": self.account["username"],
          "personal_key":self.account["password"]}))).read())

  def get_messages(self):
    for data in self.get_data()["stream"]:
      if data.has_key("id"): yield Message(self, data)
      else: yield Comment(self, data)

  def transmit_status(self, message):
    return urllib2.urlopen(urllib2.Request(
      "http://api.jaiku.com/json", urllib.urlencode({"user": self.account["username"],
      "personal_key":self.account["password"],
      "message": message, "method": "presence.send"}))).read()

class ConfigPanel(gwui.ConfigPanel):
  def ui_appearance(self):
    f = gwui.ConfigFrame("Appearance")
    t = gtk.Table()
    t.attach(gtk.Label("Message color:"), 0, 1, 0, 1, gtk.SHRINK)
    t.attach(self.account.bind(gtk.ColorButton(), "message_color"), 1, 2, 0, 1)
    t.attach(gtk.Label("Comment color:"), 0, 1, 1, 2, gtk.SHRINK)
    t.attach(self.account.bind(gtk.ColorButton(), "comment_color"), 1, 2, 1, 2)
    f.add(t)
    return f
