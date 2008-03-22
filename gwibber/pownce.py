#!/usr/bin/env python

"""

Pownce interface for Gwibber
SegPhault (Ryan Paul) - 03/01/2008

"""

import urllib2, urllib, base64, simplejson, gtk
import time, datetime, gwui, config

from gwui import StatusMessage, ConfigPanel

API_KEY = "w5t07ju7t1072o1wfx8l9012a51fdabq"

def parse_time(t):
  return datetime.datetime.fromtimestamp(t)

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.data = data
    self.sender = data["sender"]["first_name"]
    self.sender_nick = data["sender"]["username"]
    self.sender_id = data["sender"]["id"]
    self.time = parse_time(data["timestamp"])
    self.text = data["body"]
    self.image = data["sender"]["profile_photo_urls"]["medium_photo_url"]
    self.bgcolor = "message_color"
    self.url = data["permalink"]
    self.profile_url = data["sender"]["permalink"]

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

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

  def get_auth(self):
    return "Basic %s" % base64.encodestring(
      ("%s:%s" % (self.account["username"], self.account["password"]))).strip()

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(
      url, data, {"Authorization": self.get_auth()})).read()

  def get_data(self):
    return simplejson.loads(self.connect(
      "http://api.pownce.com/2.0/note_lists/%s.json?app_key=%s" % (self.account["username"], API_KEY)))

  def get_messages(self):
    for data in self.get_data()["notes"]:
      yield Message(self, data)

  def transmit_status(self, message):
    return self.connect("http://api.pownce.com/2.0/send/message.json",
        urllib.urlencode({"note_body":message, "app_key": API_KEY, "note_to": "public"}))
