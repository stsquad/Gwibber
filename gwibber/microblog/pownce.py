#!/usr/bin/env python

"""

Pownce interface for Gwibber
SegPhault (Ryan Paul) - 03/01/2008

"""

import urllib2, urllib, base64, support
import time, datetime

CONFIG = ["message_color", "comment_color", "password", "username", "receive_enabled", "send_enabled"]
API_KEY = "w5t07ju7t1072o1wfx8l9012a51fdabq"

def parse_time(t):
  return datetime.datetime.utcfromtimestamp(t)

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    self.sender = data["sender"]["first_name"]
    self.sender_nick = data["sender"]["username"]
    self.sender_id = data["sender"]["id"]
    self.time = parse_time(data["timestamp"])
    self.text = data["body"]
    self.image = data["sender"]["profile_photo_urls"]["medium_photo_url"]
    self.bgcolor = "message_color"
    if data.has_key("permalink"):
      self.url = data["permalink"]
    self.profile_url = data["sender"]["permalink"]
    self.id = data["id"]

class Comment(Message):
  def __init__(self, client, data):
    Message.__init__(self, client, data)
    self.bgcolor = "comment_color"

class Client:
  def __init__(self, acct):
    self.account = acct

  def can_send(self): return True
  def can_receive(self): return True
  def can_reply(self): return True

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

  def get_reply_data(self, msg):
    return support.simplejson.loads(self.connect(
      "http://api.pownce.com/2.0/notes/%s.json?app_key=%s&show_replies=true" % (msg.id, API_KEY)))

  def get_replies(self, msg):
    yield msg
    messages = self.get_reply_data(msg)
    if messages.has_key("replies"):
      for data in messages["replies"]:
        yield Comment(self, data)

  def transmit_reply(self, msg, message):
    return self.connect("http://api.pownce.com/2.0/send/reply.json",
        urllib.urlencode({"note_body": message, "app_key": API_KEY, "reply_to": msg.id}))
    
  def get_data(self):
    return support.simplejson.loads(self.connect(
      "http://api.pownce.com/2.0/note_lists/%s.json?app_key=%s" % (self.account["username"], API_KEY)))

  def get_messages(self):
    for data in self.get_data()["notes"]:
      if data["type"] == "message": yield Message(self, data)
      else: yield Comment(self, data)

  def transmit_status(self, message):
    return self.connect("http://api.pownce.com/2.0/send/message.json",
        urllib.urlencode({"note_body":message, "app_key": API_KEY, "note_to": "public"}))

  def transmit_link(self, message):
    return self.connect("http://api.pownce.com/2.0/send/message.json",
        urllib.urlencode({"note_body":message, "app_key": API_KEY, "note_to": "public"}))
