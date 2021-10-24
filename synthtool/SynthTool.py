from SynthCrave import SynthCrave

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib

MAIN_WIN_UI = "resources/SynthTool.glade"
CRAVE_UI    = "resources/SynthCrave.glade"

MAIN_WIN_ID = "Main Window"
CRAVE_ID    = "Crave"
WASP_ID     = "Wasp"
TD3_ID      = "TD-3"
PRO1_ID     = "PRO-1"

class SynthTool():

    def __init__( self, filedef ):
        self.synth = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )
        self.builder.connect_signals( self )
        self.builder.get_object( MAIN_WIN_ID ).show()

    def onMainWindowDestroy( self, widget ):
        Gtk.main_quit()

    def onExitClicked( self, widget ):
        widget.get_toplevel().destroy()

    def onButtonlicked( self, widget ):
        self.synth = Gtk.Buildable.get_name( widget )
        widget.get_toplevel().destroy()

    def getSynth( self ):
        return self.synth


def main():
    synthTool = SynthTool( MAIN_WIN_UI )
    Gtk.main()
    name = synthTool.getSynth()
    if( name == CRAVE_ID ):
        SynthCrave( CRAVE_UI ).run()

# Show Time
main()
