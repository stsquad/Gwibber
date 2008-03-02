#!/usr/bin/env python

"""

Gwibber Client Interface Library
SegPhault (Ryan Paul) - 05/26/2007

"""

import gtk, pango, gobject, gintegration, glitter, config
import urllib2, base64, time, datetime, os, re

DEFAULT_UPDATE_INTERVAL = 1000 * 60 * 5
LINK_PARSE = re.compile("(https?://[^ )\n]+)")

def generate_time_string(t):
  d = datetime.datetime(*time.gmtime()[0:6]) - t

  if d.seconds < 60: return "%d seconds ago" % d.seconds
  elif d.seconds < (60 * 60):  return "%d minutes ago" % (d.seconds / 60)
  elif d.seconds < (60 * 60 * 2): return "1 hour ago"
  elif d.days < 1: return "%d hours ago" % (d.seconds / 60 / 60)
  elif d.days == 1: return "1 day ago"
  elif d.days > 0: return "%d days ago" % d.days
  else: return "BUG: %s" % str(d)

def apply_pango_link_style(t, col):
  return LINK_PARSE.sub("<u><span foreground='%s'>\\1</span></u>" % col, t)

def image_cache(url, cache_dir):
  if not os.path.exists(cache_dir): os.makedirs(cache_dir)
  img_path = os.path.join(cache_dir, base64.encodestring(url)[:-1])

  if not os.path.exists(img_path):
    output = open(img_path, "w+")
    output.write(urllib2.urlopen(url).read())
    output.close()

  return img_path

class StatusMessageText(glitter.WrapLabel):
  __gsignals__ = {
      # <- widget, message, link string
      "link-clicked": (gobject.SIGNAL_RUN_FIRST, None, (object, object, object)),
      # <- widget, message
      "right-clicked": (gobject.SIGNAL_RUN_FIRST, None, (object, object))
  }
  def __init__(self, message = None, preferences = None):
    glitter.WrapLabel.__init__(self)
    self.preferences = preferences
    if message: self.populate_data(message)
    self.connect("button-press-event", self.on_button_press)
    self.ev.set_events(gtk.gdk.POINTER_MOTION_MASK)
    self.ev.connect("motion-notify-event", self.on_mouse_notify)
  
  def on_mouse_notify(self, w, e, data = None):
    x,y = self.ev.get_pointer()
    pos = self.pango_layout.xy_to_index(int(x * pango.SCALE), int(y * pango.SCALE))
    _,extents = self.pango_layout.get_extents()
    right_edge = extents[0] + extents[2]
    for match in LINK_PARSE.finditer(self.pango_layout.get_text()):
      lx,ly,lw,lh = self.pango_layout.index_to_pos(match.span()[0])  # start of the link text
      tx,ty,tw,th = self.pango_layout.index_to_pos(match.span()[1])  # end of the link text
      x *= pango.SCALE
      y *= pango.SCALE
      # try to account for wrapped link text here
      if pos[0] in range(*match.span()) and x < right_edge and \
        (y < ty or y > ty and x < tx + tw): 
          self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
      else:
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.LEFT_PTR))

  def populate_data(self, message):
    self.message = message
    if hasattr(message, "pango_markup"):
      self.pango_layout.set_markup("""<span foreground="%s">%s</span>""" % (
          self.preferences["foreground_color"], apply_pango_link_style(message.pango_markup, self.preferences["link_color"])))
    else:
      self.pango_layout.set_markup(
        """<span foreground="%s"><big><b>%s</b></big><small> (%s)</small>\n%s</span>""" % (
        self.preferences["foreground_color"],
        message.sender, generate_time_string(message.time),
        apply_pango_link_style(message.text, self.preferences["link_color"])))

  def on_button_press(self, w, e):
    if e.button == 1:
      pos = self.pango_layout.xy_to_index(int(e.x * pango.SCALE), int(e.y * pango.SCALE))

      for match in LINK_PARSE.finditer(self.pango_layout.get_text()):
        if pos[0] in range(*match.span()):
          self.emit("link-clicked", self, self.message, self.pango_layout.get_text()[match.start():match.end()])
    elif e.button == 3: self.emit("right-clicked", self, self.message)

gobject.type_register(StatusMessageText)

MESSAGE_DRAWING_SETTINGS = ["message_drawing_gradients", "message_drawing_radius", "message_drawing_transparency", "foreground_color", "link_color", "message_text_shadow", "text_shadow_color"]

