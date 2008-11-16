
"""

Twitter interface for Gwibber
SegPhault (Ryan Paul) - 12/22/2007

"""

import urllib2, urllib, base64, re, support, can, simplejson

PROTOCOL_INFO = {
  "name": "Twitter",
  "version": 0.1,
  
  "config": [
    "password",
    "username",
    "message_color",
    "receive_enabled",
    "send_enabled",
    "search_enabled",
  ],

  "features": [
    can.SEND,
    can.RECEIVE,
    can.SEARCH,
    can.REPLY,
    can.RESPONSES,
    can.DELETE,
    #can.THREAD,
  ],
}

NICK_PARSE = re.compile("@([A-Za-z0-9_]+)")
HASH_PARSE = re.compile("#([A-Za-z0-9_.\-]+)")

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
    self.text = data["text"]
    self.image = data["user"]["profile_image_url"]
    self.bgcolor = "message_color"
    self.url = "http://twitter.com/%s/statuses/%s" % (data["user"]["screen_name"], data["id"])
    self.profile_url = "http://twitter.com/%s" % data["user"]["screen_name"]
    self.html_string = '<span class="text">%s</span>' % \
        HASH_PARSE.sub('#<a class="inlinehash" href="gwibber:search/#\\1">\\1</a>',
      NICK_PARSE.sub('@<a class="inlinenick" href="http://twitter.com/\\1">\\1</a>',
        support.linkify(self.text)))
    self.is_reply = re.compile("@%s[\W]+|@%s$" % (self.username, self.username)).search(self.text)

class SearchResult:
  def __init__(self, client, data, query = None):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    self.sender = data["from_user"]
    self.sender_nick = data["from_user"]
    self.sender_id = data["from_user_id"]
    self.time = support.parse_time(data["created_at"])
    self.text = data["text"]
    self.image = data["profile_image_url"]
    self.bgcolor = "message_color"
    self.url = "http://twitter.com/%s/statuses/%s" % (data["from_user"], data["id"])
    self.profile_url = "http://twitter.com/%s" % data["from_user"]

    if query: html = support.highlight_search_results(self.text, query)
    else: html = self.text
    
    self.html_string = '<span class="text">%s</span>' % \
      HASH_PARSE.sub('#<a class="inlinehash" href="gwibber:search/#\\1">\\1</a>',
      NICK_PARSE.sub('@<a class="inlinenick" href="http://twitter.com/\\1">\\1</a>',
        support.linkify(self.text)))
    self.is_reply = ("@%s" % self.username) in self.text

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

  def get_auth(self):
    return "Basic %s" % base64.encodestring(
      ("%s:%s" % (self.account["username"], self.account["password"]))).strip()

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(
      url, data, {"Authorization": self.get_auth()})).read()

  def get_message_data(self):
    return simplejson.loads(self.connect(
      "http://twitter.com/statuses/friends_timeline.json"))

  def get_search_data(self, query):
    return simplejson.loads(urllib2.urlopen(
      urllib2.Request("http://search.twitter.com/search.json",
        urllib.urlencode({"q": query}))).read())

  def search(self, query):
    for data in self.get_search_data(query)["results"]:
      yield SearchResult(self, data, query)

  def responses(self):
    for data in self.get_search_data(
      "@%s" % self.account["username"])["results"]:
      yield SearchResult(self, data)

  def receive(self):
    for data in self.get_message_data():
      yield Message(self, data)

  def send(self, message):
    return self.connect("http://twitter.com/statuses/update.json",
        urllib.urlencode({"status":message}))

