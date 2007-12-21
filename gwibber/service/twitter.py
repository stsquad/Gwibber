#!/usr/bin/env python

"""

Twitter Python Library
SegPhault (Ryan Paul) - 05/22/2007

"""

PUBLIC_TIMELINE = "public"
FRIENDS_TIMELINE = "friends"
USER_TIMELINE = "user"

import urllib2, urllib, base64, time, datetime, simplejson

def parse_time(t):
  try:
    t = time.strptime(t, "%a %b %d %H:%M:%S +0000 %Y")
    d = datetime.datetime(*time.gmtime()[0:6]) - datetime.datetime(*t[0:6])
  except: return t
  
  if d.seconds < 60: return "%d seconds ago" % d.seconds
  elif d.seconds < (60 * 60):  return "%d minutes ago" % (d.seconds / 60)
  elif d.seconds < (60 * 60 * 2): return "1 hour ago"
  elif d.days < 1: return "%d hours ago" % (d.seconds / 60 / 60)
  elif d.days == 1: return "1 day ago"
  elif d.days > 0: return "%d days ago" % d.days
  else: return "BUG: %s" % str(d)

class Client:
  def __init__(self, user, passwd=None, auth=None):
    self.user = user
    if user and passwd:
      self.auth = "Basic %s" % base64.encodestring("%s:%s" % (user, passwd)).strip()
    else: self.auth = auth

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(
      url, data, {"Authorization": self.auth})).read()

  def get_timeline(self, kind, args = None):
    for status in simplejson.loads(self.connect(
      "http://twitter.com/statuses/%s_timeline.json?%s" % (kind, args or ""))):
      yield status["user"], status

  def friends(self, args = None):
    for user in simplejson.loads(self.connect(
      "http://twitter.com/statuses/friends.json?%s" % args)):
      yield user, user["status"]

  def update_status(self, message):
    return self.connect("http://twitter.com/statuses/update.json",
        urllib.urlencode({"status":message}))


