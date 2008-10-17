
"""

Jaiku interface for Gwibber
SegPhault (Ryan Paul) - 01/05/2008

"""

import urllib2, urllib, support, re, can, simplejson

PROTOCOL_INFO = {
  "name": "Jaiku",
  "version": 0.1,
  
  "config": [
    "password",
    "username",
    "message_color",
    "comment_color",
    "receive_enabled",
    "send_enabled"
  ],

  "features": [
    can.SEND,
    can.RECEIVE,
    can.REPLY,
  ],
}

NONCE_PARSE = re.compile('.*_nonce" value="([^"]+)".*', re.M | re.S)

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    if data.has_key("id"): self.id = data["id"]
    self.sender = "%s %s" % (data["user"]["first_name"], data["user"]["last_name"])
    self.sender_nick = data["user"]["nick"]
    self.sender_id = data["user"]["nick"]
    self.time = support.parse_time(data["created_at"])
    if data.has_key("title"):
      self.text = data["title"].replace('"', "&quot;").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    self.image = data["user"]["avatar"]
    self.bgcolor = "message_color"
    self.url = data["url"]
    self.profile_url = "http://%s.jaiku.com" % data["user"]["nick"]
    if data.has_key("icon") and data["icon"] != "": self.icon = data["icon"]

class Comment(Message):
  def __init__(self, client, data):
    Message.__init__(self, client, data)
    self.text = data["content"]
    self.bgcolor = "comment_color"

class Client:
  def __init__(self, acct):
    self.account = acct

  def send_enabled(self):
    return self.account["send_enabled"] and \
      self.account["username"] != None and \
      self.account["password"] != None

  def receive_enabled(self):
    return self.account["receive_enabled"] and \
      self.account["username"] != None and \
      self.account["password"] != None

  def get_messages(self):
    return simplejson.loads(urllib2.urlopen(urllib2.Request(
      "http://%s.jaiku.com/contacts/feed/json" % self.account["username"],
        urllib.urlencode({"user": self.account["username"],
          "personal_key":self.account["password"]}))).read())

  def get_thread_data(self, msg):
    return simplejson.loads(urllib2.urlopen(urllib2.Request(
      "http://%s.jaiku.com/presence/%s/json" % (msg.sender_nick, msg.id),
        urllib.urlencode({"user": self.account["username"],
          "personal_key":self.account["password"]}))).read())

  def get_thread(self, msg):
    yield msg
    for data in self.get_reply_data(msg)["comments"]:
      yield Comment(self, data)

  def receive(self):
    for data in self.get_messages()["stream"]:
      if data.has_key("id"): yield Message(self, data)
      else: yield Comment(self, data)

  def get_nonce(self, msg):
    try:
      page = urllib2.urlopen(urllib2.Request(
        "http://%s.jaiku.com/presence/%s" % (msg.sender_nick, msg.id),
          urllib.urlencode({"user": self.account["username"], 
            "personal_key":self.account["password"]}))).read()
      
      return NONCE_PARSE.match(page, 1).group(1)
    except: return None

  def transmit_reply(self, msg, message):
    nonce = self.get_nonce(msg)
    if nonce:
      return urllib2.urlopen(urllib2.Request(
        "http://%s.jaiku.com/presence/%s" % (msg.sender_nick, msg.id),
          urllib.urlencode({"user": self.account["username"], "_nonce": nonce, 
            "personal_key":self.account["password"], "comment": message}))).read()

  def send(self, message):
    return urllib2.urlopen(urllib2.Request(
      "http://api.jaiku.com/json", urllib.urlencode({"user": self.account["username"],
      "personal_key":self.account["password"],
      "message": message, "method": "presence.send"}))).read()

