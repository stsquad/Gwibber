#!/usr/bin/env python

"""
Flickr interface for Gwibber
SegPhault (Ryan Paul) - 03/01/2008
"""

import urllib2, urllib, base64, simplejson, gtk, os, webbrowser
import time, datetime, gwui, config

API_KEY = "36f660117e6555a9cbda4309cfaf72d0"
REST_SERVER = "http://api.flickr.com/services/rest"
BUDDY_ICON_URL = "http://farm%s.static.flickr.com/%s/buddyicons/%s.jpg"
IMAGE_URL = "http://farm%s.static.flickr.com/%s/%s_%s_%s.jpg"
IMAGE_PAGE_URL = "http://www.flickr.com/photos/%s/%s"

def parse_time(t):
  return datetime.datetime.fromtimestamp(int(t))

class Message:
  def __init__(self, client, data):
    self.client = client
    self.account = client.account
    self.data = data
    self.sender = data["username"]
    self.sender_nick = data["ownername"]
    self.sender_id = data["owner"]
    self.time = parse_time(data["dateupload"])
    self.text = data["title"]
    self.image =  BUDDY_ICON_URL % (data["iconfarm"], data["iconserver"], data["owner"])
    self.bgcolor = "message_color"
    self.url = IMAGE_PAGE_URL % (data["owner"], data["id"])
    self.profile_url = "http://www.flickr.com/people/%s" % (data["owner"])
    self.thumbnail = IMAGE_URL % (data["farm"], data["server"], data["id"], data["secret"], "t")
    self.html_string = """<img src="%s" />""" % self.thumbnail

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

  def restcall(self, method, args):
    return simplejson.loads(self.connect(
      "%s/?api_key=%s&format=json&nojsoncallback=1&method=%s&%s" % (
        REST_SERVER, API_KEY, method, urllib.urlencode(args))))

  def getNSID(self):
    return self.restcall("flickr.people.findByUsername",
      {"username": self.account["username"]})["user"]["nsid"]

  def get_data(self):
    return self.restcall("flickr.photos.getContactsPublicPhotos",
      {"user_id": self.getNSID(), "extras": "date_upload,owner_name,icon_server"})

  def get_messages(self):
    for data in self.get_data()["photos"]["photo"]:
      yield Message(self, data)

class StatusMessage(gwui.StatusMessage):
  def populate_content_block(self):
    b = gwui.StatusMessage.populate_content_block(self)

    img = gwui.glitter.RoundImage()
    img.set_from_file(gwui.image_cache(self.message.thumbnail,
      "%s/.gwibber/flickrcache" % os.path.expanduser("~")))
    
    ev = gtk.EventBox()
    ev.set_visible_window(False)
    ev.add(img)
    ev.connect("button-release-event", lambda *a: webbrowser.open(self.message.url))
    b.pack_start(ev)
    return b

class ConfigPanel(gwui.ConfigPanel):
  def ui_account_info(self):
    f = gwui.ConfigFrame("Account Information")
    t = gtk.Table()
    t.set_col_spacings(5)
    t.set_row_spacings(5)

    t.attach(gtk.Label("Username:"), 0, 1, 0, 1, gtk.SHRINK)
    t.attach(self.account.bind(gtk.Entry(), "username"), 1, 2, 0, 1)
    f.add(t)
    return f

  def ui_account_status(self):
    f = gwui.ConfigFrame("Account Status")
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.account.bind(gtk.CheckButton("Receive Messages"), "receive_enabled"))
    f.add(vb)
    return f
