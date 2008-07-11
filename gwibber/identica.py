#!/usr/bin/env python

"""
Identica interface for Gwibber
SegPhault (Ryan Paul) - 07/05/2008
"""

import urllib2, urllib, base64, simplejson, re
import time, datetime, config, gtk, gwui
from xml.dom import minidom

from gwui import StatusMessage, ConfigPanel

NICK_PARSE = re.compile("@([A-Za-z0-9]+)")

def parse_time(t):
  return datetime.datetime.strptime(t,"%Y-%m-%dT%H:%M:%S+00:00")

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.protocol = client.account["protocol"]
    self.username = client.account["username"]
    self.data = data
    self.title = data.getElementsByTagName("title")[0].firstChild.nodeValue
    self.sender = data.getElementsByTagName("dc:creator")[0].firstChild.nodeValue
    self.sender_nick = data.getElementsByTagName("description")[0].firstChild.nodeValue.split("'")[0]
    self.sender_id = self.sender_nick
    self.time = parse_time(data.getElementsByTagName("dc:date")[0].firstChild.nodeValue)
    self.text = data.getElementsByTagName("title")[0].firstChild.toxml()
    #self.pango_markup = "<big><b>%s</b></big><small> (%s)</small>\n<b>%s</b>\n%s" % (
    #  self.sender, gwui.generate_time_string(self.time), self.title, self.text)
    self.image = "http://identi.ca/theme/stoica/default-avatar-stream.png" # "http://digg.com/users/%s/l.png" % self.sender_nick
    self.bgcolor = "message_color"
    self.url = data.getElementsByTagName("link")[0].firstChild.nodeValue
    self.profile_url = "http://identi.ca/%s" % self.sender_nick
    self.html_string = '<span class="text">%s</span>' % NICK_PARSE.sub(
      '@<a class="inlinenick" href="http://identi.ca/\\1">\\1</a>', gwui.linkify(self.text))

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

class Client:
  def __init__(self, acct):
    self.account = acct

  def can_send(self): return True
  def can_receive(self): return True

  def send_enabled(self):
    return self.account["send_enabled"] and \
      self.account["username"] != None and \
      self.account["password"] != None

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

  def transmit_status(self, message):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())

    opener.open(urllib2.Request("http://identi.ca/main/login",
      urllib.urlencode({
        "nickname": self.account["username"],
        "password": self.account["password"]}))).read()

    return opener.open(urllib2.Request("http://identi.ca/notice/new",
      urllib.urlencode({"status_textarea": message}))).read()



