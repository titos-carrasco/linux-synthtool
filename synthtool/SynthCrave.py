import time
import rtmidi
import queue

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib

MAIN_WIN_ID     = "Main Window"
ERROR_WIN_ID    = "Error Window"
STATUS_BAR_ID   = "MainWin/Status Bar"

GEN_PITCH_BEND  = "MainWin/General/Pitch Bend"
GEN_CLOCK_SRC   = "MainWin/General/Clock Source"
GEN_CLOCK_TYPE  = "MainWin/General/Clock Type"
GEN_CLOCK_EDGE  = "MainWin/General/Clock Edge"
GEN_MIDI_CLOCK  = "MainWin/General/Midi Clock Out"
GEN_ASSIGN_MODE = "MainWin/General/Assign Mode"
GEN_AUTO_PLAY   = "MainWin/General/Sequencer Auto Play"
GEN_ACC_VEL_THR = "MainWin/General/Accent Velocity Threshold"

SEQ_BANK        = "MainWin/Sequencer/Bank"
SEQ_PATTERN     = "MainWin/Sequencer/Pattern"
SEQ_CLEAR       = "MainWin/Sequencer/Clear"
SEQ_RECALL      = "MainWin/Sequencer/Recall"
SEQ_STORE       = "MainWin/Sequencer/Store"
SEQ_LENGTH      = "MainWin/Sequencer/Length"
SEQ_SWING       = "MainWin/Sequencer/Swing"

SEQ_NOTES_TREE    = "MainWin/Sequencer/Notes"
SEQ_NOTES_STORE   = "ListStore MainWin/Sequencer/Notes"

DEVICE_NAME     = "CRAVE MIDI"
MANUF_ID        = [ 0x00, 0x20, 0x32 ]  # Behringer GmbH
DEVICE_ID       = [ 0x00, 0x01, 0x05 ]  # CRAVE

GATES = [ "12.5%", "25.0%", "37.5%", "50.0%", "62.5%", "75.0%", "87.5%", "100%" ]
NOTES = [ "C","C#","D","D#","E","F","F#","G","G#","A","A#","B" ]


