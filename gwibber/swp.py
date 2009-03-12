__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__author__ = "Tiago Cogumbreiro <cogumbreiro@users.sf.net>"
__copyright__ = "Copyright 2005, Tiago Cogumbreiro"
__doc__ = """
Storage-Widget Persistency defines a set of objects to implement a persistency link
between a widget and a certain data store. The data store must implement the
interface IValueHolder.
"""

import gobject

class OutOfSyncError(Exception):
    """
    This error is thrown when there's a synchronization problem
    between the L{GConfValue} and the widget.
    """

class IStorage:
    """The 'PersistencyLink' object expects an IValueHolder class"""
    def get_data():
        pass
    
    def set_data(value):
        pass
        
    data = property(get_data, set_data)
    
    def get_is_writable():
        """Returns whether or not the value can be set"""
        
    is_writable = property(get_is_writable)
    
    def set_callback(callback):
        """
        Defines a callback for when the value has changed
        The callback has the following signature:
        def callback(val)
        
        'val' is self.
        """



class PersistencyLink(object):
    """
    This utility class acts as a synchronizer between a widget and storage value.
    This data is considered to have problematic backends, since widgets can be
    destroyed and storage can have integrity problems (for example permissions
    or schema change).
    
    """
    
    def __init__(self, widget, widget_getter, widget_setter, changed_signal, storage, is_lazy=False):
        """
        @param widget: This is the widget this is observing.
        @type widget: gtk.Widget
        
        @param widget_getter: The function that gets the widget's data
        
        @param widget_setter: The function that sets the widget's data
        
        @param changed_signal: The name of the signal this observer should be
        connecting too.
        
        @param storage: The value contained in the data storage
        
        @type storage: IStorage
        """
        self._widget = widget
        self._widget_setter = widget_setter
        self._widget_getter = widget_getter
        self.storage = storage
        self.is_lazy = is_lazy
        
        storage.set_callback(self._on_storage_changed)

        widget.connect(changed_signal, self._on_widget_changed)
        widget.connect("destroy", self._on_destroy)

        if self.widget is not None:
            self.sync_widget()
    
    #######
    # data
    def get_data(self, sync_storage=True):
        if sync_storage:
            self.sync_storage()
            
        return self.storage.data
    
    def set_data(self, data):
        self.storage.data = data
        self._widget_setter(data)

    data = property(get_data, set_data, doc="The data contained in this component.")
    
    ########
    # widget
    def get_widget(self):
        return self._widget

    widget = property(get_widget)
    
    ##########
    # Methods
    
    def _on_destroy(self, widget):
        self._widget = None
        
    def _on_widget_changed(self, *args):
        if self.widget is None:
            return
            
        # Widget has changed its value, we need to update the GConfValue
        self.sync_storage()
            
    def _on_storage_changed(self, storage):
        # Something was updated on gconf
        if self.widget is None:
            return
        
        self.widget.set_sensitive(storage.is_writable)
            
        # Because widgets can validate data, sync the gconf entry again
        self.sync_widget()
        self.sync_storage()
    
    def sync_widget(self):
        """
        Synchronizes the widget in favour of the gconf key. You must check if
        there is a valid widget before calling this method.
        """
        assert self.widget, "Checking if there's a valid widget is a prerequisite."

        # Set the data from the storage
        val = self.storage.data

        if val is not None:
            self._widget_setter(val)
        
        if self.is_lazy:
            gobject.idle_add(self._check_sync, val)
        else:
            self._check_sync(val)
    
    def _check_sync(self, value):
        # Because some widgets change the value, update it to gconf again
        new_val = self._widget_getter()
        if new_val is None:
            raise OutOfSyncError("Widget getter returned 'None' after a value was set.")
        
        # The value was changed by the widget, we updated it back to GConfValue
        if value != new_val:
            self.sync_storage()
    
    def sync_storage(self):
        """
        Synchronizes the gconf key in favour of the widget. You must check if
        there is a valid widget before calling this method.
        """
        assert self.widget, "Checking if there's a valid widget is a prerequisite."
        # First we 
        val = self._widget_getter()
        if val is None:
            return

        self.storage.data = val



class PersistencyLinkFactory:
    # This class implements a _very_ basic dispatch.on matching the first argument
    def __init__(self):
        self._classes = []
    
    def _generate_cmp_func(self, widget_class):
        return lambda obj: isinstance(obj, widget_class)
    
    def append_handler_full(self, cmp_func, handler):
        self._classes.append((cmp_func, handler))
    
    def insert_handler(self, index, cmp_func, handler):
        self._classes.insert(index, (cmp_func, handler))

    def append_handler(self, widget_class, handler):
        self.append_handler_full(self._generate_cmp_func(widget_class), handler)
    
    def insert_handler(self, index, widget_class, handler):
        self.insert_handler_full(self._generate_cmp_func(widget_class), handler)
    
    def __call__(self, widget, *args, **kwargs):
        for cmp_func, handler in self._classes:
            if cmp_func(widget):
                return handler(widget, *args, **kwargs)
