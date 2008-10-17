
"""

Identi.ca interface for Gwibber
SegPhault (Ryan Paul) - 07/18/2008

"""

import urllib2, urllib, base64, re, support, can, simplejson

PROTOCOL_INFO = {
  "name": "Identi.ca",
  "version": 0.1,
  
  "config": [
    "password",
    "username",
    "message_color",
    "receive_enabled",
    "send_enabled"
  ],

  "features": [
    can.SEND,
    can.RECEIVE,
    #can.SEARCH,
    can.REPLY,
    can.RESPONSES,
    can.DELETE,
    #can.THREAD,
  ],
}

NICK_PARSE = re.compile("@([A-Za-z0-9]+)")
HASH_PARSE = re.compile("#([A-Za-z0-9_\-.]+)")

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
    self.time = support.parse_time(data["created_at"])
    self.text = support.xml_escape(data["text"])
    self.image = data["user"]["profile_image_url"]
    self.bgcolor = "message_color"
    self.url = "http://identi.ca/notice/%s" % data["id"] # % (data["user"]["screen_name"], data["id"])
    self.profile_url = "http://identi.ca/%s" % data["user"]["screen_name"]
    self.html_string = '<span class="text">%s</span>' % \
      HASH_PARSE.sub('#<a class="inlinehash" href="http://identi.ca/tag/\\1">\\1</a>',
        NICK_PARSE.sub('@<a class="inlinenick" href="http://identi.ca/\\1">\\1</a>',
          support.linkify(self.text)))
    self.is_reply = ("@%s" % self.username) in self.text

class Client:
  def __init__(self, acct):
    self.account = acct

  def get_auth(self):
    return "Basic %s" % base64.encodestring(
      ("%s:%s" % (self.account["username"], self.account["password"]))).strip()

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(
      url, data, {"Authorization": self.get_auth()})).read()

  def get_messages(self):
    return simplejson.loads(self.connect(
      "http://identi.ca/api/statuses/friends_timeline.json"))

  def get_responses(self):
    return simplejson.loads(self.connect(
      "http://identi.ca/api/statuses/replies.json"))

  def responses(self):
    for data in self.get_responses():
      yield Message(self, data)

  def receive(self):
    for data in self.get_messages():
      yield Message(self, data)

  def send(self, message):
    return self.connect("http://identi.ca/api/statuses/update.json",
        urllib.urlencode({"status":message}))
