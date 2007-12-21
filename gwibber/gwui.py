#!/usr/bin/env python

"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import gtk, pango, gobject
import urllib2, base64, time, datetime, os, cgi, re, webbrowser
from service import twitter

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5
LINK_PARSE = re.compile("(https?://[^ )]+)")

def replace_entities(content):
  # Why isn't there a real function for this in the Python standard libs?
  return content.replace("&quot;",'"').replace("&amp;", "&").replace("&lt", "<").replace("&gt", ">")

class UpdateManager(gobject.GObject):
  __gsignals__ = {
    "twitter-update-starting": (gobject.SIGNAL_RUN_FIRST, None, (object,)),
    "twitter-update-finished": (gobject.SIGNAL_RUN_FIRST, None, (object,)),
    "twitter-update-nochange": (gobject.SIGNAL_RUN_FIRST, None, (object,)),
    "twitter-update-failed": (gobject.SIGNAL_RUN_FIRST, None, (object,)),
    "twitter-update-change": (gobject.SIGNAL_RUN_FIRST, None, (object,)),
  }
  def __init__(self, twit, interval=DEFAULT_UPDATE_INTERVAL, timeline=twitter.FRIENDS_TIMELINE):
    self.__gobject_init__()
    self.twitter, self.last_update, self.timeline = twit, None, timeline
    self.set_interval(interval)

  def set_interval(self, interval):
    self.refresh_interval = interval
    if hasattr(self, "timeout"): gobject.source_remove(self.timeout)
    self.timeout = gobject.timeout_add(self.refresh_interval, self.update)

  def compare(self):
    if self.last_update and self.data:
      for f in self.data:
        if f == self.last_update[0]: break
        else: yield f

  def update(self):
    if self.twitter:
      self.emit("twitter-update-starting", self)
      try:
        self.data = tuple(self.twitter.get_timeline(self.timeline))
        if self.data == self.last_update: self.emit("twitter-update-nochange", self.data)
        else: self.emit("twitter-update-change", list(self.compare()))
        self.last_update = self.data
      except: self.emit("twitter-update-failed", self)
      self.emit("twitter-update-finished", self.data)
      return True

class StatusMessage(gtk.TextView):
  def __init__(self, name, message, created_at):
    gtk.TextView.__init__(self)
    self.set_wrap_mode(gtk.WRAP_WORD)
    self.set_editable(False)

    self.link_offsets = {}

    self.modify_base(gtk.STATE_NORMAL,
        gtk.Image().rc_get_style().bg[gtk.STATE_NORMAL])

    self.new_tag("name", weight=pango.WEIGHT_BOLD, scale=pango.SCALE_LARGE)
    self.new_tag("time", scale=pango.SCALE_SMALL)
    self.new_tag("text", pixels_above_lines=4)
    l = self.new_tag("link", foreground="blue", underline=pango.UNDERLINE_SINGLE)
    l.connect("event", self.tag_event)

    self.add_text(name, "name")
    self.add_text(" (%s)" % created_at, "time")

    for item in LINK_PARSE.split(message + " "):
      if item.startswith("https://") or item.startswith("http://"):
        self.link_offsets[self.get_buffer().get_bounds()[1].get_offset()] = item
        self.add_text(item, "link")
      else:
        self.add_text(replace_entities(item))

  def tag_event(self, tag, view, ev, iter):
    if ev.type == gtk.gdk.BUTTON_PRESS:
      offset = iter.backward_search(" ", gtk.TEXT_SEARCH_TEXT_ONLY)[0].get_offset() + 1
      webbrowser.open(self.link_offsets[offset])

  def add_text(self, text, tag=None):
    if tag:
      self.get_buffer().insert_with_tags_by_name(
          self.get_buffer().get_bounds()[1], text, tag)
    else: self.get_buffer().insert(self.get_buffer().get_bounds()[1], text)
    
  def new_tag(self, name, **props):
    tag = gtk.TextTag(name)
    for k, v in props.items(): tag.set_property(k, v)
    self.get_buffer().get_tag_table().add(tag)
    return tag

class UserIcon(gtk.Image):
  def __init__(self, user):
    gtk.Image.__init__(self)
    self.set_from_file(self.user_image_path(user))

  @classmethod
  def user_image_path(self, user, cache_dir="%s/.gwibber/imgcache" % os.path.expanduser("~")):
    timestamp = user["profile_image_url"].split("/")[-1].split("?")[-1]
    if not os.path.exists(cache_dir): os.makedirs(cache_dir)
    img_path = os.path.join(cache_dir, "%s-%s" % (user["id"], timestamp))

    if not os.path.exists(img_path):
      output = open(img_path, "w+")
      output.write(urllib2.urlopen(user["profile_image_url"]).read())
      output.close()

    return img_path

class StatusList(gtk.VBox):
  def __init__(self, data):
    gtk.VBox.__init__(self)
    self.set_spacing(5); self.set_border_width(5)

    for user, status in data:
      hb = gtk.HBox(); hb.set_border_width(5); hb.set_spacing(10)
      hb.set_tooltip_text(user["screen_name"])
      hb.pack_start(UserIcon(user), False, False)
      hb.pack_start(StatusMessage(user["name"], status["text"],
        twitter.parse_time(status["created_at"])))

      frame = gtk.Frame(); frame.add(hb)
      self.pack_start(frame, False, False)
