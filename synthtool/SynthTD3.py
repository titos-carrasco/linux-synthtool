import time
import rtmidi
import queue

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk,GLib

DEVICE_NAME     = "TD-3 MIDI"
MANUF_ID        = [ 0x00, 0x20, 0x32 ]  # Behringer GmbH
DEVICE_ID       = [ 0x00, 0x01, 0x0A ]  # TD-3

UI_MAIN_WIN           = "MainWin"
UI_ERROR_WIN          = "ErrorWin"
UI_STATUS_BAR         = "MainWin/Status Bar"
UI_MIDI_IN_CHANNEL    = "MainWin/General/MIDI IN Channel"
UI_MIDI_OUT_CHANNEL   = "MainWin/General/MIDI OUT Channel"
UI_PITCH_BEND         = "MainWin/General/Pitch Bend"
UI_KEY_PRIORITY       = "MainWin/General/Key Priority"
UI_MIDI_IN_TRANSPOSE  = "MainWin/General/MIDI IN Transpose"
UI_MULTI_TRIGGER      = "MainWin/General/Multi Trigger"
UI_MULTI_TRIGGER_MODE = "MainWin/General/Multi Trigger Mode"
UI_CLOCK_SOURCE       = "MainWin/General/Clock Source"
UI_CLOCK_RATE         = "MainWin/General/Clock Rate"
UI_CLOCK_POLARITY     = "MainWin/General/Clock Polarity"
UI_ACC_VEL_THR        = "MainWin/General/Accent Velocity Threshold"
UI_NOTES_TREE         = "MainWin/Sequencer/Notes"
UI_NOTES_STORE        = "ListStore MainWin/Sequencer/Notes"
UI_FIRMWARE_VERSION   = "MainWin/Update/Firmware Version"

UI_SEQ_BANK         = "MainWin/Sequencer/Bank"
UI_SEQ_PATTERN      = "MainWin/Sequencer/Pattern"
UI_SEQ_CLEAR        = "MainWin/Sequencer/Clear"
UI_SEQ_RECALL       = "MainWin/Sequencer/Recall"
UI_SEQ_STORE        = "MainWin/Sequencer/Store"
UI_SEQ_LENGTH       = "MainWin/Sequencer/Length"
UI_SEQ_SWING        = "MainWin/Sequencer/Swing"

GATES = [ "12.5%", "25.0%", "37.5%", "50.0%", "62.5%", "75.0%", "87.5%", "100%" ]
NOTES = [ "C","C#","D","D#","E","F","F#","G","G#","A","A#","B" ]


