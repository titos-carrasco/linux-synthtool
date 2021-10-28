from SynthCrave import SynthCrave
from SynthWasp import SynthWasp
from SynthTD3 import SynthTD3

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib

MAIN_WIN_UI = "resources/SynthTool.glade"
CRAVE_UI    = "resources/SynthCrave.glade"
WASP_UI     = "resources/SynthWasp.glade"
TD3_UI     = "resources/SynthTD3.glade"

MAIN_WIN = "Main Window"
CRAVE    = "Crave"
WASP     = "Wasp"
TD3      = "TD-3"
PRO1     = "PRO-1"

class SynthTool():

    def __init__( self, filedef ):
        self.synth = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )
        self.builder.connect_signals( self )
        self.builder.get_object( MAIN_WIN ).show()

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
    if( name == CRAVE ):
        SynthCrave( CRAVE_UI ).run()
    elif( name == WASP ):
        SynthWasp( WASP_UI ).run()
    elif( name == TD3 ):
        SynthTD3( TD3_UI ).run()

# Show Time
main()
