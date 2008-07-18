#!/usr/bin/env python

"""

Identi.ca interface for Gwibber
SegPhault (Ryan Paul) - 07/18/2008

"""

import urllib2, urllib, base64, simplejson, gtk
import time, datetime, gwui, config, re

from gwui import ConfigPanel

NICK_PARSE = re.compile("@([A-Za-z0-9]+)")

def parse_time(t):
  return datetime.datetime.strptime(t, "%a %b %d %H:%M:%S +0000 %Y")

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    self.sender = data["user"]["name"]
    self.sender_nick = data["user"]["screen_name"]
    self.sender_id = data["user"]["id"]
    self.time = parse_time(data["created_at"])
    self.text = data["text"]
    self.image = data["user"]["profile_image_url"]
    self.bgcolor = "message_color"
    self.url = "http://identi.ca/api/%s/statuses/%s" % (data["user"]["screen_name"], data["id"])
    self.profile_url = "http://identi.ca/api/%s" % data["user"]["screen_name"]
    self.html_string = '<span class="text">%s</span>' % NICK_PARSE.sub(
      '@<a class="inlinenick" href="http://identi.ca/api/\\1">\\1</a>', gwui.linkify(self.text))

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
      "http://identi.ca/api/statuses/friends_timeline.json"))

  def get_messages(self):
    for data in self.get_data():
      yield Message(self, data)

  def transmit_status(self, message):
    return self.connect("http://identi.ca/api/statuses/update.json",
        urllib.urlencode({"status":message}))
