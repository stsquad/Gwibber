# Copyright (C) 2004 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# Authors: Tiago Cogumbreiro <cogumbreiro@users.sf.net>
"""
GConf Widget Persistency is a module for maintaining persistency between your
existing widgets and the GConf keys. Not only it forces the schema you've
defined for the key but also preserves the widget state, for example making it
insensitive when the GConf key is insensitive.

It also implements a representation of a gconf key (GConfValue) that handles
the repetitive hassles of a maintaining its integrity. 
"""
import gconf, gobject

class Spec (object):
    def __init__ (self, name, gconf_type, py_type, default):
        self.__gconf_type = gconf_type
        self.__py_type = py_type
        self.__default = default
        self.__name = name
    
    gconf_type = property (lambda self: self.__gconf_type)
    py_type = property (lambda self: self.__py_type)
    default = property (lambda self: self.__default)
    name = property (lambda self: self.__name)

Spec.STRING = Spec ("string", gconf.VALUE_STRING, str, '')
Spec.FLOAT = Spec ("float", gconf.VALUE_FLOAT, float, 0.0)
Spec.INT = Spec ("int", gconf.VALUE_INT, int, 0)
Spec.BOOL = Spec ("bool", gconf.VALUE_BOOL, bool, True)


def data_file_chooser (button, key, use_directory = False, use_uri = True, default = None, client = None):
    """
    Returns a gaw.Data.
    
    use_directory - boolean variable setting if it's we're using files or directories.
    use_uri - boolean variable setting if we're using URI's or normal filenames.
    
    Associates a gaw.Data to a gtk.FileChooserButton. 
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
        
    return Data (button, getter, setter, "selection-changed", GConfValue (key, Spec.STRING, default = default, client = client))

def data_entry (entry, key, data_spec = Spec.STRING, default = None, client = None):
    return Data (entry, entry.get_text, entry.set_text, "changed", GConfValue (key, data_spec, default, client))

def data_combo (combo, key, data_spec = Spec.INT, default = None, client = None):
  return Data (combo, lambda: combo.get_active() + 1, lambda i: combo.set_active(i-1), "changed", GConfValue (key, Spec.INT, default, client))

def data_spin_button (spinbutton, key, use_int = True, default = None, client = None):
    if use_int:
        return Data (spinbutton, spinbutton.get_value_as_int, spinbutton.set_value, "value-changed", GConfValue (key, Spec.INT, default, client))
    else:
        return Data (spinbutton, spinbutton.get_value, spinbutton.set_value, "value-changed", GConfValue (key, Spec.FLOAT, default, client))

def data_toggle_button (toggle, key, default = None, client = None):
    return Data (toggle, toggle.get_active, toggle.set_active, "toggled", GConfValue (key, Spec.BOOL, default, client))

class GConfValue (object):
    """
    The GConfValue represents the GConf key's data. You define a certain schema
    (or type of data) and GConfValue keeps track of its integrity. It adds the
    possibility to define a default value to be used when the key is inexistent
    or contains an invalid data type. You can also define callbacks that notify
    you when the key is altered.
    
    Taken from http://s1x.homelinux.net/documents/gaw_intro :
        import gaw, gconf, gtk
        gconf.client_get_default ().add_dir ("/apps/gaw", gconf.CLIENT_PRELOAD_NONE)

        key_str = gaw.GConfValue (
          key = "/apps/gaw/key_str",
          data_spec = gaw.Spec.STRING
        )

        def on_changed (*args):
          global key_str
          print key_str.key, "=", key_str.data
          gtk.main_quit ()
          
        tmp.set_callback (on_changed)
        tmp.data = "Hello world"

        gtk.main ()
    """
    def __init__ (self, key, data_spec, default = None, client = None):
        if not client:
            client = gconf.client_get_default ()

        self.client = client
    
        self.key = key
        
        self.data_spec = data_spec
        
        # init the source id
        self.__notify_id = None
        
        if default is not None:
            self.default = default

    
    # Returns the appropriate method which is bound to the GConfClient object
    __setter = property (
        # fget
        lambda self: getattr (
            self.client,
            "set_" + self.data_spec.name
        )
    )
    
    def __get_data (self):
        val = self.client.get (self.key)
        if val is None:
            return self.get_default ()
        
        return getattr (val, "get_" + self.data_spec.name)()
    
    
    # The real getter and setter methods encapsulate the key
    data = property (
        fget = __get_data,#lambda self: self.__getter (self.key),
        fset = lambda self, value: self.__setter (self.key, value)
    )
    
    def set_callback (self, on_changed):
        assert on_changed is None or callable (on_changed)
        
        if self.__notify_id is not None:
            self.client_notify_remove (self.__notify_id)
            self.__notify_id = None
        
        if on_changed is not None:
            self.__notify_id = self.client.notify_add (
                self.key,
                on_changed
            )
    
    def __del__ (self):
        self.set_callback (None)
    
    def reset_default (self):
        self.data = self.data_spec.default

    def get_default (self):
        return getattr (self, "default", self.data_spec.default)

class RadioButtonData:
    """A radio_group is a dictionary that associates a gconf boolean key
    with a radio button.
    data = RadioButtonData (
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
    
    def __init__ (self, widgets, key, client = None):
        self.widgets = widgets
        self.keys = {}
        self.gconf_value = GConfValue (key, Spec.STRING, client)
        self.gconf_value.set_callback (self.__on_gconf_changed)
        
        notify_widget = False
        for key, widget in widgets.iteritems ():
            if not notify_widget:
                widget.connect ("toggled", self.__on_widget_changed)
                notify_widget = True
            widget.connect ("destroy", self.__on_destroy)

            self.keys[widget] = key
            
        self.sync_widget ()
        
    def __on_destroy (self, widget):
        key = self.keys[widget]
        del self.widgets[key]
        # Set the widget to none so that the key still exists
        self.keys[widget] = None
        
    def _get_active (self):
        for radio in self.keys:
            if radio is not None and radio.get_active ():
                return radio
        return None
    
    def __on_widget_changed (self, radio_button):
        # Update gconf entries
        self.sync_gconf ()
        
    def __on_gconf_changed (self, client, conn_id, entry, user_data):
        
        data_spec = self.gconf_value.data_spec

        for widget in self.keys:
            widget.set_sensitive (client.key_is_writable (self.gconf_value.key))
            
        if entry.value is None or entry.value.type != data_spec.gconf_type:
            self.sync_gconf ()

        else:
            self.sync_widget ()
            
    def sync_widget (self):
        key = self.gconf_value.data
        
        if key in self.widgets:
            # value is in radio group
            self.widgets[key].set_active (True)
        
        else:
            # When there is a default value, set it
            if self.selected_by_default is not None:
                self.data = self.selected_by_default
            
            # Otherwise deselect all entries
            active = self._get_active ()
            if active is not None:
                # Unset the active radio button
                active.set_active (False)
        self.sync_gconf ()
    
    def sync_gconf (self):
        active = self._get_active ()
        if active is not None:
            self.gconf_value.data = self.keys[active]
        else:
            self.gconf_value.reset_default ()
        
    def __set_data (self, value):
        self.sync_gconf ()
        self.gconf_value = value
        
    def __get_data (self):
        self.sync_gconf ()
        return self.gconf_value.data
    
    data = property (__get_data, __set_data)
    
class Data (object):
    """
    This utility class acts as a synchronizer between a widget and gconf entry.
    This data is considered to have problematic backends, since widgets can be
    destroyed and gconf can have integrity problems (for example permissions or
    schema change).
    
    To use the gaw.Data object you just need to specify it's associated type
    (the schema) and optionally a default value.
    
    Here's a simple example on how to use it (taken from http://s1x.homelinux.net/documents/gaw_intro): 
    
            
    """
    
    def __init__ (self, widget, widget_getter, widget_setter, changed_signal, gconf_value):
        self.__widget = widget
        self.__widget_setter = widget_setter
        self.__widget_getter = widget_getter
        self.__gconf_value = gconf_value
        
        gconf_value.set_callback (self.__on_gconf_changed)

        widget.connect (changed_signal, self.__on_widget_changed)
        widget.connect ("destroy", self.__on_destroy)

        if self.widget is not None:
            self.sync_widget ()
    
    gconf_value = property (lambda self: self.__gconf_value)
    widget = property (lambda self: self.__widget)
    
    def __get_data (self):
        # policy is widget has the most up to date data, so update gconf key
        
        try:
            # GConf is always our data resource, get data from there
            return self.gconf_value.data
        except gobject.GError:

            if self.widget is not None:
                # we had an error retrieving the error, return widget value
                val = self.__widget_getter ()
            else:
                # no widget return default
                return self.gconf_value.get_default ()
    
    def __set_data (self, data):
        assert isinstance (data, self.gconf_value.data_spec.py_type)
        try:
            self.gconf_value.data = data
        except gobject.GError:
            # when something goes wrong there's nothing we can do about it
            pass

    data = property (__get_data, __set_data, None, "The data contained in this component.")

    def __on_destroy (self, widget):
        self.__widget = None
        
    def __on_widget_changed (self, *args):
        if self.widget is None:
            return
        self.sync_gconf ()
            
    def __on_gconf_changed (self, client, conn_id, entry, user_data = None):

        if self.widget is None:
            return
        
        data_spec = self.gconf_value.data_spec
        
        self.widget.set_sensitive (client.key_is_writable (self.gconf_value.key))
        if entry.value and entry.value.type == data_spec.gconf_type:
            converter = getattr (entry.value, 'get_' + data_spec.name)
            self.__widget_setter (converter ())
            
        else:
            self.__widget_setter (self.gconf_value.get_default())
            
        # Because widgets can validate data, sync the gconf entry again
        self.sync_gconf()
    
    def sync_widget (self):
        """
        Synchronizes the widget in favour of the gconf key. You must check if
        there is a valid widget before calling this method.
        """
        assert self.widget, "Checking if there's a valid widget is a prerequisite."
        try:
            val = self.gconf_value.data

            if val:
                self.__widget_setter (val)

        except gobject.GError:

            self.__widget_setter (self.gconf_value.get_default ())
        # Because some widgets change the value, update it to gconf again
        self.sync_gconf ()
    
    def sync_gconf (self):
        """
        Synchronizes the gconf key in favour of the widget. You must check if
        there is a valid widget before calling this method.
        """
        assert self.widget, "Checking if there's a valid widget is a prerequisite."
        val = self.__widget_getter ()
        try:
            self.gconf_value.data = val
            self.__widget_setter (self.gconf_value.data)
            
        except gobject.GError:
            pass
