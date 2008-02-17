#!/usr/bin/env python

"""
Digg interface for Gwibber
SegPhault (Ryan Paul) - 01/06/2008
"""

import urllib2, urllib, base64, simplejson, re
import time, datetime, config
import gtk, gwui, gintegration
from xml.dom import minidom

LINK_PARSE =  re.compile("<a[^>]+href=\"(http://[^\"]+)\">[^<]+</a>")


def parse_time(t):
  return datetime.datetime.strptime(t,"%a, %d %b %Y %H:%M:%S %Z")

def sanitize_text(t):
  return LINK_PARSE.sub("\\1", t.strip())

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.data = data
    self.title = data.getElementsByTagName("title")[0].firstChild.nodeValue
    self.sender = data.getElementsByTagName("author")[0].firstChild.nodeValue
    self.sender_nick = self.sender
    self.sender_id = self.sender.replace(" ","_")
    self.time = parse_time(data.getElementsByTagName("pubDate")[0].firstChild.nodeValue)
    self.text = sanitize_text(data.getElementsByTagName("description")[0].firstChild.nodeValue)
    self.image = "http://digg.com/users/%s/l.png" % self.sender_nick

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

class Digg(Message):
  def __init__(self, client, data):
    Message.__init__(self, client, data)
    self.title = "%s dugg %s" % (self.sender_nick,    
      data.getElementsByTagName("title")[0].firstChild.nodeValue)

class Client:
  def __init__(self, acct):
    self.account = acct

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(url, data)).read()

  def get_data(self):
    return minidom.parseString(self.connect(
      "http://digg.com/users/%s/friends/comments.rss" %
        self.account["username"])).getElementsByTagName("item")

  def get_diggs(self):
    return minidom.parseString(self.connect(
      "http://digg.com/users/%s/friends/diggs.rss" %
        self.account["username"])).getElementsByTagName("item")

  def get_messages(self):
    for data in self.get_data()[0:10]:
      yield Message(self, data)

    for data in self.get_diggs()[0:10]:
      yield Digg(self, data)

  def account_is_enabled(self):
    return self.account.get_bool("enabled") and \
      self.account["username"] != None

  def transmit_status(self, message):
    pass
    
class StatusMessage(gwui.StatusMessage):
  def __init__(self, message):
    self.bg_color = gtk.gdk.color_parse(
      message.is_new() and "orange" or "orange")
    gwui.StatusMessage.__init__(self, message)


