#!/usr/bin/env python

"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import gtk, pango, gobject, gintegration
import urllib2, base64, time, datetime, os, cgi, re, webbrowser
from service import twitter

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5
LINK_PARSE = re.compile("(https?://[^ )]+)")

def replace_entities(content):
  # Why isn't there a real function for this in the Python standard libs?
  return content.replace("&quot;",'"').replace("&amp;", "&").replace("&lt", "<").replace("&gt", ">")

def draw_round_rect(c, r, x, y, w, h):
  c.move_to(x+r,y)
  c.line_to(x+w-r,y);   c.curve_to(x+w,y,x+w,y,x+w,y+r)
  c.line_to(x+w,y+h-r); c.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h)
  c.line_to(x+r,y+h);   c.curve_to(x,y+h,x,y+h,x,y+h-r)
  c.line_to(x,y+r);     c.curve_to(x,y,x,y,x+r,y)
  c.close_path()

class RoundRect(gtk.Frame):
  def do_expose_event(self, event):
    self.set_shadow_type(gtk.SHADOW_NONE)
    
    c = self.window.cairo_create()
    c.set_source_color(gtk.TextView().rc_get_style().base[gtk.STATE_ACTIVE])
    draw_round_rect(c, 20, *self.allocation)
    c.fill()
    
    gtk.Frame.do_expose_event(self, event)
    
gobject.type_register(RoundRect)

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
    self.set_cursor_visible(False)
    self.set_accepts_tab(False)

    self.link_offsets = {}
    self.connect("populate-popup", self.on_populate_context_menu)
    self.tname = name; self.tmessage = message; self.tcreated_at = created_at

    #self.modify_base(gtk.STATE_NORMAL,
    #    gtk.Image().rc_get_style().bg[gtk.STATE_NORMAL])
    self.modify_base(gtk.STATE_NORMAL, gtk.TextView().rc_get_style().base[gtk.STATE_ACTIVE])
    self.modify_text(gtk.STATE_NORMAL, gtk.TextView().rc_get_style().text[gtk.STATE_ACTIVE])

    self.new_tag("name", weight=pango.WEIGHT_BOLD, scale=pango.SCALE_LARGE)
    self.new_tag("time", scale=pango.SCALE_SMALL)
    self.new_tag("text", pixels_above_lines=4)
    l = self.new_tag("link", foreground="blue", underline=pango.UNDERLINE_SINGLE)
    l.connect("event", self.tag_event)

    self.add_text(name, "name")
    self.add_text(" (%s)\n" % twitter.parse_time(created_at), "time")

    for item in LINK_PARSE.split(message + " "):
      if item.startswith("https://") or item.startswith("http://"):
        self.link_offsets[self.get_buffer().get_bounds()[1].get_offset()] = item
        self.add_text(item, "link")
      else: self.add_text(replace_entities(item))

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

  def on_populate_context_menu(self, tv, menu):
    if gintegration.service_is_running("org.gnome.Tomboy"):
      mi = gtk.MenuItem("Copy to _Tomboy")
      mi.connect("activate", lambda m: self.copy_to_tomboy())

      menu.append(gtk.SeparatorMenuItem())
      menu.append(mi)
      menu.show_all()

  def copy_to_tomboy(self):
    bus = gintegration.dbus.SessionBus()
    obj = bus.get_object("org.gnome.Tomboy", "/org/gnome/Tomboy/RemoteControl")
    tomboy = gintegration.dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")

    n = tomboy.CreateNamedNote("Tweet from %s at %s" % (self.tname, self.tcreated_at))
    tomboy.SetNoteContents(n, "Tweet from %s at %s\n\n%s" % (
      self.tname, self.tcreated_at, self.tmessage))
    tomboy.DisplayNote(n)

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

  def do_expose_event(self, event):
    x, y, w, h = self.allocation
    
    i = self.get_pixbuf()
    c = self.window.cairo_create()
    c.set_source_pixbuf(i, 0, 0)
    draw_round_rect(c, 20, x, y, i.get_width() - 5, i.get_height() - 5)
    c.fill()

gobject.type_register(UserIcon)

class StatusList(gtk.VBox):
  def __init__(self, data):
    gtk.VBox.__init__(self)
    self.set_spacing(5); self.set_border_width(5)

    for user, status in data:
      hb = gtk.HBox(); hb.set_border_width(5); hb.set_spacing(10)
      hb.set_tooltip_text(user["screen_name"])
      hb.pack_start(UserIcon(user), False, False)
      hb.pack_start(StatusMessage(user["name"], status["text"], status["created_at"]))

      frame = RoundRect(); frame.set_border_width(2)
      ev = gtk.EventBox(); ev.add(hb); frame.add(ev)
      ev.modify_bg(gtk.STATE_NORMAL, gtk.TextView().rc_get_style().base[gtk.STATE_ACTIVE])
      self.pack_start(frame, False, False)
