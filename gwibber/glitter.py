#!/usr/bin/env python

import gtk, pango, gobject, cairo

def draw_round_rect(c, r, x, y, w, h):
  c.move_to(x+r,y)
  c.line_to(x+w-r,y);   c.curve_to(x+w,y,x+w,y,x+w,y+r)
  c.line_to(x+w,y+h-r); c.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h)
  c.line_to(x+r,y+h);   c.curve_to(x,y+h,x,y+h,x,y+h-r)
  c.line_to(x,y+r);     c.curve_to(x,y,x,y,x+r,y)
  c.close_path()

def color_to_cairo_rgba(c, a = 1):
  return c.red/65535.0, c.green/65535.0, c.blue/65535.0, a

class Frame(gtk.Frame):
  def __init__(self, gradient = None, bgcolor = "white", transparency = 1, rounded=15, gradient_position=2, show_gradient=True):
    self.set_bgcolor(bgcolor)
    self.transparency = transparency
    self.rounded = rounded
    self.gradient = gradient
    self.show_gradient = show_gradient
    self.gradient_position = gradient_position
    gtk.Frame.__init__(self)

  def get_cairo_gradient(self):
    if self.gradient: return gradient
    elif self.bgcolor:
      x,y,w,h = self.allocation
      g = cairo.LinearGradient(0.0, y, 0.0, y + h * self.gradient_position)
      g.add_color_stop_rgba(0, *color_to_cairo_rgba(self.bgcolor, self.transparency))
      if self.show_gradient: g.add_color_stop_rgba(1, 0, 0, 0, 1)
      return g

  def set_bgcolor(self, color):
    if isinstance(color, gtk.gdk.Color): self.bgcolor = color
    elif isinstance(color, str): self.bgcolor = gtk.gdk.color_parse(color)

  def do_expose_event(self, event):
    self.set_shadow_type(gtk.SHADOW_NONE)
    x,y,w,h = self.allocation

    c = self.window.cairo_create()
    c.set_source(self.get_cairo_gradient())

    draw_round_rect(c, self.rounded, *self.allocation)
    c.fill()
    
    gtk.Frame.do_expose_event(self, event)
    
gobject.type_register(Frame)

class WrapLabel(gtk.Frame):
  def __init__(self, markup = None, text = None, shadow = None):
    gtk.Frame.__init__(self)
    self.set_shadow_type(gtk.SHADOW_NONE)
    self.shadow = shadow

    self.pango_layout = self.create_pango_layout(text or "")
    if markup: self.pango_layout.set_markup(markup)
    self.pango_layout.set_wrap(pango.WRAP_WORD_CHAR)
    
    self.ev = gtk.EventBox()
    self.ev.set_visible_window(False)
    self.add(self.ev)

  def do_expose_event(self, event):
    gtk.Frame.do_expose_event(self, event)
    self.set_size_request(-1, (self.pango_layout.get_size()[1] // pango.SCALE + 10))

    x,y,w,h = self.allocation
    
    gc = self.window.new_gc()
    self.pango_layout.set_width(w * pango.SCALE)
    
    if self.shadow:
      shadow = self.pango_layout.copy()
      attrs = shadow.get_attributes()
      attrs.change(pango.AttrForeground(self.shadow.red, self.shadow.green, self.shadow.blue, 0, -1))
      shadow.set_attributes(attrs)
      self.window.draw_layout(gc, x + 1, y + 1, shadow)

    self.window.draw_layout(gc, x, y, self.pango_layout)

gobject.type_register(WrapLabel)

class RoundImage(gtk.Image):
  def __init__(self, radius = 15):
    self.radius = 15
    gtk.Image.__init__(self)

  def do_expose_event(self, event):
    x, y, w, h = self.allocation
    i = self.get_pixbuf()
    c = self.window.cairo_create()

    #c.set_source_rgba(0, 0, 0, 0.5)
    #draw_round_rect(c, 15, x + 3, y + 3, i.get_width(), i.get_height())
    #c.fill()
    
    c.set_source_pixbuf(i, x, y)
    draw_round_rect(c, self.radius, x, y, i.get_width(), i.get_height())
    c.fill()

gobject.type_register(RoundImage)

class CompositedWindow(gtk.Window):
  def __init__(self, *a):
    gtk.Window.__init__(self, *a)
    
    self.connect("expose-event", self.on_expose)
    self.connect("screen-changed", self.screen_changed)
    self.set_app_paintable(True)
    self.screen_changed(self)

  def screen_changed(self, w, old_screen=None):
    screen = w.get_screen()
    cma = screen.get_rgba_colormap()
    w.set_colormap(cma)

  def on_expose(self, w, e):
    cr = w.window.cairo_create()
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.paint()

if __name__ == "__main__":
  w = CompositedWindow()
  w.connect("destroy", gtk.main_quit)
  f = Frame(bgcolor="red", transparency=0.8)
  l = WrapLabel(markup="<b>This is a test</b>")
  f.add(l)
  w.add(f)
  w.show_all()
  gtk.main()