class SynthCrave():

    def __init__( self, filedef ):
        self.fromDevice = False

        self.midiIn = rtmidi.MidiIn()
        self.midiIn.ignore_types( sysex=False )
        self.midiOut = rtmidi.MidiOut()

        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )
        self.builder.connect_signals( self )

        self.notesStore = self.builder.get_object( SEQ_NOTES_STORE )

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
            self.builder.get_object( STATUS_BAR_ID ).set_text( midiName )
            self.midiIn.set_callback( self.midiCallback )
            self.sendSysEx( [ 0x75 ] )
            self.builder.get_object( MAIN_WIN_ID ).show()
        else:
            self.builder.get_object( ERROR_WIN_ID ).show()
        Gtk.main()

    def sendSysEx( self, sysex ):
        msg = [ 0xF0 ] + MANUF_ID + DEVICE_ID + sysex + [ 0xF7 ]
        #print( "SendSysEx:", bytes(msg).hex().upper() )
        self.midiOut.send_message( msg )

    def midiCallback( self, msg, data=None ):
        data = bytes( msg[0] )
        #print( "MidiCallBack:", data.hex().upper() )

        start = data[:7]
        resp  = data[7:-1]
        end   = data[-1]

        if( start.hex().upper() != bytes( [ 0xF0 ] + MANUF_ID + DEVICE_ID ).hex().upper() ): return
        if( len( resp ) == 0 ): return
        if( end != 0xF7 ): return

        # get config answer
        if( resp[0] == 0x76 ):
            GLib.idle_add( self.showParameters, resp[1:] )
        # recall pattern answer
        elif( resp[0] == 0x78 ):
            GLib.idle_add( self.showSequencer, resp[1:] )

    def onWindowDestroy( self, widget ):
        self.midiIn.close_port()
        self.midiOut.close_port()
        Gtk.main_quit()

    def onExitClicked( self, widget ):
        widget.get_toplevel().destroy()

    # Tab general
    def showParameters( self, data ):
        self.fromDevice = True
        self.builder.get_object( GEN_PITCH_BEND ).set_value( data[0] )
        self.builder.get_object( GEN_MIDI_CLOCK ).set_active( data[2] )
        self.builder.get_object( GEN_AUTO_PLAY ).set_active( data[3] )
        self.builder.get_object( GEN_CLOCK_SRC ).set_active( data[4] )
        self.builder.get_object( GEN_CLOCK_TYPE ).set_active( data[5] )
        self.builder.get_object( GEN_CLOCK_EDGE ).set_active( data[6] )
        self.builder.get_object( GEN_ASSIGN_MODE ).set_active( data[7] )
        self.builder.get_object( GEN_ACC_VEL_THR ).set_value( data[8] )
        self.fromDevice = False

    def setSpinButton( self, widget ):
        if( self.fromDevice ): return

        oID = Gtk.Buildable.get_name( widget )
        if( oID == GEN_PITCH_BEND ):
            data = [ 0x11, 0x00, 0x00 ]
        elif( oID == GEN_ACC_VEL_THR ):
            data = [ 0x1C, 0x00 ]
        else:
            return

        data[1] = int( widget.get_value() )
        self.sendSysEx( data )

    def setComboBox( self, widget, data=None ):
        if( self.fromDevice ): return

        oID = Gtk.Buildable.get_name( widget )
        if( oID == GEN_CLOCK_SRC ):
            data = [ 0x1B, 0x00 ]
        elif( oID == GEN_CLOCK_TYPE ):
            data = [ 0x1A, 0x00 ]
        elif( oID == GEN_CLOCK_EDGE ):
            data = [ 0x19, 0x00 ]
        elif( oID == GEN_MIDI_CLOCK ):
            data = [ 0x17, 0x00 ]
        elif( oID == GEN_ASSIGN_MODE ):
            data = [ 0x1F, 0x00 ]
        elif( oID == GEN_AUTO_PLAY ):
            data = [ 0x1D, 0x00 ]
        else:
            return

        data[1] = int( widget.get_active() )
        self.sendSysEx( data )

    def onFactorySettingClicked( self, widget ):
        self.sendSysEx( [ 0x7D ] )
        self.sendSysEx( [ 0x75 ] )

    # Tab Sequencer
    def onClearClicked( self, widget ):
        self.notesStore.clear()
        self.notesStore.append( [ 1, False, "C", 3, "50.0%", 1, 64, False, False ] )

    def onSeqRecallClicked( self, widget ):
        bank = int( self.builder.get_object( SEQ_BANK ).get_active() )
        patt = int( self.builder.get_object( SEQ_PATTERN ).get_active() )
        self.sendSysEx( [ 0x77, bank, patt ] )

    def onStoreClicked( self, widget ):
        bank  = int( self.builder.get_object( SEQ_BANK ).get_active() )
        patt  = int( self.builder.get_object( SEQ_PATTERN ).get_active() )
        steps = int( self.builder.get_object( SEQ_LENGTH ).get_value() ) - 1
        swing = int( self.builder.get_object( SEQ_SWING ).get_value() )

        data = [0]*8
        data[0] = bank
        data[1] = patt
        data[2] = 0 if swing< 66 else 1
        data[3] = swing-50 if swing < 66 else swing - 66
        data[4] = 0
        data[5] = steps >> 3
        data[6] = 0
        data[7] = steps & 0x07

        n = len( self.notesStore )
        for i in range( n ):
            elem     = self.notesStore[i].iter
            rest     = int( self.notesStore[elem][1] )
            note     = NOTES.index( self.notesStore[elem][2] )
            octave   = int( self.notesStore[elem][3] )
            gate     = GATES.index( self.notesStore[elem][4] )
            ratchet  = int( self.notesStore[elem][5] ) - 1
            velocity = int( self.notesStore[elem][6] )
            glide    = int( self.notesStore[elem][7] )
            accent   = int( self.notesStore[elem][8] )

            note = note + (octave+1)*12
            row = [0]*8
            row[0] = note >> 4
            row[1] = note & 0x0F
            row[2] = gate
            row[3] = ratchet
            row[4] = velocity >> 4
            row[5] = velocity & 0x0F
            row[6] = rest*0x08 + accent*0x04 + glide*0x01
            row[7] = 0

            data = data + row

        for i in range( n, 32 ):
            data = data + [ 0x00, 0x04, 0x02, 0x03, 0x00, 0x40, 0x00, 0x00 ]

        self.sendSysEx( [ 0x78 ] + data )

    def onSeqLengthChanged( self, widget ):
        if( self.fromDevice ): return

        l = int( widget.get_value() )
        n = len( self.notesStore )

        if( l > n ):
            l = l - n
            for i in range( l ):
                self.notesStore.append( [ n+i+1, False, "C", 3, "50.0%", 1, 64, False, False ] )
        elif( l < n ):
            elems = []
            for i in range( l, n ):
                elems.append( self.notesStore[i].iter )
            for e in elems:
                self.notesStore.remove( e )

    def onRestToggled( self, cell, path ):
        self.notesStore[path][1]= not self.notesStore[path][1]

    def onNotedEdited( self, cell, path, tree_iter ):
        note = tree_iter
        octave = self.notesStore[path][3]
        if( note != "C" and octave == 9 ):
            note = "C"
        self.notesStore[path][2] = note

    def onOctaveEdited( self, cell, path, tree_iter ):
        octave = int( tree_iter )
        note = self.notesStore[path][2]
        if( note != "C" and octave == 9 ):
            octave = 8
        self.notesStore[path][3] = octave

    def onGateEdited( self, cell, path, tree_iter ):
        self.notesStore[path][4] = tree_iter

    def onRatchetEdited( self, cell, path, tree_iter ):
        self.notesStore[path][5] = int( tree_iter )

    def onVelocityEdited( self, cell, path, tree_iter ):
        try:
            v = int( tree_iter )
        except:
            v = 64
        v = 0 if v < 0 else v
        v= 127 if v > 127 else v
        self.notesStore[path][6] = v

    def onGlideToggled( self, cell, path ):
        self.notesStore[path][7]= not self.notesStore[path][7]

    def onAccentToggled( self, cell, path ):
        self.notesStore[path][8]= not self.notesStore[path][8]

    def showSequencer( self, data ):
        self.fromDevice = True

        bank   = int( data[0] ) + 1
        patt   = int( data[1] ) + 1

        swing  = data[2:4]
        if( swing[0] == 0 ): swing = 50 + int( swing[1] )
        else: swing = 66 + int( swing[1] )
        nsteps = int( data[5] )*8 + int( data[7] ) + 1

        self.builder.get_object( SEQ_SWING ).set_value( swing )
        self.builder.get_object( SEQ_LENGTH ).set_value( nsteps )

        steps  = data[8:]
        self.notesStore.clear()
        for i in range(nsteps):
            step = steps[0:8]
            n = step[0:2]
            n = int( n[1] ) + int( n[0] )*16 + 1
            octave = int( n/12 ) - 1
            note = NOTES[ n%12 - 1]
            gate = GATES[ int(step[2]) ]
            ratchet = int( step[3] ) + 1
            velocity = int( step[5] ) + int( step[4] )*16
            glide  = 1 if( step[6] & 0x01 != 0 ) else 0
            accent = 1 if( step[6] & 0x04 != 0 ) else 0
            rest   = 1 if( step[6] & 0x08 != 0 ) else 0
            unk      = step[7]
            self.notesStore.append( [ i + 1, rest, note, octave, gate, ratchet, velocity, glide, accent ] )
            steps = steps[8:]

        self.fromDevice = False


# Show Time
if( __name__ == "__main__" ):
    synth = SynthCrave( "resources/SynthCrave.glade" )
    synth.run()
