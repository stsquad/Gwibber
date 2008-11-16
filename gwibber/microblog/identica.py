
"""

Identi.ca interface for Gwibber
SegPhault (Ryan Paul) - 07/18/2008

"""

import urllib2, urllib, base64, re, support, can, simplejson
from xml.dom import minidom

PROTOCOL_INFO = {
  "name": "Identi.ca",
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
        HASH_PARSE.sub('#<a class="inlinehash" href="gwibber:search/#\\1">\\1</a>',
        NICK_PARSE.sub('@<a class="inlinenick" href="http://identi.ca/\\1">\\1</a>',
          support.linkify(self.text)))
    self.is_reply = re.compile("@%s[\W]+|@%s$" % (self.username, self.username)).search(self.text)

class SearchResult:
  def __init__(self, client, data, query = None):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    self.sender = data.getElementsByTagName("dc:creator")[0].firstChild.nodeValue
    self.sender_nick = data.getElementsByTagName("title")[0].firstChild.nodeValue.split(":")[0]
    self.sender_id = self.sender_nick
    self.time = support.parse_time(data.getElementsByTagName("dc:date")[0].firstChild.nodeValue)
    self.text = data.getElementsByTagName("title")[0].firstChild.nodeValue.split(":", 1)[1].strip()
    self.image = data.getElementsByTagName("laconica:postIcon")[0].getAttribute("rdf:resource").replace("-96-", "-48-")
    self.bgcolor = "message_color"
    self.url = data.getAttribute("rdf:about")
    self.profile_url = data.getElementsByTagName("sioc:has_creator")[0].getAttribute("rdf:resource")

    self.html_string = '<span class="text">%s</span>' % \
        HASH_PARSE.sub('#<a class="inlinehash" href="gwibber:search/#\\1">\\1</a>',
        NICK_PARSE.sub('@<a class="inlinenick" href="http://identi.ca/\\1">\\1</a>',
          support.linkify(self.text)))
    self.is_reply = re.compile("@%s[\W]+|@%s$" % (self.username, self.username)).search(self.text)

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

  def get_search(self, query):
    return minidom.parseString(urllib2.urlopen(
      urllib2.Request("http://identi.ca/search/notice/rss",
        urllib.urlencode({"q": query}))).read()).getElementsByTagName("item")

  def search(self, query):
    for data in self.get_search(query):
      yield SearchResult(self, data, query)

  def responses(self):
    for data in self.get_responses():
      yield Message(self, data)

  def receive(self):
    for data in self.get_messages():
      yield Message(self, data)

  def send(self, message):
    return self.connect("http://identi.ca/api/statuses/update.json",
        urllib.urlencode({"status":message}))
