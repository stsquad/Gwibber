__doc__ = """
GConf Widget Persistency is a module for maintaining persistency between your
existing widgets and the GConf keys. Not only it forces the schema you've
defined for the key but also preserves the widget state, for example making it
insensitive when the GConf key is insensitive.

It also implements a representation of a gconf key(GConfValue) that handles
the repetitive hassles of a maintaining its integrity.

Use the L{create_persistency_link} function to create persistency links between
your widget and a gconf value. The signature of the function changes according
the first argument:
    
    * gtk.FileChooserButton:(button, key, use_directory=False, use_uri=True, *args, **kwargs)
    * gtk.Entry:(entry, key, data_spec = Spec.STRING, *args, **kwargs)
    * gtk.SpinButton:(spinbutton, key, use_int = True, *args, **kwargs)
    * gtk.ToggleButton:(toggle, key, *args, **kwargs)

You can add new handlers to the L{create_persistency_link} function like this::

    import gwp
    gwp.create_persistency_link.append_handler(SomeClass, my_handler)
    
C{my_handler} should be a function that returns a L{PersistencyLink} 

Here's a simple example on how to use it::

    from rat import gwp
    import gtk
    import gconf
    # Monitor the key, so gaw can listen for gconf events
    gconf.client_get_default().add_dir("/apps/gaw", gconf.CLIENT_PRELOAD_NONE)

    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    entry = gtk.Entry()
    entry.show()
    # bind the key with the widget
    link = gwp.create_persistency_link(entry, "/apps/gaw/str_key")
    win.add(entry)
    win.show()
    gtk.main()            

"""
__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__author__ = "Tiago Cogumbreiro <cogumbreiro@users.sf.net>"
__copyright__ = "Copyright 2005, Tiago Cogumbreiro"

import gconf
import gobject
import gtk
try:
  import gnomekeyring
except: pass

from swp import *

class Spec:
    """
    The spec is an adapter between a GConfValue and a Python value,
    simplifying the conversion and the integrity.
    
    You should use L{Spec.STRING}, L{Spec.FLOAT}, L{Spec.INT} and L{Spec.BOOL}
    instead.
    """
    def __init__(self, name, gconf_type, py_type, default):
        self.gconf_type = gconf_type
        self.py_type = py_type
        self.default = default
        self.name = name

Spec.STRING = Spec("string", gconf.VALUE_STRING, str, '')
Spec.FLOAT = Spec("float", gconf.VALUE_FLOAT, float, 0.0)
Spec.INT = Spec("int", gconf.VALUE_INT, int, 0)
Spec.BOOL = Spec("bool", gconf.VALUE_BOOL, bool, True)   
    

class GConfValue(object):
    """
    The GConfValue represents the GConf key's data. You define a certain schema
   (or type of data) and GConfValue keeps track of its integrity. It adds the
    possibility to define a default value to be used when the key is inexistent
    or contains an invalid data type. You can also define callbacks that notify
    you when the key is altered.
    
    Taken from U{GAW Introduction <http://s1x.homelinux.net/documents/gaw_intro>}::

        import gwp, gconf, gtk
        gconf.client_get_default().add_dir("/apps/gwp", gconf.CLIENT_PRELOAD_NONE)

        key_str = gwp.GConfValue(
          key = "/apps/gwp/key_str",
          data_spec = gwp.Spec.STRING
        )

        def on_changed(*args):
          global key_str
          print key_str.key, "=", key_str.data
          gtk.main_quit()
          
        tmp.set_callback(on_changed)
        tmp.data = "Hello world"

        gtk.main()
    """
    
    _notify_id = None
    
    def __init__(self, key, data_spec, client = None, **kwargs):
        if not client:
            client = gconf.client_get_default()

        self.client = client
    
        self.private = "private:" in key
        
        self.key = key.replace("private:", "")
        
        self.data_spec = data_spec
        
        if "default" in kwargs:
            self.default = kwargs["default"]

    ############
    # data_spec
    def get_data_spec(self):
        return self._data_spec

    def set_data_spec(self, data_spec):
        self._data_spec = data_spec
        self._setter = getattr(self.client, "set_" + data_spec.name)
        self._getter = getattr(self.client, "get_" + self.data_spec.name)
    
    data_spec = property(get_data_spec, set_data_spec)
    
    #######
    # data
    def get_data(self):

        if self.private:
            try:
                return gnomekeyring.find_items_sync(
                  gnomekeyring.ITEM_GENERIC_SECRET, {"id": self.key})[0].secret
            except gnomekeyring.NoMatchError: pass
        
        try:
            val = self._getter(self.key)
        except gobject.GError:
            return self.default
            
        if val is None:
            return self.default
        return val
    
    def set_data(self, value):

        if self.private:
            try:
                token = gnomekeyring.item_create_sync(
                  gnomekeyring.get_default_keyring_sync(),
                  gnomekeyring.ITEM_GENERIC_SECRET, "Gwibber preference %s" % self.key,
                  {"id": self.key}, value, True)
                self._setter(self.key, ":KEYRING:%s" % token)
            except gnomekeyring.NoMatchError:
                pass

        assert isinstance(value, self.data_spec.py_type)
        val = self.get_data()
        if val != value:
            self._setter(self.key, value)
    
    data = property(get_data, set_data)
    

    ##########
    # default
    def get_default(self):
        return getattr(self, "_default", self.data_spec.default)

    def set_default(self, default):
        self._default = default

    default = property(get_default, set_default)
    
    ###############
    # is writable
    def get_is_writable(self):
        return self.client.key_is_writable(self.key)
    
    is_writable = property(get_is_writable)
    
    ################
    # Other methods
    def set_callback(self, on_changed):
    
        assert on_changed is None or callable(on_changed)
        
        if self._notify_id is not None:
            self.client_notify_remove(self._notify_id)
            self._notify_id = None
            self._on_changed_cb = None
        
        if on_changed is not None:
            self._on_changed_cb = on_changed
            self._notify_id = self.client.notify_add(
                self.key,
                self._on_changed
            )
                                                                                                                                                
    def _on_changed(self, *args):
        self._on_changed_cb(self)
    
    def __del__(self):
        self.set_callback(None)
    
    def reset_default(self):
        """
        Resets the default value to the one present in the Spec
        """
        if hasattr(self, "_default"):
            del self._default




