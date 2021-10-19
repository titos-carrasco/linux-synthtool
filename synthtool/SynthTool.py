from SynthCrave import SynthCrave

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib


class SynthTool():
    def __init__( self, filedef ):
        self.synth = None
        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )

        self.mainWindow = self.builder.get_object( "Main Window" )
        self.mainWindow.connect( "destroy", self.onMainWindowDestroy )
        self.builder.get_object( "Main Exit" ).connect( "clicked", self.onExitClicked )
        self.builder.get_object( "Crave" ).connect( "clicked", self.onButtonlicked, "Crave" )
        #self.builder.get_object( "Wasp" ).connect( "clicked", self.onButtonlicked, "Wasp" )
        #self.builder.get_object( "TD-3" ).connect( "clicked", self.onButtonlicked, "TD-3"" )
        #self.builder.get_object( "PRO-1" ).connect( "clicked", self.onButtonlicked, "PRO-1" )

    def onMainWindowDestroy( self, *args ):
        Gtk.main_quit()

    def onExitClicked( self, button ):
        self.mainWindow.destroy()

    def onButtonlicked( self, button, name ):
        self.synth = name
        self.mainWindow.destroy()

    def run( self ):
        self.mainWindow.show_all()
        Gtk.main()
        return self.synth


def main():
    synthTool = SynthTool( "resources/SynthTool.glade" )
    name = synthTool.run()
    if( name is not None ):
        if( name == "Crave" ):
            synth = SynthCrave( "resources/SynthCrave.glade" )
        synth.run()

# Show Time
main()