class SynthTD3():

    def __init__( self, filedef ):
        self.midiIn = rtmidi.MidiIn()
        self.midiOut = rtmidi.MidiOut()
        self.midiIn.ignore_types( sysex=False )

        self.builder = Gtk.Builder()
        self.builder.add_from_file( filedef )

        self.ui_error_win          = self.builder.get_object( UI_ERROR_WIN )
        self.ui_main_win           = self.builder.get_object( UI_MAIN_WIN )
        self.ui_status_bar         = self.builder.get_object( UI_STATUS_BAR )
        self.ui_midi_in_channel    = self.builder.get_object( UI_MIDI_IN_CHANNEL )
        self.ui_midi_out_channel   = self.builder.get_object( UI_MIDI_OUT_CHANNEL )
        self.ui_pitch_bend         = self.builder.get_object( UI_PITCH_BEND )
        self.ui_key_priority       = self.builder.get_object( UI_KEY_PRIORITY )
        self.ui_midi_in_transpose  = self.builder.get_object( UI_MIDI_IN_TRANSPOSE )
        self.ui_multi_trigger      = self.builder.get_object( UI_MULTI_TRIGGER )
        self.ui_multi_trigger_mode = self.builder.get_object( UI_MULTI_TRIGGER_MODE )
        self.ui_clock_source       = self.builder.get_object( UI_CLOCK_SOURCE )
        self.ui_clock_rate         = self.builder.get_object( UI_CLOCK_RATE )
        self.ui_clock_polarity     = self.builder.get_object( UI_CLOCK_POLARITY )
        self.ui_acc_vel_thr        = self.builder.get_object( UI_ACC_VEL_THR )
        self.ui_notes_tree         = self.builder.get_object( UI_NOTES_TREE )
        self.ui_notes_store        = self.builder.get_object( UI_NOTES_STORE )
        self.ui_firmware_version   = self.builder.get_object( UI_FIRMWARE_VERSION )

        self.ui_seq_bank    = self.builder.get_object( UI_SEQ_BANK )
        self.ui_seq_pattern = self.builder.get_object( UI_SEQ_BANK )
        self.ui_seq_length  = self.builder.get_object( UI_SEQ_LENGTH )
        self.ui_seq_swing   = self.builder.get_object( UI_SEQ_SWING )

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
        print( "SEND:", bytes( sysex ).hex().upper() )

        self.waiting = True
        self.midiOut.send_message( sysex )
        t = time.time()
        while( self.waiting and (time.time() - t) < 0.5): time.sleep( 0.01 )
        self.waiting = False

    def midiCallback( self, msg, data=None ):
        data = bytes( msg[0] )

        start = data[:7]
        resp  = data[7:-1]
        end   = data[-1]

        if( start != bytes( [ 0xF0 ] + MANUF_ID + DEVICE_ID ) ): return
        if( len( resp ) == 0 ): return
        if( end != 0xF7 ): return

        print( "RECV:", resp.hex().upper() )

        # firmware version
        if( resp[0:2] == bytes( [ 0x09, 0x00 ] ) ):
            fv = "Current Version: v%d.%d.%d" % (resp[2], resp[3], resp[4])
            GLib.idle_add( self.showFirmwareVersion, fv )

        # config values
        elif( resp[0] == 0x76 ):
            GLib.idle_add( self.showParameters, resp[1:] )

        # a pattern
        #elif( resp[0] == 0x78 ):
        #    GLib.idle_add( self.showSequencer, resp[1:] )

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

        self.ui_midi_in_channel.set_value( data[1] + 1 )
        self.ui_midi_out_channel.set_value( data[0] + 1 )
        #self.ui_pitch_bend.set_value( data[3] )
        #self.ui_key_priority.set_active( data[4] )
        #self.ui_midi_in_transpose.set_value( data[2] - 12 )
        #self.ui_multi_trigger.set_active( data[5] )
        #self.ui_multi_trigger_mode.set_active( data[6] )
        #self.ui_clock_source.set_active( data[8] )
        #self.ui_clock_rate.set_active( data[7] )
        #self.ui_clock_polarity.set_active( data[7] )
        #self.ui_acc_vel_thr.set_value( data[9] )

        self.fromApp = False

    def onPitchBendChanged( self, widget ):
        if( self.fromApp ): return
        pitch_bend = int( widget.get_value() )
        data = [ 0x11, pitch_bend, 0x00 ]
        self.sendSysEx( data )

    def onClockSourceChanged( self, widget ):
        if( self.fromApp ): return
        clock_source = int( widget.get_active() )
        data = [ 0x1B, clock_source ]
        self.sendSysEx( data )

    def onClockTypeChanged( self, widget ):
        if( self.fromApp ): return
        clock_type = int( widget.get_active() )
        data = [ 0x1A, clock_type ]
        self.sendSysEx( data )

    def onClockEdgeChanged( self, widget ):
        if( self.fromApp ): return
        clock_edge = int( widget.get_active() )
        data = [ 0x19, clock_edge ]
        self.sendSysEx( data )

    def onMidiClockOutChanged( self, widget ):
        if( self.fromApp ): return
        clock_out = int( widget.get_active() )
        data = [ 0x17, clock_out ]
        self.sendSysEx( data )

    def onAssignModeChanged( self, widget ):
        if( self.fromApp ): return
        assign_mode = int( widget.get_active() )
        data = [ 0x1F, assign_mode ]
        self.sendSysEx( data )

    def onAutoPlayChanged( self, widget ):
        if( self.fromApp ): return
        auto_play = int( widget.get_active() )
        data = [ 0x1D, auto_play ]
        self.sendSysEx( data )

    def onAccentVelocityThresholdChanged( self, widget ):
        if( self.fromApp ): return
        threshold = int( widget.get_value() )
        data = [ 0x1C, threshold ]
        self.sendSysEx( data )

    def onFactorySettingClicked( self, widget ):
        # restore factory settings
        self.sendSysEx( [ 0x7D ] )

        # get config
        self.sendSysEx( [ 0x75 ] )

    # Tab Sequencer
    def onClearClicked( self, widget ):
        self.ui_notes_store.clear()

        # num, rest, note, octave, gate, ratchet, velocitym glide, accent
        self.ui_notes_store.append( [ 1, False, "C", 3, "50.0%", 1, 64, False, False ] )

        self.fromApp = True
        self.ui_seq_length.set_value( 1 )
        self.ui_seq_swing.set_value( 50 )
        self.fromApp = False

    def onSeqRecallClicked( self, widget ):
        bank = int( self.ui_seq_bank.get_active() )
        patt = int( self.ui_seq_pattern.get_active() )
        self.sendSysEx( [ 0x77, bank, patt ] )

    def onStoreClicked( self, widget ):
        bank  = int( self.ui_seq_bank.get_active() )
        patt  = int( self.ui_seq_pattern.get_active() )
        steps = int( self.ui_seq_length.get_value() ) - 1
        swing = int( self.ui_seq_swing.get_value() )

        data = [0]*8
        data[0] = bank
        data[1] = patt
        data[2] = 0 if swing< 66 else 1
        data[3] = swing-50 if swing < 66 else swing - 66
        data[4] = 0
        data[5] = steps >> 3
        data[6] = 0
        data[7] = steps & 0x07

        n = len( self.ui_notes_store )
        for i in range( n ):
            elem     = self.ui_notes_store[i].iter
            rest     = int( self.ui_notes_store[elem][1] )
            note     = NOTES.index( self.ui_notes_store[elem][2] )
            octave   = int( self.ui_notes_store[elem][3] )
            gate     = GATES.index( self.ui_notes_store[elem][4] )
            ratchet  = int( self.ui_notes_store[elem][5] ) - 1
            velocity = int( self.ui_notes_store[elem][6] )
            glide    = int( self.ui_notes_store[elem][7] )
            accent   = int( self.ui_notes_store[elem][8] )

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
            data = data + [ 0X0F, 0X0F, 0X0F, 0X0F, 0X0F, 0X0F, 0X0F, 0X0F ]

        self.sendSysEx( [ 0x78 ] + data )

    def onSeqLengthChanged( self, widget ):
        if( self.fromApp ): return

        l = int( widget.get_value() )
        n = len( self.ui_notes_store )

        if( l > n ):
            l = l - n
            for i in range( l ):
                self.ui_notes_store.append( [ n+i+1, False, "C", 3, "50.0%", 1, 64, False, False ] )
        elif( l < n ):
            elems = []
            for i in range( l, n ):
                elems.append( self.ui_notes_store[i].iter )
            for e in elems:
                self.ui_notes_store.remove( e )

    def onRestToggled( self, cell, path ):
        self.ui_notes_store[path][1]= not self.ui_notes_store[path][1]

    def onNotedEdited( self, cell, path, tree_iter ):
        note = tree_iter
        octave = self.ui_notes_store[path][3]
        if( note != "C" and octave == 9 ):
            note = "C"
        self.ui_notes_store[path][2] = note

    def onOctaveEdited( self, cell, path, tree_iter ):
        octave = int( tree_iter )
        note = self.ui_notes_store[path][2]
        if( note != "C" and octave == 9 ):
            octave = 8
        self.ui_notes_store[path][3] = octave

    def onGateEdited( self, cell, path, tree_iter ):
        self.ui_notes_store[path][4] = tree_iter

    def onRatchetEdited( self, cell, path, tree_iter ):
        self.ui_notes_store[path][5] = int( tree_iter )

    def onVelocityEdited( self, cell, path, tree_iter ):
        try:
            v = int( tree_iter )
        except:
            v = 64
        v = 0 if v < 0 else v
        v= 127 if v > 127 else v
        self.ui_notes_store[path][6] = v

    def onGlideToggled( self, cell, path ):
        self.ui_notes_store[path][7]= not self.ui_notes_store[path][7]

    def onAccentToggled( self, cell, path ):
        self.ui_notes_store[path][8]= not self.ui_notes_store[path][8]

    def showSequencer( self, data ):
        self.fromApp = True

        bank   = int( data[0] ) + 1
        patt   = int( data[1] ) + 1

        swing  = data[2:4]
        if( swing[0] == 0 ): swing = 50 + int( swing[1] )
        else: swing = 66 + int( swing[1] )
        nsteps = int( data[5] )*8 + int( data[7] ) + 1

        self.ui_seq_swing.set_value( swing )
        self.ui_seq_length.set_value( nsteps )

        steps  = data[8:]
        self.ui_notes_store.clear()
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
            self.ui_notes_store.append( [ i + 1, rest, note, octave, gate, ratchet, velocity, glide, accent ] )
            steps = steps[8:]

        self.fromApp = False


# Show Time
if( __name__ == "__main__" ):
    synth = SynthTD3( "resources/SynthTD3.glade" )
    synth.run()
