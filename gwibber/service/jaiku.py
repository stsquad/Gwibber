#!/usr/bin/env python

"""

Jaiku Python Library
SegPhault (Ryan Paul) - 05/27/2007

"""

import urllib2, urllib, simplejson

class Client:
  def __init__(self, user, key):
    self.user = user
    self.key = key

  def update_status(self, message):
    return urllib2.urlopen(urllib2.Request(
      "http://api.jaiku.com/json", urllib.urlencode({"user": self.user,
        "personal_key":self.key, "message": message, "method": "presence.send"}))).read()
