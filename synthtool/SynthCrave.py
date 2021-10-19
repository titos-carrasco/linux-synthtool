import time
import rtmidi
import queue

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib


class SynthCrave():
    MANU_ID         = [ 0x00, 0x20, 0x32 ]  # Behringer GmbH
    DEVICE_ID       = [ 0x00, 0x01, 0x05 ]  # CRAVE
    DEVICE_NAME     = "CRAVE MIDI"

    def __init__( self, filedef ):
        self.theWindow = None
        self.midiName = None
        self.fromDevice = False
        self.midiIn = rtmidi.MidiIn()
        self.midiIn.ignore_types(sysex=False)
        self.midiOut = rtmidi.MidiOut()

        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )

        self.mainWindow = self.builder.get_object( "Main Window" )
        self.mainWindow.connect( "destroy", self.onWindowDestroy )
        self.builder.get_object( "Main Exit" ).connect( "clicked", self.onExitClicked )

        self.pitchBend = self.builder.get_object( "Pitch Bend" )
        self.clockSource = self.builder.get_object( "Clock Source")
        self.clockType = self.builder.get_object( "Clock Type" )
        self.clockEdge = self.builder.get_object( "Clock Edge" )
        self.midiClockOut = self.builder.get_object( "Midi Clock Out" )
        self.assignMode = self.builder.get_object( "Assign Mode" )
        self.sequencerAutoPlay = self.builder.get_object( "Sequencer Auto Play" )
        self.accentVelocityTreshold = self.builder.get_object( "Accent Velocity Threshold" )
        self.factorySettings = self.builder.get_object( "Factory Settings" )

        self.pitchBend.connect( "value-changed", self.setSpinButton, [ 0x11, 0x00, 0x00 ]  )
        self.clockSource.connect( "changed", self.setComboBox, [ 0x1B, 0x00 ]  )
        self.clockType.connect( "changed", self.setComboBox, [ 0x1A, 0x00 ] )
        self.clockEdge.connect( "changed", self.setComboBox, [ 0x19, 0x00 ] )
        self.midiClockOut.connect( "changed", self.setComboBox, [ 0x17, 0x00 ] )
        self.assignMode.connect( "changed", self.setComboBox, [ 0x1F, 0x00 ] )
        self.sequencerAutoPlay.connect( "changed", self.setComboBox, [ 0x1D, 0x00 ] )
        self.accentVelocityTreshold.connect( "value-changed", self.setSpinButton, [ 0x1C, 0x00 ] )
        self.factorySettings.connect( "clicked", self.onFactorySettingClicked )

        self.errorWindow = self.builder.get_object( "Error Mindow" )
        self.errorWindow.connect( "destroy", self.onWindowDestroy )
        self.builder.get_object( "Error Exit" ).connect( "clicked", self.onExitClicked )

        self.statusBar = self.builder.get_object( "Status Bar" )

    def onWindowDestroy( self, *args ):
        self.midiIn.close_port()
        self.midiOut.close_port()
        Gtk.main_quit()

    def onExitClicked( self, button ):
        self.theWindow.destroy()

    def sendSysEx( self, sysex ):
        msg = [ 0xF0 ] + self.MANU_ID + self.DEVICE_ID + sysex + [ 0xF7 ]
        print( "SendSysEx:", bytes(msg).hex().upper() )
        self.midiOut.send_message( msg )

    def midiCallback( self, msg, data=None ):
        data = bytes( msg[0] )
        print( "MidiCallBack RC:", data.hex().upper() )

        start = data[:7]
        resp  = data[7:-1]
        end   = data[-1]

        if( start.hex().upper() != bytes( [ 0xF0 ] + self.MANU_ID + self.DEVICE_ID ).hex().upper() ): return
        if( len( resp ) == 0 ): return
        if( end != 0xF7 ): return
        print( "MidiCallBack OK:", resp.hex().upper() )

        if( resp[0] == 0x76 ):
            GLib.idle_add( self.showParameters, resp[1:] )

    def showParameters( self, data ):
        self.fromDevice = True
        self.pitchBend.set_value( data[0] )
        self.midiClockOut.set_active( data[2] )
        self.sequencerAutoPlay.set_active( data[3] )
        self.clockSource.set_active( data[4] )
        self.clockType.set_active( data[5] )
        self.clockEdge.set_active( data[6] )
        self.assignMode.set_active( data[7] )
        self.accentVelocityTreshold.set_value( data[8] )
        self.fromDevice = False

    def run( self ):
        ports = self.midiIn.get_ports()
        for i in range( len(ports) ):
            if( self.DEVICE_NAME in ports[i] ):
                self.midiIn.open_port( i )
                self.midiName = ports[i]
                break

        ports = self.midiOut.get_ports()
        for i in range( len(ports) ):
            if( self.DEVICE_NAME in ports[i] ):
                self.midiOut.open_port( i )
                break

        if( self.midiIn.is_port_open() and self.midiOut.is_port_open() ):
            self.midiIn.set_callback( self.midiCallback )
            self.sendSysEx( [ 0x75 ] )
            self.setStatusBar( self.midiName )
            self.theWindow = self.mainWindow
        else:
            self.theWindow = self.errorWindow
        self.theWindow.show_all()
        Gtk.main()

    #--
    def setStatusBar( self, msg ):
        self.statusBar.set_text( msg )

    def setSpinButton( self, widget, data=None ):
        if( not self.fromDevice ):
            data[1] = int( widget.get_value() )
            self.sendSysEx( data )

    def setComboBox( self, widget, data=None ):
        if( not self.fromDevice ):
            data[1] = int( widget.get_active() )
            self.sendSysEx( data )

    def onFactorySettingClicked( self, widget, data=None ):
        self.sendSysEx( [ 0x7D ] )
        self.sendSysEx( [ 0x75 ] )

# Show Time
if( __name__ == "__main__" ):
    synth = SynthCrave( "resources/SynthCrave.glade" )
    synth.run()
