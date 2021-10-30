import time
import rtmidi

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib

DEVICE_NAME     = "WASP DELUXE MIDI"
MANUF_ID        = [ 0x00, 0x20, 0x32 ]  # Behringer GmbH
DEVICE_ID       = [ 0x00, 0x01, 0x06 ]  # Wasp

UI_MAIN_WIN              = "MainWin"
UI_ERROR_WIN             = "ErrorWin"
UI_STATUS_BAR            = "MainWin/Status Bar"
UI_MIDI_CHANNEL_SWITCHES = "MainWin/General/Midi Channel Switches"
UI_MIDI_CHANNEL          = "MainWin/General/Midi Channel"
UI_KEY_PRIORITY          = "MainWin/General/Key Priority"
UI_MIDI_IN_TRANSPOSE     = "MainWin/General/MIDI IN Transpose"
UI_MIDI_MULTI_TRIGGER    = "MainWin/General/Multi Trigger"
UI_FIRMWARE_VERSION      = "MainWin/Update/Firmware Version"

class SynthWasp():

    def __init__( self, filedef ):
        self.midiIn = rtmidi.MidiIn()
        self.midiOut = rtmidi.MidiOut()
        self.midiIn.ignore_types( sysex=False )

        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )

        self.ui_error_win             = self.builder.get_object( UI_ERROR_WIN )
        self.ui_main_win              = self.builder.get_object( UI_MAIN_WIN )
        self.ui_status_bar            = self.builder.get_object( UI_STATUS_BAR )
        self.ui_midi_channel_switches = self.builder.get_object( UI_MIDI_CHANNEL_SWITCHES )
        self.ui_midi_channel          = self.builder.get_object( UI_MIDI_CHANNEL )
        self.ui_key_priority          = self.builder.get_object( UI_KEY_PRIORITY )
        self.ui_midi_in_transpose     = self.builder.get_object( UI_MIDI_IN_TRANSPOSE )
        self.ui_midi_multitrigger     = self.builder.get_object( UI_MIDI_MULTI_TRIGGER )
        self.ui_firmware_version      = self.builder.get_object( UI_FIRMWARE_VERSION )

        self.builder.connect_signals( self )

    def run( self ):
        ports = self.midiIn.get_ports()
        for i in range( len(ports) ):
            if( DEVICE_NAME in ports[i] ):
                self.midiIn.open_port( i )
                midiName = ports[i]
                break

        ports = self.midiOut.get_ports()
        for i in range( len(ports) ):
            if( DEVICE_NAME in ports[i] ):
                self.midiOut.open_port( i )
                break

        if( self.midiIn.is_port_open() and self.midiOut.is_port_open() ):
            self.ui_status_bar.set_text( midiName )
            self.midiIn.set_callback( self.midiCallback )

            # get firmware version
            self.sendSysEx( [ 0x08, 0x00 ] )

            # ???
            self.sendSysEx( [ 0x02 ] )

            # get config
            self.sendSysEx( [ 0x75 ] )

            self.ui_main_win.show()
        else:
            self.ui_error_win.show()
        Gtk.main()

    def sendSysEx( self, data ):
        sysex = [ 0xF0 ] + MANUF_ID + DEVICE_ID + data + [ 0xF7 ]
        #print( "SEND:", bytes( sysex ).hex().upper() )

        self.waiting = True
        self.midiOut.send_message( sysex )
        while( self.waiting ): time.sleep( 0.01 )

    def midiCallback( self, msg, data=None ):
        data = bytes( msg[0] )

        start = data[:7]
        resp  = data[7:-1]
        end   = data[-1]

        if( start != bytes( [ 0xF0 ] + MANUF_ID + DEVICE_ID ) ): return
        if( len( resp ) == 0 ): return
        if( end != 0xF7 ): return

        #print( "RECV:", resp.hex().upper() )

        # firmware version
        if( resp[0:2] == bytes( [ 0x09, 0x00 ] ) ):
            fv = "Current Version: v%d.%d.%d" % (resp[2], resp[3], resp[4])
            GLib.idle_add( self.showFirmwareVersion, fv )

        # config values
        elif( resp[0] == 0x76 ):
            GLib.idle_add( self.showParameters, resp[1:] )

        self.waiting = False

    def onWindowDestroy( self, widget ):
        self.midiIn.close_port()
        self.midiOut.close_port()
        Gtk.main_quit()

    def onExitClicked( self, widget ):
        widget.get_toplevel().destroy()

    # Tab general
    def showFirmwareVersion( self, data ):
        self.ui_firmware_version.set_text( data )

    def showParameters( self, data ):
        self.fromApp = True

        self.ui_midi_channel_switches.set_active( data[0] )
        self.ui_midi_channel.set_value( data[1] + 1 )
        self.ui_key_priority.set_active( data[3] )
        self.ui_midi_in_transpose.set_value( data[2]  - 12 )
        self.ui_midi_multitrigger.set_active( data[4] )

        self.ui_midi_channel.set_sensitive( data[0] == 1 )

        if( self.ui_midi_channel_switches.get_active() == 0 ):
            self.ui_midi_channel.set_sensitive( False )
        else:
            self.ui_midi_channel.set_sensitive( True )

        self.fromApp = False

    def onMidiChannelSwitchesChanged( self, widget ):
        if( self.fromApp ): return
        disabled = int( widget.get_active() )
        data = [ 0x0E, disabled, 0x00, 0x00  ]
        self.sendSysEx( data )

        if( disabled ):
            self.ui_midi_channel.set_sensitive( True )
        else:
            self.fromApp = True
            self.ui_midi_channel.set_value( 1 )
            self.fromApp = False
            self.ui_midi_channel.set_sensitive( False )

    def onMidiChannelChanged( self, widget ):
        if( self.fromApp ): return
        channel = int( widget.get_value() - 1 )
        data = [ 0x0E, 0x01, channel, channel ]
        self.sendSysEx( data )

    def onKeypriorityChanged( self, widget ):
        if( self.fromApp ): return
        priority = int( widget.get_active() )
        data = [ 0x12, priority ]
        self.sendSysEx( data )

    def onMidiInTransposeChanged( self, widget ):
        if( self.fromApp ): return
        transpose = int( widget.get_value() ) + 12
        data = [ 0x0F, transpose  ]
        self.sendSysEx( data )

    def onMultiTriggerChanged( self, widget ):
        if( self.fromApp ): return
        multitrigger = int( widget.get_active() )
        data = [ 0x14, multitrigger, 0x00  ]
        self.sendSysEx( data )

    def onFactorySettingClicked( self, widget ):
        # restore factory settings
        self.sendSysEx( [ 0x7D ] )

        # get config
        self.sendSysEx( [ 0x75 ] )


# Show Time
if( __name__ == "__main__" ):
    synth = SynthWasp( "resources/SynthWasp.glade" )
    synth.run()
