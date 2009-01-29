
#
# Custom GUI Tree Widgets
#

import gtk, inspect

class Obj:
  def __init__(self, **args):
    self.__dict__.update(args)

class Store(gtk.ListStore):
  def __init__(self):
    gtk.ListStore.__init__(self, object)

  def get_obj(self, iter):
    return self[iter][0]

class Style:
  def __init__(self, cols):
    self.columns = cols
    self.column_types = [str] * len(self.columns)
    
  def generate_column_data(self, model, iter, column, tree):
    i = tree.filter.convert_iter_to_child_iter(iter)
    o = tree.filter.get_model().get_obj(i)

    c = self.columns[column]

    if len(c) <= 1: return getattr(o, c[0])
    elif inspect.isfunction(c[1]): return c[1](o)

  def custom_handler(self, col, cell, model, iter, data):
    fns, tree = data
    i = tree.filter.convert_iter_to_child_iter(iter)
    o = tree.filter.get_model().get_obj(i)

    for k, f in fns.items(): cell.set_property(k, f(o))
    
  def make_columns(self, tree):
    for ci, c in enumerate(self.columns):
      
      if len(c) > 2: name = c[2]
      else: name = c[0].replace("_", " ").title()

      if len(c) > 1 and isinstance(c[1], tuple):
        col = gtk.TreeViewColumn(name, c[1][0])
        col.set_cell_data_func(c[1][0], self.custom_handler, [c[1][1], tree])
      else:
        col = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=ci)
        renderer = gtk.CellRendererText()

      col.set_reorderable(True)
      col.set_resizable(True)
      tree.append_column(col)

class Filter:
  def filter(self, model, iter):
    o = model.get_obj(iter)
    return True

class View(gtk.TreeView):
  def __init__(self, style, store, filter):
    gtk.TreeView.__init__(self, store)
    self.tree_store = store
    self.tree_style = style
    self.tree_filter = filter

    self.filter = self.tree_store.filter_new()
    self.filter.set_visible_func(self.tree_filter.filter)
    self.filter.set_modify_func(self.tree_style.column_types,
        self.tree_style.generate_column_data, self)

    self.set_model(self.filter)
    self.tree_style.make_columns(self)

  def get_selected(self):
    model, iter = self.get_selection().get_selected()
    if not iter: return None
    i = self.filter.convert_iter_to_child_iter(iter)
    return self.filter.get_model().get_obj(i)

  def __iadd__(self, item):
    if isinstance(item, dict): item = Obj(**item)
    self.tree_store.append([item])
    return self

def generate(cols):
  return View(Style(cols), Store(), Filter())
