#!/usr/bin/env python

"""
Facebook interface for Gwibber
SegPhault (Ryan Paul) - 12/22/2007

Based on code by Rudolf Olah
http://web2point0.groups.vox.com/library/post/6a00d414257d066a4700cd972544814cd5.html
"""

import urllib2, urllib, base64, simplejson
import time, datetime, config
import gtk, gwui, gintegration
from xml.dom import minidom

def parse_time(t):
  return datetime.datetime.strptime(
    " ".join(t.split(" ")[0:-1]), "%a, %d %b %Y %H:%M:%S") + \
      datetime.timedelta(hours=int(t.split()[-1][2]))

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.data = data
    self.sender = data.getElementsByTagName("author")[0].firstChild.nodeValue
    self.sender_nick = self.sender
    self.sender_id = self.sender.replace(" ","_")
    self.time = parse_time(data.getElementsByTagName("pubDate")[0].firstChild.nodeValue)
    self.text = data.getElementsByTagName(
        "title")[0].firstChild.nodeValue.replace("%s is " % self.sender, "")
    self.image = None

  def is_new(self):
    return self.time > datetime.datetime(
      *time.strptime(config.Preferences()["last_update"])[0:6])

class Client:
  def __init__(self, acct):
    self.account = acct

  def connect(self, url, data = None):
    return urllib2.urlopen(urllib2.Request(url, data)).read()

  def get_data(self):
    return minidom.parseString(self.connect(
      self.account["feed_url"])).getElementsByTagName("item")

  def get_messages(self):
    for data in self.get_data():
      m = Message(self, data)
      if not m.text.startswith("twittering:"):
        yield m

  def account_is_enabled(self):
    return self.account.get_bool("enabled") and \
      self.account["feed_url"] != None

  def transmit_status(self, message):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    urllib2.install_opener(opener)

    urllib2.urlopen(urllib2.Request(
      "https://login.facebook.com/login.php?m&amp;next=http%3A%2F%2Fm.facebook.com%2Fhome.php",
      "email=%s&pass=%s&login=Login" % (self.user, self.passwd)))

    connection = urllib2.urlopen("http://m.facebook.com/")
    form_id = re.findall('name="post_form_id" value="(\w+)"', connection.read())[0]

    opener.open(urllib2.Request("http://m.facebook.com/home.php",
      "post_form_id=%s&status=%s&update=Update" % (form_id, message)))

class StatusMessage(gwui.StatusMessage):
  def __init__(self, message):
    self.bg_color = gtk.gdk.color_parse(
      message.is_new() and "#ad7fa8" or "#75507b")
    gwui.StatusMessage.__init__(self, message)
