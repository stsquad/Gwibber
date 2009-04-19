"""

FriendFeed interface for Gwibber
SegPhault (Ryan Paul) - 04/18/2009

"""

from . import can, support
import urllib2, urllib, base64, re, simplejson
import gettext
_ = gettext.lgettext


PROTOCOL_INFO = {
  "name": "FriendFeed",
  "version": 0.1,
  
  "config": [
    "private:password",
    "username",
    "message_color",
    "receive_enabled",
    "send_enabled",
    "search_enabled",
    "receive_count",
  ],

  "features": [
    #can.SEND,
    can.RECEIVE,
    can.SEARCH,
    #can.TAG,
    #can.REPLY,
    #can.RESPONSES,
    can.THREAD,
    #can.THREAD_REPLY,
    #can.SEARCH_URL,
    can.USER_MESSAGES,
  ],
}

NICK_PARSE = re.compile("\B@([A-Za-z0-9_]+|@[A-Za-z0-9_]$)")
HASH_PARSE = re.compile("\B#([A-Za-z0-9_\-]+|@[A-Za-z0-9_\-]$)")

class Message:
  def __init__(self, client, data, append_comments=True):
   try:
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.bgcolor = "message_color"
    self.id = data["id"] or ''
    self.time = support.parse_time(data["published"])
    self.is_private  = False

    user = data["user"]

    self.sender = user["name"]
    self.sender_nick = user["nickname"]
    self.sender_id = user["id"]
    #self.sender_location = user["location"]
    #self.sender_followers_count = user["followers_count"]
    self.image = "http://i.friendfeed.com/p-%s-medium-1" % user["id"].replace("-", "")
    self.url = data["link"]
    self.profile_url = "gwibber:user/%s/%s" % (self.account.id, user["nickname"])
    self.external_profile_url = "https://friendfeed.com/%s" % user["nickname"]
    self.sigil = data["service"]["iconUrl"]
    self.can_thread = True

    if data["service"]["id"] == "twitter":
      self.text = data["title"]
      self.html_string = '<span class="text">%s</span>' % (
          HASH_PARSE.sub('#<a class="inlinehash" href="gwibber:tag/\\1">\\1</a>',
          NICK_PARSE.sub('@<a class="inlinenick" href="gwibber:user/'+self.account.id+'/\\1">\\1</a>',
          support.linkify(self.text))))
      self.is_reply = re.compile("@%s[\W]+|@%s$" % (self.username, self.username)).search(self.text)
      self.reply_nick = ''
      self.reply_url = ''
    else:
      self.text = data["title"]
      self.html_string = data["title"]

    if data.has_key("geo"):
      self.geo_position = (data["geo"]["lat"], data["geo"]["long"])

    if data["likes"] != []:
      self.liked_by = [(i["user"]["name"], i["user"]["profileUrl"]) for i in data["likes"]]

    if data["comments"] != [] and append_comments:
      self.comments = [Comment(client, i) for i in data["comments"]]
          
    return

    if data["media"] != []:
      for i in data["media"]:
        if i.has_key("thumbnails") and i["thumbnails"] and len(i["thumbnails"]) > 0:
          self.html_string += """<a href="%s"><img style="margin: 2px;" src="%s" /></a>""" % (
            i["link"], i["thumbnails"][0]["url"])

      if self.html_string != "": self.html_string += "<br />"

   except Exception:
    from traceback import format_exc
    print(format_exc())

class Comment:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.bgcolor = "message_color"

    self.time = support.parse_time(data["date"])
    self.text = data["body"]
    self.sender = data["user"]["name"]
    self.sender_nick = data["user"]["nickname"]
    self.sender_id = data["user"]["id"]
    self.image = "http://i.friendfeed.com/p-%s-medium-1" % data["user"]["id"].replace("-", "")
    self.profile_url =  "https://friendfeed.com/%s" % data["user"]["nickname"]

class SearchResult(Message):
  def __init__(self, client, data, query = None):
    Message.__init__(self, client, data)

class Client:
  def __init__(self, acct):
    self.account = acct

  def send_enabled(self):
    return self.account["send_enabled"] and \
      self.account["username"] != None and \
      self.account["private:password"] != None

  def receive_enabled(self):
    return self.account["receive_enabled"] and \
      self.account["username"] != None and \
      self.account["private:password"] != None

  def get_auth(self):
    return "Basic %s" % base64.encodestring(
      ("%s:%s" % (self.account["username"], self.account["private:password"]))).strip()

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(
      url, data, headers = {"Authorization": self.get_auth()})).read()

  def get_messages(self):
    return simplejson.loads(self.connect(
      "https://friendfeed.com/api/feed/home?" +
      urllib.urlencode({"num": self.account["receive_count"] or "80"})))["entries"]

  def get_user_messages(self, screen_name):
    try:
      return simplejson.loads(self.connect(
        "https://friendfeed.com/api/feed/user/"+ screen_name + "?"+
          urllib.urlencode({"num": self.account["receive_count"] or "20"})))["entries"]
    except Exception:
      return []

  def get_replies(self):
    return simplejson.loads(self.connect(
      "https://twitter.com/statuses/replies.json" +'?'+
        urllib.urlencode({"count": self.account["receive_count"] or "20"})))

  def get_direct_messages(self):
    return simplejson.loads(self.connect(
      "https://twitter.com/direct_messages.json"))

  def get_search_data(self, query):
    return simplejson.loads(urllib2.urlopen(
      urllib2.Request("http://friendfeed.com/api/feed/search?" +
        urllib.urlencode({"q": query}))).read())

  def get_thread_data(self, msg):
    return simplejson.loads(urllib2.urlopen(
      urllib2.Request("http://friendfeed.com/api/feed/entry/" + msg.id + "?" +
        urllib.urlencode({"num": self.account["receive_count"] or "20"}))).read())["entries"]

  def get_thread(self, msg):
    thread_content = self.get_thread_data(msg)
    yield Message(self, thread_content[0], False)
    for data in thread_content[0]["comments"]:
      yield Comment(self, data)

  def search(self, query):
    for data in self.get_search_data(query)["entries"]:
      yield SearchResult(self, data)

  def search_url(self, query):
    urls = support.unshorten_url(query)
    for data in self.get_search_data(" OR ".join(urls))["results"]:
      if any(item in data["text"] for item in urls):
        yield SearchResult(self, data, query)

  def tag(self, query):
    for data in self.get_search_data("#%s" % query)["results"]:
      yield SearchResult(self, data, "#%s" % query)

  def responses(self):
    for data in self.get_replies():
      yield Message(self, data)

    for data in self.get_direct_messages():
      m = Message(self, data)
      m.is_private = True
      yield m

  def receive(self):
    for data in self.get_messages():
      #if data.has_key("geo") or data["likes"] != [] or data["comments"] != []:
      yield Message(self, data)

  def user_messages(self, screen_name):
    for data in self.get_user_messages(screen_name):
      yield Message(self, data)

  def send(self, message):
    data = simplejson.loads(self.connect(
      "https://twitter.com/statuses/update.json",
        urllib.urlencode({"status":message, "source": "gwibbernet"})))
    return Message(self, data)

  def send_thread(self, message, target):
    data = simplejson.loads(self.connect(
      "https://twitter.com/statuses/update.json",
        urllib.urlencode({"status":message,
          "in_reply_to_status_id":target.id, "source": "gwibbernet"})))
    return Message(self, data)

