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
        self.midiName = None
        self.fromDevice = False
        self.midiIn = rtmidi.MidiIn()
        self.midiIn.ignore_types( sysex=False )
        self.midiOut = rtmidi.MidiOut()

        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )

        self.initErrorWindow()
        self.initMainWindow()

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
            self.setStatusBar( self.midiName )
            self.midiIn.set_callback( self.midiCallback )
            self.sendSysEx( [ 0x75 ] )
            self.mainWindow.show_all()
        else:
            self.errorWindow.show_all()
        Gtk.main()

    def onWindowDestroy( self, *args ):
        self.midiIn.close_port()
        self.midiOut.close_port()
        Gtk.main_quit()

    def onExitClicked( self, button, win ):
        win.destroy()

    def sendSysEx( self, sysex ):
        msg = [ 0xF0 ] + self.MANU_ID + self.DEVICE_ID + sysex + [ 0xF7 ]
        print( "SendSysEx:", bytes(msg).hex().upper() )
        self.midiOut.send_message( msg )

    def midiCallback( self, msg, data=None ):
        data = bytes( msg[0] )
        print( "MidiCallBack:", data.hex().upper() )

        start = data[:7]
        resp  = data[7:-1]
        end   = data[-1]

        if( start.hex().upper() != bytes( [ 0xF0 ] + self.MANU_ID + self.DEVICE_ID ).hex().upper() ): return
        if( len( resp ) == 0 ): return
        if( end != 0xF7 ): return

        # get config answer
        if( resp[0] == 0x76 ):
            GLib.idle_add( self.showParameters, resp[1:] )
        # recall pattern answer
        elif( resp[0] == 0x78 ):
            GLib.idle_add( self.showSequencer, resp[1:] )

    # Error Window
    def initErrorWindow( self ):
        self.errorWindow = self.builder.get_object( "Error Mindow" )

        self.errorWindow.connect( "destroy", self.onWindowDestroy )
        self.builder.get_object( "ErrWin/Exit" ).connect( "clicked", self.onExitClicked, self.errorWindow )

    # Main Window
    def initMainWindow( self ):
        self.mainWindow = self.builder.get_object( "Main Window" )
        self.statusBar = self.builder.get_object( "MainWin/Status Bar" )

        self.mainWindow.connect( "destroy", self.onWindowDestroy )
        self.builder.get_object( "MainWin/Exit" ).connect( "clicked", self.onExitClicked, self.mainWindow )

        self.initTabGeneral()
        self.initTabSequencer()

    def setStatusBar( self, msg ):
        self.statusBar.set_text( msg )

    # Tab general
    def initTabGeneral( self ):
        self.pitchBend = self.builder.get_object( "MainWin/General/Pitch Bend" )
        self.clockSource = self.builder.get_object( "MainWin/General/Clock Source")
        self.clockType = self.builder.get_object( "MainWin/General/Clock Type" )
        self.clockEdge = self.builder.get_object( "MainWin/General/Clock Edge" )
        self.midiClockOut = self.builder.get_object( "MainWin/General/Midi Clock Out" )
        self.assignMode = self.builder.get_object( "MainWin/General/Assign Mode" )
        self.sequencerAutoPlay = self.builder.get_object( "MainWin/General/Sequencer Auto Play" )
        self.accentVelocityTreshold = self.builder.get_object( "MainWin/General/Accent Velocity Threshold" )
        self.factorySettings = self.builder.get_object( "MainWin/General/Factory Settings" )

        self.pitchBend.connect( "value-changed", self.setSpinButton, [ 0x11, 0x00, 0x00 ]  )
        self.clockSource.connect( "changed", self.setComboBox, [ 0x1B, 0x00 ]  )
        self.clockType.connect( "changed", self.setComboBox, [ 0x1A, 0x00 ] )
        self.clockEdge.connect( "changed", self.setComboBox, [ 0x19, 0x00 ] )
        self.midiClockOut.connect( "changed", self.setComboBox, [ 0x17, 0x00 ] )
        self.assignMode.connect( "changed", self.setComboBox, [ 0x1F, 0x00 ] )
        self.sequencerAutoPlay.connect( "changed", self.setComboBox, [ 0x1D, 0x00 ] )
        self.accentVelocityTreshold.connect( "value-changed", self.setSpinButton, [ 0x1C, 0x00 ] )
        self.factorySettings.connect( "clicked", self.onFactorySettingClicked )

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

    # Tab Sequencer
    def initTabSequencer( self ):
        self.notes = self.builder.get_object( "ListStore MainWin/Sequencer/Notes" )

        self.builder.get_object( "MainWin/Sequencer/Recall" ).connect( "clicked", self.onSeqRecallClicked )
        self.builder.get_object( "MainWin/Sequencer/Rest" ).connect( "toggled", self.onNoteToggle, 1 )
        self.builder.get_object( "MainWin/Sequencer/Glide" ).connect( "toggled", self.onNoteToggle, 6 )
        self.builder.get_object( "MainWin/Sequencer/Accent" ).connect( "toggled", self.onNoteToggle, 7 )

        #self.seqListaNotas.append( [ 1, False, "C#-1", "75.5%", 4, 120, False, False ] )
        #for i in range( 1, 32 ):
        #    self.seqListaNotas.append( [ i + 1, True, "C#-1", "75.5%", 4, 120, False, False ] )

    def onSeqRecallClicked( self, widget, data=None ):
        bank = int( self.builder.get_object( "MainWin/Sequencer/Bank" ).get_active() )
        patt = int( self.builder.get_object( "MainWin/Sequencer/Pattern" ).get_active() )
        self.sendSysEx( [ 0x77, bank, patt ] )

    def onNoteToggle( self, cell, path, col ):
        self.notes[path][col]= not self.notes[path][col]

    GATES = [ "12,5%", "25.0%", "37.5%", "50.0%", "62.5%", "75.0%", "87.5%", "100%" ]
    NOTES = [ "C","C#","D","D#","E","F","F#","G","G#","A","A#","B" ]

    def showSequencer( self, data ):
        self.fromDevice = True
        bank   = int( data[0] ) + 1
        patt   = int( data[1] ) + 1

        swing  = data[2:4]
        if( swing[0] == 0 ): swing = 50 + int( swing[1] )
        else: swing = 66 + int( swing[1] )
        nsteps = int( data[5] )*8 + int( data[7] ) + 1

        self.builder.get_object( "MainWin/Sequencer/Swing" ).set_value( swing )
        self.builder.get_object( "MainWin/Sequencer/Length" ).set_value( nsteps )

        #print( "Bank: %d, Pattern: %d, Swing: %d%%" % ( bank, patt, swing ) )

        steps  = data[8:]
        self.notes.clear()
        for i in range(nsteps):
            step = steps[0:8]
            #print( step.hex().upper() )

            n = step[0:2]
            n = int( n[1] ) + int( n[0] )*16 + 1
            octave = int( n/12 ) - 1
            note = self.NOTES[ n%12 - 1]
            gate = self.GATES[ int(step[2]) ]
            ratchet = int( step[3] ) + 1
            n = step[4:6]
            velocity = int( n[1] ) + int( n[0] )*16
            glide  = 1 if( step[6] & 0x01 != 0 ) else 0
            accent = 1 if( step[6] & 0x04 != 0 ) else 0
            rest   = 1 if( step[6] & 0x08 != 0 ) else 0
            unk      = step[7]
            #print( "Step %02d: Note: %-2s%2d, Gate Length: %5s, Ratchet: %d, Velocity: %3d, Glide: %d, Accent: %d, Rest: %d" % ( i, note, octave, gate, ratchet, velocity, glide, accent, rest ) )
            self.notes.append( [ i + 1, rest, "%s%d" % (note, octave), gate, ratchet, velocity, glide, accent ] )
            steps = steps[8:]
        self.fromDevice = False


# Show Time
if( __name__ == "__main__" ):
    synth = SynthCrave( "resources/SynthCrave.glade" )
    synth.run()
