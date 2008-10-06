
"""

Digg interface for Gwibber
SegPhault (Ryan Paul) - 01/06/2008

"""

import urllib2, urllib, support, re, can
from xml.dom import minidom

PROTOCOL_INFO = {
  "name": "Digg",
  "version": 0.1,
  
  "config": [
    "username",
    "digg_color",
    "comment_enabled"
    "receive_enabled",
  ],

  "features": [
    can.RECEIVE,
  ],
}

LINK_PARSE =  re.compile("<a[^>]+href=\"(https?://[^\"]+)\">[^<]+</a>")

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
    self.time = support.parse_time(data.getElementsByTagName("pubDate")[0].firstChild.nodeValue)
    self.text = sanitize_text(data.getElementsByTagName("description")[0].firstChild.nodeValue)
    self.image = "http://digg.com/users/%s/l.png" % self.sender_nick
    self.bgcolor = "comment_color"
    self.url = data.getElementsByTagName("link")[0].firstChild.nodeValue
    self.profile_url = "http://digg.com/users/%s" % self.sender

class Digg(Message):
  def __init__(self, client, data):
    Message.__init__(self, client, data)
    self.title = "%s <small>dugg %s</small>" % (self.sender_nick,    
      data.getElementsByTagName("title")[0].firstChild.nodeValue)
    self.bgcolor = "digg_color"

    self.diggs = support.simplejson.loads(urllib2.urlopen(urllib2.Request(
      "http://services.digg.com/story/%s?appkey=http://cixar.com&type=json" %
        self.url.split("/")[-1])).read())["stories"][0]["diggs"]

class Client:
  def __init__(self, acct):
    self.account = acct

  def receive_enabled(self):
    return self.account["receive_enabled"] and \
      self.account["username"] != None

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(url, data)).read()

  def get_comments(self):
    return minidom.parseString(self.connect(
      "http://digg.com/users/%s/friends/comments.rss" %
        self.account["username"])).getElementsByTagName("item")

  def get_diggs(self):
    return minidom.parseString(self.connect(
      "http://digg.com/users/%s/friends/diggs.rss" %
        self.account["username"])).getElementsByTagName("item")

  def receive(self):
    for data in self.get_comments()[0:10]:
      yield Message(self, data)

    for data in self.get_diggs()[0:10]:
      yield Digg(self, data)