class RadioButtonPersistencyLink:
    """
    A radio_group is a dictionary that associates a gconf boolean key
    with a radio button::
    
        data = RadioButtonPersistency(
            {
                'cheese': cheese_btn,
                'ham': ham_btn,
                'fish': fish_btn
            },
        )
        data.selected_by_default = 'ham'
    
        selected_value = data.data
        data.data = 'fish'
    """
    
    selected_by_default = None
    
    def __init__(self, widgets, key, client = None):
        self.widgets = widgets
        self.keys = {}
        self.gconf_value = GConfValue(key, Spec.STRING, client)
        self.gconf_value.set_callback(self._on_gconf_changed)
        
        notify_widget = False
        for key, widget in widgets.iteritems():
            if not notify_widget:
                widget.connect("toggled", self._on_widget_changed)
                notify_widget = True
            widget.connect("destroy", self._on_destroy)

            self.keys[widget] = key
            
        self.sync_widget()
        
    def _on_destroy(self, widget):
        key = self.keys[widget]
        del self.widgets[key]
        # Set the widget to none so that the key still exists
        self.keys[widget] = None
        
    def _get_active(self):
        for radio in self.keys:
            if radio is not None and radio.get_active():
                return radio
        return None
    
    def _on_widget_changed(self, radio_button):
        # Update gconf entries
        self.sync_gconf()
        
    def _on_gconf_changed(self, data):
        
        data_spec = self.gconf_value.data_spec

        for widget in self.keys:
            widget.set_sensitive(self.gconf_value.is_writable)
        
        self.sync_widget()
        self.sync_gconf()
            
    def sync_widget(self):
        key = self.gconf_value.data
        
        if key in self.widgets:
            # value is in radio group
            self.widgets[key].set_active(True)
        
        else:
            # When there is a default value, set it
            if self.selected_by_default is not None:
                self.data = self.selected_by_default
            
            # Otherwise deselect all entries
            active = self._get_active()
            if active is not None:
                # Unset the active radio button
                active.set_active(False)
        self.sync_gconf()
    
    def sync_gconf(self):
        active = self._get_active()
        if active is not None:
            self.gconf_value.data = self.keys[active]
        else:
            self.gconf_value.reset_default()
        
    def set_data(self, value):
        self.sync_gconf()
        self.gconf_value = value
        
    def get_data(self):
        self.sync_gconf()
        return self.gconf_value.data
    
    data = property(get_data, set_data)

    def cmp_func(cls, obj):
        try:
            obj_iter = iter(obj)
        except TypeError:
            return False
        
        for item in obj_iter:
            if not isinstance(item, gtk.RadioButton):
                return False
        
        return True
    
    cmp_func = classmethod(cmp_func)


create_persistency_link = PersistencyLinkFactory()

