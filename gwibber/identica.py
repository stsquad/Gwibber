#!/usr/bin/env python

"""
Identica interface for Gwibber
SegPhault (Ryan Paul) - 07/05/2008
"""

import urllib2, urllib, base64, simplejson, re
import time, datetime, config, gtk, gwui
from xml.dom import minidom
from gwui import StatusMessage, ConfigPanel

LINK_PARSE =  re.compile("<a[^>]+href=\"(https?://[^\"]+)\">[^<]+</a>")

def parse_time(t):
  return datetime.datetime.strptime(t,"%Y-%m-%dT%H:%M:%S+00:00")

def sanitize_text(t):
  return LINK_PARSE.sub("\\1", t.strip())

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.data = data
    self.title = data.getElementsByTagName("title")[0].firstChild.nodeValue
    self.sender = data.getElementsByTagName("dc:creator")[0].firstChild.nodeValue
    self.sender_nick = data.getElementsByTagName("description")[0].firstChild.nodeValue.split("'")[0]
    self.sender_id = self.sender_nick
    self.time = parse_time(data.getElementsByTagName("dc:date")[0].firstChild.nodeValue)
    self.text = sanitize_text(data.getElementsByTagName("title")[0].firstChild.nodeValue)
    self.pango_markup = "<big><b>%s</b></big><small> (%s)</small>\n<b>%s</b>\n%s" % (
      self.sender, gwui.generate_time_string(self.time), self.title, self.text)
    self.image = "http://identi.ca/theme/stoica/default-avatar-stream.png" # "http://digg.com/users/%s/l.png" % self.sender_nick
    self.bgcolor = "message_color"
    self.url = data.getElementsByTagName("link")[0].firstChild.nodeValue
    self.profile_url = "http://identi.ca/%s" % self.sender_nick

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

class Client:
  def __init__(self, acct):
    self.account = acct

  def can_send(self): return False
  def can_receive(self): return True

  def send_enabled(self): return False

  def receive_enabled(self):
    return self.account["receive_enabled"] and \
      self.account["username"] != None

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(url, data)).read()

  def get_data(self):
    return minidom.parseString(self.connect(
      "http://identi.ca/%s/all/rss" %
        self.account["username"])).getElementsByTagName("item")

  def get_messages(self):
    for data in self.get_data()[0:10]:
      yield Message(self, data)