class StatusMessage(glitter.Frame):
  def __init__(self, message, preferences):
    glitter.Frame.__init__(self)
    self.message = message
    self.set_border_width(5)
    self.apply_visual_settings(preferences)
    
    b = gtk.HBox(spacing=10)
    self.messagetext = StatusMessageText(message, preferences)
    if preferences["message_text_shadow"]:
      self.messagetext.shadow = gtk.gdk.color_parse(preferences["text_shadow_color"])

    b.set_border_width(5)
    b.set_tooltip_text(message.sender_nick)

    imgs = gtk.VBox(spacing=5)

    if hasattr(message, "image"):
      self.usericon = UserIcon(message)
      self.icon_frame = gtk.EventBox()
      self.icon_frame.add(self.usericon)
      self.icon_frame.set_visible_window(False)
      imgs.pack_start(self.icon_frame, False, False)

    self.set_bgcolor(message.account[message.bgcolor])
    message.account.notify(message.bgcolor, lambda *a: self.apply_visual_settings(preferences))

    for i in MESSAGE_DRAWING_SETTINGS:
      config.GCONF.notify_add(config.GCONF_PREFERENCES_DIR + "/%s" % i,
        lambda *a: self.apply_visual_settings(preferences))

    if hasattr(message, "icon"):
      i = gtk.Image()
      i.set_from_file(UserIcon.user_image_path(message, message.icon))
      imgs.pack_start(i, False, False)

    b.pack_start(imgs, False, False)
    b.pack_start(self.populate_content_block())
    self.add(b)

  def populate_content_block(self):
    vb = gtk.VBox()
    vb.pack_start(self.messagetext)
    return vb

  def apply_visual_settings(self, preferences):
    self.set_bgcolor(self.message.account[self.message.bgcolor])
    self.transparency = float(preferences["message_drawing_transparency"]) / 100.0
    self.rounded = preferences["message_drawing_radius"]
    self.show_gradient = preferences["message_drawing_gradients"]
    self.gradient_position = 2.5
    if hasattr(self, "messagetext"):
      self.messagetext.populate_data(self.message)
      if preferences["message_text_shadow"]:
        self.messagetext.shadow = gtk.gdk.color_parse(preferences["text_shadow_color"])
      else: self.messagetext.shadow = None
    if hasattr(self, "usericon"):
      radius = preferences["message_drawing_radius"]
      self.usericon.radius = radius < 40 and radius or 40
      self.usericon.queue_draw()
    self.queue_draw()

class UserIcon(glitter.RoundImage):
  def __init__(self, message):
    glitter.RoundImage.__init__(self)
    self.set_from_file(self.user_image_path(message))

  @classmethod
  def user_image_path(self, message, url=None, cache_dir="%s/.gwibber/imgcache" % os.path.expanduser("~")):
    if url: return image_cache(url, cache_dir)
    else: return image_cache(message.image, cache_dir)
  
gobject.type_register(UserIcon)

def props(w, **args):
  for k,v in args.items(): w.set_property(k,v)
  return w

class ConfigFrame(gtk.Frame):
  def __init__(self, caption=""):
    gtk.Frame.__init__(self)
    self.set_shadow_type(gtk.SHADOW_NONE)
    self.set_property("label-xalign", 0)
    self.label = gtk.Label()
    self.label.set_markup("<b>%s</b>" % caption)
    self.set_label_widget(self.label)
    self.alignment = gtk.Alignment(0.50, 0.50, 1, 1)
    self.alignment.set_padding(5, 0, 12, 0)
    gtk.Frame.add(self, self.alignment)

  def add(self, w): self.alignment.add(w)

class ConfigPanel(gtk.VBox):
  def __init__(self, acct, prefs):
    self.account = acct
    self.preferences = prefs

  def build_ui(self):
    ui = gtk.VBox(spacing=15)
    ui.pack_start(self.ui_account_info())
    ui.pack_start(self.ui_account_status())
    ui.pack_start(self.ui_appearance())
    return self.customize_ui(ui)

  def customize_ui(self, ui):
    return ui

  def ui_account_info(self):
    f = ConfigFrame("Account Information")
    t = gtk.Table()
    t.set_col_spacings(5)
    t.set_row_spacings(5)

    p = gtk.Entry()
    p.set_visibility(False)
    self.account.bind(p, "password")

    t.attach(gtk.Label("Username:"), 0, 1, 0, 1, gtk.SHRINK)
    t.attach(self.account.bind(gtk.Entry(), "username"), 1, 2, 0, 1)
    t.attach(gtk.Label("Password:"), 0, 1, 1, 2, gtk.SHRINK)
    t.attach(p, 1, 2, 1, 2)
    f.add(t)
    return f

  def ui_account_status(self):
    f = ConfigFrame("Account Status")
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.account.bind(gtk.CheckButton("Receive Messages"), "receive_enabled"))
    vb.pack_start(self.account.bind(gtk.CheckButton("Send Messages"), "send_enabled"))
    f.add(vb)
    return f

  def ui_appearance(self):
    f = ConfigFrame("Appearance")
    vb = gtk.VBox(spacing=5)
    vb.pack_start(self.account.bind(gtk.ColorButton(), "message_color", default = "#8e8eb1b1dcdc"))
    f.add(vb)
    return f