def _persistency_link_file_chooser(button, key, use_directory=False, use_uri=True, *args, **kwargs):
    """
    
    Associates a L{gwp.PersistencyLink} to a gtk.FileChooserButton. This is an utility function
    that wrapps around L{gwp.PersistencyLink}.

    @param button: the file chooser button
    @param key: the gconf key
    @param use_directory: boolean variable setting if it's we're using files or directories.
    @param use_uri: boolean variable setting if we're using URI's or normal filenames.
    @param default: the default value that L{gwp.GConfValue} falls back to.
    @param client: The GConfClient
    @type button: U{gtk.FileChooserButton <http://pygtk.org/pygtk2reference/class-gtkfilechooserbutton.html>}
    
    @rtype: L{gwp.PersistencyLink}
    """
    if not use_directory and not use_uri:
        getter = button.get_filename
        setter = button.set_filename
    elif not use_directory and use_uri:
        getter = button.get_uri
        setter = button.set_uri
    elif use_directory and not use_uri:
        getter = button.get_current_folder
        setter = button.set_current_folder
    elif use_directory and use_uri:
        getter = button.get_current_folder_uri
        setter = button.set_current_folder_uri
    
    return PersistencyLink(button, getter, setter, "selection-changed", GConfValue(key, Spec.STRING, default=default, client=client, *args, **kwargs), is_lazy=True)

create_persistency_link.append_handler(gtk.FileChooserButton, _persistency_link_file_chooser)

def _persistency_link_entry(entry, key, data_spec = Spec.STRING, *args, **kwargs):
    """
    Associates to a U{gtk.Entry <http://pygtk.org/pygtk2reference/class-gtkentry.html>}

    @rtype: L{gwp.PersistencyLink}
    """
    return PersistencyLink(entry, entry.get_text, entry.set_text, "changed", GConfValue(key, data_spec, *args, **kwargs))

create_persistency_link.append_handler(gtk.Entry, _persistency_link_entry)

def _persistency_link_spin_button(spinbutton, key, use_int = True, *args, **kwargs):
    """
    Associates to a U{gtk.SpinButton <http://pygtk.org/pygtk2reference/class-gtkspinbutton.html>}

    @param use_int: when set to False it uses floats instead.
    @rtype: L{gwp.PersistencyLink}
    """
    
    if use_int:
        return PersistencyLink(spinbutton, spinbutton.get_value_as_int, spinbutton.set_value, "value-changed", GConfValue(key, Spec.INT, *args, **kwargs))
    else:
        return PersistencyLink(spinbutton, spinbutton.get_value, spinbutton.set_value, "value-changed", GConfValue(key, Spec.FLOAT, *args, **kwargs))

create_persistency_link.append_handler(gtk.SpinButton, _persistency_link_spin_button)

def _persistency_link_toggle_button(toggle, key, *args, **kwargs):
    """
    This is to be used with a U{gtk.ToggleButton <http://pygtk.org/pygtk2reference/class-gtktogglebutton.html>}

    @rtype: L{gwp.PersistencyLink}
    """
    return PersistencyLink(toggle, toggle.get_active, toggle.set_active, "toggled", GConfValue(key, Spec.BOOL, *args, **kwargs))

create_persistency_link.append_handler(gtk.ToggleButton, _persistency_link_toggle_button)
create_persistency_link.append_handler(gtk.CheckMenuItem, _persistency_link_toggle_button)

#create_persistency_link.append_handler_full(RadioButtonPersistencyLink.cmp_func, RadioButtonPersistencyLink)

def _persistency_link_color_button(button, key, default="black", *args, **kwargs):
  return PersistencyLink(button, lambda: button.get_color().to_string(), lambda x: button.set_color(gtk.gdk.color_parse(x)), "color-set", GConfValue(key, Spec.STRING, default=default, *args, **kwargs))

create_persistency_link.append_handler(gtk.ColorButton, _persistency_link_color_button)

def _persistency_link_range(range, key, *args, **kwargs):
  return PersistencyLink(range, lambda: int(range.get_value()), range.set_value, "value-changed", GConfValue(key, Spec.INT, *args, **kwargs))

create_persistency_link.append_handler(gtk.HScale, _persistency_link_range)

def _persistency_link_combobox(combo, key, data_spec = Spec.STRING, *args, **kwargs):
  return PersistencyLink(combo, combo.get_active_text, lambda val: combo.set_active_iter([x.iter for x in combo.get_model() if x[0].strip() == val][0]), "changed", GConfValue(key, data_spec, *args, **kwargs))

create_persistency_link.append_handler(gtk.ComboBox, _persistency_link_combobox) 

def _persistency_link_combobox_entry(entry, key, data_spec = Spec.STRING, *args, **kwargs):
  """
  Associates to a U{gtk.ComboBoxEntry <http://pygtk.org/pygtk2reference/class-gtkcomboboxentry.html>}

  @rtype: L{gwp.PersistencyLink}
  """
  return PersistencyLink(entry, entry.child.get_text, entry.child.set_text, "changed", GConfValue(key, data_spec, *args, **kwargs))

create_persistency_link.append_handler(gtk.ComboBoxEntry, _persistency_link_combobox_entry) 
