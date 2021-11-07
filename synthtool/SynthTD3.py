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

UI_SEQ_PATTERN_GROUP   = "MainWin/Sequencer/Pattern Group"
UI_SEQ_PATTERN_SECTION = "MainWin/Sequencer/Pattern Section"
UI_SEQ_PATTERN         = "MainWin/Sequencer/Pattern"
UI_SEQ_LENGTH          = "MainWin/Sequencer/Length"
UI_SEQ_LENGTH_ADJ      = "Adjustment MainWin/Sequencer/Length"
UI_SEQ_LENGTH_TEXT     = "MainWin/Sequencer/Length text"
UI_SEQ_TRIPLET         = "MainWin/Sequencer/Triplet"
UI_SEQ_RECALL          = "MainWin/Sequencer/Recall"
UI_SEQ_STORE           = "MainWin/Sequencer/Store"
UI_SEQ_CLEAR           = "MainWin/Sequencer/Clear"

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

        self.ui_seq_pattern_group   = self.builder.get_object( UI_SEQ_PATTERN_GROUP )
        self.ui_seq_pattern_section = self.builder.get_object( UI_SEQ_PATTERN_SECTION )
        self.ui_seq_pattern         = self.builder.get_object( UI_SEQ_PATTERN )
        self.ui_seq_length          = self.builder.get_object( UI_SEQ_LENGTH )
        self.ui_seq_length_adj      = self.builder.get_object( UI_SEQ_LENGTH_ADJ )
        self.ui_seq_length_text     = self.builder.get_object( UI_SEQ_LENGTH_TEXT )
        self.ui_seq_triplet         = self.builder.get_object( UI_SEQ_TRIPLET )
        self.ui_seq_recall          = self.builder.get_object( UI_SEQ_RECALL )
        self.ui_seq_store           = self.builder.get_object( UI_SEQ_STORE )
        self.ui_seq_clear           = self.builder.get_object( UI_SEQ_CLEAR )

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

        #print( "RECV:", resp.hex().upper() )

        # firmware version
        if( resp[0:2] == bytes( [ 0x09, 0x00 ] ) ):
            fv = "Current Version: v%d.%d.%d" % (resp[2], resp[3], resp[4])
            GLib.idle_add( self.showFirmwareVersion, fv )

        # config values
        elif( resp[0] == 0x76 ):
            GLib.idle_add( self.showParameters, resp[1:] )

        # a pattern
        elif( resp[0] == 0x78 ):
            GLib.idle_add( self.showSequencer, resp[1:] )

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
        self.ui_pitch_bend.set_value( data[3] )
        self.ui_key_priority.set_active( data[4] )
        self.ui_midi_in_transpose.set_value( data[2] - 12 )
        self.ui_clock_source.set_active( data[8] )
        self.ui_clock_rate.set_active( data[7] )
        self.ui_clock_polarity.set_active( data[6] )
        self.ui_multi_trigger.set_active( data[5] )
        self.ui_acc_vel_thr.set_value( data[9] )

        self.set_sensitive()

        self.fromApp = False

    def set_sensitive( self ):
        clock_source = self.ui_clock_source.get_active()
        if( clock_source == 3  ):
            self.ui_clock_rate.set_sensitive( True )
            self.ui_clock_polarity.set_sensitive( True )
        else:
            self.ui_clock_rate.set_sensitive( False )
            self.ui_clock_polarity.set_sensitive( False )

    def onMidiInChanged( self, widget ):
        if( self.fromApp ): return
        channel_in = int( widget.get_value() ) - 1
        channel_out = int( self.ui_midi_out_channel.get_value() ) - 1
        data = [ 0x0E, 0x01, channel_out, channel_in ]
        self.sendSysEx( data )

    def onMidiOutChanged( self, widget ):
        if( self.fromApp ): return
        channel_out = int( widget.get_value() ) - 1
        channel_in = int( self.ui_midi_in_channel.get_value() ) - 1
        data = [ 0x0E, 0x01, channel_out, channel_in ]
        self.sendSysEx( data )

    def onPitchBendChanged( self, widget ):
        if( self.fromApp ): return
        semitone = int( widget.get_value() )
        data = [ 0x11, semitone, 0x00 ]
        self.sendSysEx( data )

    def onKeyPriorityChanged( self, widget ):
        if( self.fromApp ): return
        priority = int( widget.get_active() )
        data = [ 0x12, priority ]
        self.sendSysEx( data )

    def onMidiInTransposeChanged( self, widget ):
        if( self.fromApp ): return
        transpose = int( widget.get_value() ) + 12
        data = [ 0x0F, transpose ]
        self.sendSysEx( data )

    def onMultiTriggerChanged( self, widget ):
        if( self.fromApp ): return
        multitrigger = int( widget.get_active() )
        data = [ 0x14, multitrigger, 0x00 ]
        self.sendSysEx( data )

    def onClockSourceChanged( self, widget ):
        if( self.fromApp ): return
        source = int( widget.get_active() )
        data = [ 0x1B, source ]
        self.sendSysEx( data )

        self.set_sensitive()

    def onClockRateChanged( self, widget ):
        if( self.fromApp ): return
        rate = int( widget.get_active() )
        data = [ 0x1A, rate ]
        self.sendSysEx( data )

    def onClockPolarityChanged( self, widget ):
        if( self.fromApp ): return
        polarity = int( widget.get_active() )
        data = [ 0x19, polarity ]
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

        # num, rest, note, octave, slide, accent
        self.ui_notes_store.append( [ 1, False, "C", 2, False, False, True ] )

        self.fromApp = True
        self.ui_seq_length.set_value( 1 )
        self.ui_seq_triplet.set_active( 0 )
        self.fromApp = False

    def onSeqRecallClicked( self, widget ):
        patt_grp = int( self.ui_seq_pattern_group.get_active() )
        patt_sec = int( self.ui_seq_pattern_section.get_active() )
        patt = int( self.ui_seq_pattern.get_active() )
        self.sendSysEx( [ 0x77, patt_grp, patt_sec << 3 | patt ] )

    def onStoreClicked( self, widget ):
        patt_grp = int( self.ui_seq_pattern_group.get_active() )
        patt_sec = int( self.ui_seq_pattern_section.get_active() )
        patt = int( self.ui_seq_pattern.get_active() )
        data = [ patt_grp, patt_sec << 4 | patt, 0x00, 0x00 ]

        notes   = []
        accents = []
        slides  = []

        nsteps  = len( self.ui_notes_store )
        mask_1 = 0x0000
        mask_2 = 0x0000
        i = 0
        while( i < 16 ):
            if( i < nsteps ):
                row = self.ui_notes_store[i][1:6]
                rest = row[0]
                note = row[1]
                octave = row[2]
                slide = row[3]
                accent = row[4]

                if( octave == 4 ):
                    n = 0xB0
                else:
                    n = octave*12 + NOTES.index( note )
                notes = notes + [ n>>4 , n & 0x0F ]
                accents = accents + [ 0x00, accent ]
                slides  = slides + [ 0x00, slide ]
                if( rest ):
                    mask_2 = mask_2 | ( 1 << i )
            else:
                notes   = notes + [ 0x01, 0x08 ]
                accents = accents + [ 0x00, 0x00 ]
                slides  = slides + [ 0x00, 0x00 ]
            i = i + 1

        data = data + notes + accents + slides + [ 0x00, self.ui_seq_triplet.get_active(), (nsteps>>4) & 0x0F, nsteps & 0x0F, 0x00, 0x00 ]
        data = data + [ (mask_1 & 0x00F0)>>4, mask_1 & 0x000F, (mask_1 & 0xF000)>>12, (mask_1 & 0x0F00)>>8 ]
        data = data + [ (mask_2 & 0x00F0)>>4, mask_2 & 0x000F, (mask_2 & 0xF000)>>12, (mask_2 & 0x0F00)>>8 ]
        print( bytes(data).hex().upper() )
        return

        self.sendSysEx( [ 0x78 ] + data )

    def onSeqLengthChanged( self, widget ):
        if( self.fromApp ): return

        l = int( widget.get_value() )
        n = len( self.ui_notes_store )

        if( l > n ):
            l = l - n
            for i in range( l ):
                self.ui_notes_store.append( [ n+i+1, False, "C", 2, False, False, True ] )
        elif( l < n ):
            elems = []
            for i in range( l, n ):
                elems.append( self.ui_notes_store[i].iter )
            for e in elems:
                self.ui_notes_store.remove( e )

    def onTripletChanged( self, widget ):
        if( self.fromApp ): return
        triplet = widget.get_active()
        if( triplet ):
            self.ui_seq_length_text.set_text( "[1, 15]" )
            self.ui_seq_length_adj.set_upper( 15 )
            n = len( self.ui_notes_store )
            if( n == 16 ):
                self.ui_seq_length.set_value( 15 )
        else:
            self.ui_seq_length_text.set_text( "[1, 16]" )
            self.ui_seq_length_adj.set_upper( 16 )

    def onRestToggled( self, cell, path ):
        rest = not self.ui_notes_store[path][1]
        self.ui_notes_store[path][1]= rest

        # la fila no es editables si es un silencio
        self.ui_notes_store[path][6] = not rest

    def onNotedEdited( self, cell, path, tree_iter ):
        note = tree_iter
        octave = self.ui_notes_store[path][3]
        if( note != "C" and octave == 4 ):
            note = "C"
        self.ui_notes_store[path][2] = note

    def onOctaveEdited( self, cell, path, tree_iter ):
        octave = int( tree_iter )
        note = self.ui_notes_store[path][2]
        if( note != "C" and octave == 4 ):
            octave = 3
        self.ui_notes_store[path][3] = octave

    def onSlideToggled( self, cell, path ):
        self.ui_notes_store[path][4]= not self.ui_notes_store[path][4]

    def onAccentToggled( self, cell, path ):
        self.ui_notes_store[path][5]= not self.ui_notes_store[path][5]

    def showSequencer( self, data ):
        print( data.hex().upper() )
        self.fromApp = True
        patt_grp = int( data[0] )
        patt_sec = 0 if int( data[1] ) & 0x08 == 0 else 1
        patt     = int( data[1] ) & 0x07
        notes    = data[4:36]
        accents  = data[36:68]
        slides   = data[68:100]
        triplet  = int( data[101] )
        nsteps   = int( data[102] )*16 + int( data[103] )

        mask   = data[106:110]
        mask_1 = ( mask[2]&0x0F )<< 12 | ( mask[3]&0x0F )<<8 | ( mask[0]&0x0F )<<4 | ( mask[1]&0x0F )
        mask   = data[110:114]
        mask_2 = ( mask[2]&0x0F )<< 12 | ( mask[3]&0x0F )<<8 | ( mask[0]&0x0F )<<4 | ( mask[1]&0x0F )

        self.ui_seq_pattern_group.set_active( patt_grp )
        self.ui_seq_pattern_section.set_active( patt_sec )
        self.ui_seq_pattern.set_active( patt )
        self.ui_seq_length.set_value( nsteps  )
        self.ui_seq_triplet.set_active( triplet )
        if( triplet ):
            self.ui_seq_length_text.set_text( "[1, 15]" )
            self.ui_seq_length_adj.set_upper( 15 )
        else:
            self.ui_seq_length_text.set_text( "[1, 16]" )
            self.ui_seq_length_adj.set_upper( 16 )

        self.ui_notes_store.clear()
        for i in range(nsteps):
            n = int( notes[0] )<<4 | int( notes[1] )&0x0F
            if( n <= 0x2F ):
                octave = int( n/12 )
                note = NOTES[ n%12]
            else:
                octave = 4
                note ="C"
            rest   = mask_2 & 0x01
            accent = accents[1] if rest == 0 else 0
            slide  = slides[1]  if rest == 0 else 0
            self.ui_notes_store.append( [ i + 1, rest, note, octave, slide, accent, not rest ] )

            if( rest == 0 ):
                notes   = notes[2:]
                accents = accents[2:]
                slides  = slides[2:]
            else:
                pass

            mask_2 = mask_2 >> 1

        self.fromApp = False


# Show Time
if( __name__ == "__main__" ):
    synth = SynthTD3( "resources/SynthTD3.glade" )
    synth.run()
