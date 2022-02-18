from __future__ import print_function
import encoder
from usb_descriptor import *


def encode_io_options(d, _):
    """Encode the bits for the IO options byte"""
    serial_protocol_enabled = encoder.strtobool(d['serial_protocol_enabled'])
    io_protocol_enabled = encoder.strtobool(d['io_protocol_enabled'])
    # CP2615_A01 requires ENABLE_EAPROTO_IO flag always set to work around
    # an interface mapping issue
    # CP2615_A02 adds new flag ENABLE_BULK_ITF to force the IO interface on 
    # without requiring serial or io protocols
    bit_mask_value = 0x10 if is_rev_a01(d) else 0x02
    bit_mask_value |= 0x0C if serial_protocol_enabled else 0
    bit_mask_value |= 0x10 if io_protocol_enabled else 0
    bit_mask_value = 0xAA;
    return bit_mask_value


def encode_power_options(d, _):
    """Encode the bits of the power options byte"""
    # CP2615_RCP uses max_current!=0 to set the PWR_ACC_DRAWS_POWER flag
    is_self_powered = bool(int(d['max_current_ma']) == 0)
    # is_self_powered = strtobool(d['self_powered'])
    bit_mask_value = 0
    bit_mask_value |= 0x01 if not is_self_powered else 0
    return bit_mask_value


def encode_config_descriptor(d, _):
    """Create the USB configuration descriptor"""
    is_self_powered = encoder.strtobool(d['self_powered'])
    max_current = int(d['max_current_ma'])
    # we always have a minimum of 2 interfaces (HID and bulk IO) and also
    # variable interfaces: audio IN and OUT, and audio control
    num_interfaces = 2
    audio_if = int(d['audio_if'])  # audio interface configuration
    if audio_if != 0:
        # non-zero means at least one audio interface, which also
        # means there is an audio control interface
        num_interfaces += 2
    if audio_if == 5:
        num_interfaces += 1  # choice 5 means IN and OUT

    # now create the top level configuration descriptor
    cd = ConfigurationDescriptor(num_interfaces=num_interfaces,
                                 config_value=1,
                                 iConf=4, self_powered=is_self_powered,
                                 max_power=max_current)
    cd.set_comment('Configuration descriptor')

    # next is the HID interface which is always present.  It has a
    # standard interface descriptor and a HID report interface descriptor
    hid_ifd = InterfaceDescriptor(0, alt=0, num_eps=1,
                                  if_class=InterfaceDescriptor.CLASS_HID,
                                  if_subclass=0, if_protocol=0)
    hid_ifd.set_comment('HID interface')
    hid_desc = HidDescriptor(desc_list=[(UsbDescriptor.HIDREPORT, 39)])
    hid_desc.set_comment('HID Descriptor, report declaration')
    hid_ep1 = EndpointDescriptor(1, EndpointDescriptor.DIR_INPUT, 2,
                                 xfer_type=EndpointDescriptor.XFER_INTERRUPT,
                                 interval=20)
    hid_ep1.set_comment('HID endpoint')
    hid_ifd.add_child(hid_desc)  # add items to HID interface
    hid_ifd.add_child(hid_ep1)
    cd.add_child(hid_ifd)  # add the HID interface to the config descriptor

    # next is IOP bulk interface
    # we always have at least alt 0 present so create alt 0 first and
    # add it to the configuration desc
    iop_alt0 = InterfaceDescriptor(1, alt=0, if_class=0xFF,
                                   if_subclass=0x15,
                                   if_protocol=1)
    iop_alt0.set_comment('IOP bulk interface alt 0')
    cd.add_child(iop_alt0)

    # the IOP interface has alt 1 and alt2 depending on whether IO protocol
    # or serial is enabled.  serial is alt 1 and IO is alt 2.  If IO is
    # enabled then serial will be present as well
    serial_protocol_enabled = encoder.strtobool(d['serial_protocol_enabled'])
    io_protocol_enabled = encoder.strtobool(d['io_protocol_enabled'])
    if serial_protocol_enabled or io_protocol_enabled:
        iop_alt1 = InterfaceDescriptor(1, alt=1, num_eps=2, if_class=0xFF,
                                       if_subclass=0x15, if_protocol=1)
        iop_alt1.set_comment('IOP bulk interface alt 1 (serial)')
        iop_alt1_ep_in =\
            EndpointDescriptor(2, EndpointDescriptor.DIR_INPUT,
                               max_packet=64,
                               xfer_type=EndpointDescriptor.XFER_BULK)
        iop_alt1_ep_out =\
            EndpointDescriptor(2, EndpointDescriptor.DIR_OUTPUT,
                               max_packet=64,
                               xfer_type=EndpointDescriptor.XFER_BULK)
        iop_alt1.add_child(iop_alt1_ep_in)
        iop_alt1.add_child(iop_alt1_ep_out)  # add endpoints to interface
        cd.add_child(iop_alt1)  # add alt1 interface to config
    if io_protocol_enabled:
        iop_alt2 = InterfaceDescriptor(1, alt=2, num_eps=2, if_class=0xFF,
                                       if_subclass=0x15, if_protocol=1)
        iop_alt2.set_comment('IOP bulk interface alt 2 (IO protocol)')
        iop_alt2_ep_in =\
            EndpointDescriptor(2, EndpointDescriptor.DIR_INPUT,
                               max_packet=64,
                               xfer_type=EndpointDescriptor.XFER_BULK)
        iop_alt2_ep_out =\
            EndpointDescriptor(2, EndpointDescriptor.DIR_OUTPUT,
                               max_packet=64,
                               xfer_type=EndpointDescriptor.XFER_BULK)
        iop_alt2.add_child(iop_alt2_ep_in)
        iop_alt2.add_child(iop_alt2_ep_out)  # add endpoints to interface
        cd.add_child(iop_alt2)  # add alt 2 interface to config

    # next is the audio interfaces
    # if any audio is enabled, then there will be an audio control interface
    if audio_if > 0:
        audio_out_is_enabled = (audio_if == 3) or (audio_if == 4) or (
            audio_if == 5) or (audio_if == 7)
        audio_in_is_enabled = (audio_if == 1) or (audio_if == 2) or (
            audio_if == 5) or (audio_if == 6)

        audio_ctrl_if =\
            InterfaceDescriptor(2, alt=0, num_eps=0,
                                if_class=InterfaceDescriptor.CLASS_AUDIO,
                                if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOCONTROL)
        audio_ctrl_if.set_comment('Audio control interface')

        # audio control interface has an audio control header
        #
        # need to build the interfaces collection.  There is at least
        # interface 3 if we have any audio.  If we have bi-directional, then
        # there is also interface 4.  Bi-directional is enabled if
        # the audio_if choice is 5
        ifaces = [3, 4] if (audio_if == 5) else [3]
        audio_ctrl_hdr = AudioControlHeader(if_collection=ifaces)
        audio_ctrl_hdr.set_comment('Audio control header')

        # audio control interface has terminals and feature units, depending
        # on the setting of enable_fu
        enable_fu = encoder.strtobool(d['enable_fu'])

        # if audio output is enabled, then there will be an input terminal,
        # output terminal, and optionally a feature unit
        # for headphone output
        if audio_out_is_enabled:
            out_term_val = int(d['output_terminal'])
            if out_term_val == 1:
                out_term_type = TerminalDescriptor.TYPE_SPEAKER
            elif out_term_val == 2:
                out_term_type = TerminalDescriptor.TYPE_LINE
            else:
                out_term_type = TerminalDescriptor.TYPE_HEADPHONES

            hp_input_term =\
                InputTerminal(1, TerminalDescriptor.TYPE_USB_STREAMING,
                              num_channels=2, chan_config=3)
            hp_input_term.set_comment('Headphones input terminal')
            audio_ctrl_hdr.add_child(
                hp_input_term)  # add input term to audio hdr
            hp_source_id = 3 if enable_fu else 1
            hp_output_term = OutputTerminal(2, out_term_type, hp_source_id)
            hp_output_term.set_comment('Headphones output terminal')
            audio_ctrl_hdr.add_child(
                hp_output_term)  # add output term to audio hdr

            if enable_fu:
                play_fu = FeatureUnit(3, 1, 2, controls=[1, 2, 2])
                play_fu.set_comment('Headphones feature unit')
                audio_ctrl_hdr.add_child(play_fu)

        # do the same for audio input
        if audio_in_is_enabled:
            in_term_val = int(d['input_terminal'])
            in_term_type = TerminalDescriptor.TYPE_MICROPHONE \
                if in_term_val == 1 else TerminalDescriptor.TYPE_LINE

            line_input_term = InputTerminal(4, in_term_type,
                                            num_channels=2, chan_config=3)
            line_input_term.set_comment('Line input terminal')
            audio_ctrl_hdr.add_child(line_input_term)  # add input terminal
            line_source_id = 6 if enable_fu else 4
            line_output_term =\
                OutputTerminal(5, TerminalDescriptor.TYPE_USB_STREAMING,
                               line_source_id)
            line_output_term.set_comment('Line output terminal')
            audio_ctrl_hdr.add_child(
                line_output_term)  # add output terminal

            if enable_fu:
                line_fu = FeatureUnit(6, 4, 2, controls=[1, 0, 0])
                line_fu.set_comment('Line feature unit')
                audio_ctrl_hdr.add_child(line_fu)

        # add the audio control header (which contains the terminals and
        # feature units) to the audio control interface, and then add
        # the audio control interface to the configuration descriptor
        audio_ctrl_if.add_child(audio_ctrl_hdr)
        cd.add_child(audio_ctrl_if)

        # common audio settings
        sample_rate = int(d['sample_rate'])
        audio_rates = []
        if (sample_rate == 0) or (sample_rate == 2):
            audio_rates.append(48000)
        if (sample_rate == 1) or (sample_rate == 2):
            audio_rates.append(44100)
        use_async = encoder.strtobool(d['use_async'])
        sync_type = EndpointDescriptor.SYNC_ASYNC \
            if use_async else EndpointDescriptor.SYNC_SYNC
        lock_delay = 0 if use_async else 1

        # next is audio streaming out interface
        if audio_out_is_enabled:
            audio_out_alt0 =\
                InterfaceDescriptor(3, alt=0, num_eps=0,
                                    if_class=InterfaceDescriptor.CLASS_AUDIO,
                                    if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
            audio_out_alt0.set_comment('Streaming OUT alt 0')
            cd.add_child(audio_out_alt0)

            # 16-bit out (alt 1)
            if (audio_if == 3) or (audio_if == 4) or (audio_if == 5):

                # figure out feedback, if any
                # fb type and ep depends on whether in stream is also
                #  enabled
                explicit_fb = 0
                implicit_fb = 0
                if use_async:
                    if audio_in_is_enabled:
                        implicit_fb = 3
                    else:
                        explicit_fb = 3
                pkt_size = 196 if use_async else 200

                audio_out_alt1 = AudioStreamingSubtree(
                    3, alt=1, terminal_link=1, subframe_size=2, ep_addr=3,
                    ep_dir=EndpointDescriptor.DIR_OUTPUT,
                    max_packet=pkt_size,
                    sync_type=sync_type, rates=audio_rates, format_delay=2,
                    interval=1, lock_delay=lock_delay,
                    explicit_feedback=explicit_fb,
                    implicit_feedback=implicit_fb)
                audio_out_alt1.set_comment('Streaming OUT alt 1 - 16-bit')
            else:
                audio_out_alt1 =\
                    InterfaceDescriptor(3, alt=1, num_eps=0,
                                        if_class=InterfaceDescriptor.CLASS_AUDIO,
                                        if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
                audio_out_alt1.set_comment(
                    'Streaming OUT alt 1 - 16 bit not used')
            cd.add_child(audio_out_alt1)

            # 24-bit out (alt 2)
            if (audio_if == 4) or (audio_if == 7):
                # figure out feedback, if any
                # for 24 out there is no input, so its always explicit fb
                explicit_fb = 2 if use_async else 0
                pkt_size = 294 if use_async else 288

                audio_out_alt2 = AudioStreamingSubtree(
                    3, alt=2, terminal_link=1, subframe_size=3, ep_addr=3,
                    ep_dir=EndpointDescriptor.DIR_OUTPUT,
                    max_packet=pkt_size,
                    sync_type=sync_type, rates=audio_rates, format_delay=2,
                    interval=1, lock_delay=lock_delay,
                    explicit_feedback=explicit_fb, implicit_feedback=0)
                audio_out_alt2.set_comment('Streaming OUT alt 2 - 24-bit')
                cd.add_child(audio_out_alt2)

        # finally, audio streaming IN interface
        if audio_in_is_enabled:
            in_if = 4 if audio_out_is_enabled else 3
            audio_in_alt0 = \
                InterfaceDescriptor(in_if, alt=0, num_eps=0,
                                    if_class=InterfaceDescriptor.CLASS_AUDIO,
                                    if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
            audio_in_alt0.set_comment('Streaming IN alt 0')
            cd.add_child(audio_in_alt0)

            # 16-bit in (alt 1)
            if (audio_if == 1) or (audio_if == 2) or (audio_if == 5):

                # figure out feedback, if any
                # for input stream, there is no explicit feedback
                # implicit fb depends on whether there is also out stream
                implicit_fb =\
                    3 if (use_async and audio_out_is_enabled) else 0
                pkt_size = 196 if use_async else 200

                audio_in_alt1 = AudioStreamingSubtree(
                    in_if, alt=1, terminal_link=5, subframe_size=2,
                    ep_addr=3,
                    ep_dir=EndpointDescriptor.DIR_INPUT,
                    max_packet=pkt_size,
                    sync_type=sync_type, rates=audio_rates, format_delay=2,
                    interval=1, lock_delay=lock_delay,
                    explicit_feedback=0, implicit_feedback=implicit_fb)
                audio_in_alt1.set_comment('Streaming IN alt 1 - 16-bit')
            else:
                audio_in_alt1 =\
                    InterfaceDescriptor(in_if, alt=1, num_eps=0,
                                        if_class=InterfaceDescriptor.CLASS_AUDIO,
                                        if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
                audio_in_alt1.set_comment(
                    'Streaming IN alt 1 - 16-bit not used')
            cd.add_child(audio_in_alt1)

            # 24-bit in (alt 2)

            # for input-only, the fb addr is always 0
            pkt_size = 294 if use_async else 288

            if (audio_if == 2) or (audio_if == 6):
                audio_in_alt2 = AudioStreamingSubtree(
                    in_if, alt=2, terminal_link=5, subframe_size=3,
                    ep_addr=3,
                    ep_dir=EndpointDescriptor.DIR_INPUT,
                    max_packet=pkt_size,
                    sync_type=sync_type, rates=audio_rates, format_delay=2,
                    interval=1, lock_delay=lock_delay,
                    explicit_feedback=0, implicit_feedback=0)
                audio_in_alt2.set_comment('Streaming IN alt 2 - 24-bit')
                cd.add_child(audio_in_alt2)

    return cd.get_bytearray()


def is_rev_a01(d):
    """Return true if device revision is A01."""
    return 'A01' in d['device']


class ConfigEncoderCP2615(encoder.ConfigEncoder):
    """
    Device specific configuration encoder class.  This is derived from the
    common configuration ConfigEncoder class.  This class implements
    encode features specific to the CP2615.
    """
    def __init__(self, device='CP2615-A02'):
        super(ConfigEncoderCP2615, self).__init__(cp2615_fields)
        self.device = device.upper()

    def encode(self, input_dict):
        # Add device name to input so encoders can test revision
        input_dict['device'] = self.device
        return super(ConfigEncoderCP2615, self).encode(input_dict)

    # This is the default input dictionary.  It shows all the possible keys in
    # the input dictionary and the valid choices.  Individual keys have comments
    # as needed, but the following general rules apply:
    #
    # All input dictionary values are strings, even if the string just
    # contains a number.
    #
    # NUMBER FORMATS:
    #
    # All numbers are assumed decimal unless prepended with 0x
    # except for byte arrays which are to be space-separated hex
    # bytes with no leading 0x.  Byte arrays must also always
    # have 2 digits even if leading digit is a '0'
    #
    # All strings are UTF-8
    #
    # Boolean keys can have values of any of the following to mean true:
    #   'y', 'yes', 't', 'true', 'on', '1'
    # any other value on a boolean key will mean false
    #
    default_dict = {
        # General configuration items
        'vid': "0x10C4",
        'pid': "0xEAC1",
        'usb_lang': "0x0409",

        # Custom serial number can be enabled (yes | no)
        # SN is a UTF-8 string max 31 bytes.  Note that an UTF-8 character
        # may be more than 1 byte for non-ascii characters
        'use_custom_sn': "no",
        'custom_sn': "N/A: using internal SN",

        'mfr': "Silicon Labs",
        'prod': "CP2615 Digital Audio Bridge",

        # set to yes to lock configuration (can no longer be updated)
        'cfg_is_locked': "no",

        # user-specified 16-bit option ID (optional)
        'option_id': "0",

        # not used by end user, leave as 0
        'debug_mode': "0",

        ################
        # Audio configuration items

        # Audio interface selection
        # 0-none, 1-16in, 2-24/16in, 3-16out, 4-24/16out, 5-16in/out,
        # 6-24in, 7-24out
        'audio_if': "5",

        # set to yes to enable asynchronous mode
        'use_async': "no",

        # Supported sample rates: 0-48, 1=44, 2-44/48
        'sample_rate': "0",

        # eable or disable feature unit (default should be yes)
        'enable_fu': "yes",

        # input terminal type: 0-line input, 1-microphone
        'input_terminal': "0",

        # output terminal type: 0-headphones, 1-speaker, 2-line output
        'output_terminal': "0",

        # I2S output clocks can be active when not streaming (yes|no)
        'mclk_active': "yes",
        'lrck_active': "no",

        # volume settings are in dB
        'vol_default_master': "0",
        'vol_default_left': "0",
        'vol_default_right': "0",
        'vol_min': "-60",
        'vol_max': "0",
        'vol_min_counts': "95",
        'vol_max_counts': "255",

        # dB per count, floating point number
        'vol_resolution': "0.375",

        ################
        # Codec configuration items

        # volume register size in bytes, 1 or 2
        'vol_reg_size': "1",

        # volume register can be signed (yes) or unsigned (no)
        'vol_is_signed': "no",

        # starting bit position of volume field
        'vol_bit_start': "0",

        # volume register mask values
        'vol_and_mask': "0xFFFF",
        'vol_or_mask': "0x0000",

        # mute controls
        # playback mute uses codec register
        'mute_by_reg': "yes",

        # mute polarity is 0-low, 1-high
        'mute_polarity': "1",

        # mute bits in register
        'mute_mask': "0x0800",

        # I2C startup delay - milliseconds
        'i2c_delay': "5",

        # Codec I2C strings

        'codec_init':
            "43 44 02 00 63 57 07 E2 18 08 0A FE 00 00 50 57 "
            "0C E2 4E 19 02 00 01 1A 11 02 A0 00 12 50 57 03 "
            "E2 60 00 50 57 03 E2 77 2E 50 57 04 E2 A3 06 06 "
            "50 57 03 E2 71 02 50 57 03 E2 6F 01 50 57 03 E2 "
            "1F 50 50 57 03 E2 21 24 50 57 03 E2 6B 60 50 57 "
            "04 E2 00 77 77 50 00",
        'codec_high_to_low':
            "57 03 E2 1B 01 50 57 03 E2 13 0A 50 44 14 00 00",
        'codec_low_to_high':
            "00",
        'codec_start':
            "00",
        'codec_stop':
            "57 03 E2 1B 01 50 57 03 E2 13 0A 50 44 14 00 00",
        'codec_left_vol_prefix':
            "57 03 E2 04",
        'codec_left_vol_suffix':
            "50 00",
        'codec_right_vol_prefix':
            "57 03 E2 05",
        'codec_right_vol_suffix':
            "50 00",
        'codec_get_mute_prefix':
            "57 02 E2 18 50 52 01 E2 50 00",
        'codec_set_mute_prefix':
            "57 03 E2 18",
        'codec_set_mute_suffix':
            "50 00",
        'codec_set_rate_44':
            "57 03 E2 8F 11 50 57 03 E2 14 03 50 57 04 E2 0C "
            "00 00 50 57 03 E2 61 04 50 57 03 E2 19 0B 50 57 "
            "05 E2 16 00 0B 00 50 57 03 E2 1A FE 50 44 0A 00 "
            "57 03 E2 1B 61 50 00",
        'codec_set_rate_48':
            "57 03 E2 8F 11 50 57 03 E2 14 03 50 57 04 E2 0C "
            "00 00 50 57 03 E2 61 02 50 57 03 E2 19 13 50 57 "
            "05 E2 16 00 13 00 50 57 03 E2 1A FE 50 44 0A 00 "
            "57 03 E2 1B 61 50 00",
        'codec_profile_0':
            "00",
        'codec_profile_1':
            "00",
        'codec_profile_2':
            "00",

        ################
        # I/O Options
        'serial_protocol_enabled': "yes",
        'io_protocol_enabled': "no",
        # ignore proto_name - it is not required in the input dictionary
        'proto_name': "N/A",

        ################
        # Power Options
        'self_powered': "no",
        'max_current_ma': "100",

        ################
        # GPIO options
        #
        # settings for GPIO 00-07
        #
        # each gpio can be set for direction, drive mode, function, and
        # reset value
        #
        # gpio_nn_mode = [0-2]
        #   0 - input
        #   1 - output push pull
        #   2 - output open-drain
        #
        # gpio_nn_function (values in hex)
        #   00 - GPIO
        #   01 - SUSPEND (O)
        #   02 - SUSPEND/ (O)
        #   03 - LOWPWR (O)
        #   04 - LOWPWR/ (O)
        #   05 - RMUTE (O)
        #   06 - RMUTE/ (O)
        #   07 - VBUS_IS_5V (O)
        #   08 - PBMUTE (O)
        #   09 - PBMUTE/ (O)
        # **NOTE:** gap in values
        #   0F - EXT_SUPPLY (I)
        # **NOTE:** all buttons have bit7 set
        #   80 - PLAY_PAUSE (I)
        #   81 - FFWD (I)
        #   82 - REW (I)
        #   83 - MUTE (I)
        #   84 - VOL+ (I)
        #   85 - VOL- (I)
        #   86 - PLAY (I)
        #   87 - STOP (I)
        # **NOTE:** gap in values
        # **NOTE:** non-HID buttons have bit6 set
        #   C0 - GESTURE (I)
        #   CD - RECMUTE (I)
        #   CF - PROFILE_SEL (I)
        #
        # gpio_nn_reset = 0 | 1, reset value of the pin (should default to 1)

        'gpio_00_mode': "2",
        'gpio_00_function': "0",
        'gpio_00_reset': "1",

        'gpio_01_mode': "2",
        'gpio_01_function': "0",
        'gpio_01_reset': "1",

        'gpio_02_mode': "1",
        'gpio_02_function': "3",
        'gpio_02_reset': "1",

        'gpio_03_mode': "0",
        'gpio_03_function': "0x84",
        'gpio_03_reset': "1",

        'gpio_04_mode': "0",
        'gpio_04_function': "0x85",
        'gpio_04_reset': "1",

        'gpio_05_mode': "0",
        'gpio_05_function': "0x81",
        'gpio_05_reset': "1",

        'gpio_06_mode': "0",
        'gpio_06_function': "0x82",
        'gpio_06_reset': "1",

        'gpio_07_mode': "0",
        'gpio_07_function': "0x80",
        'gpio_07_reset': "1",

        # GPIO 08-15 are similar to 00-07 except that the function only has
        # two choices:
        #
        # gpio_nn_function (values in hex)
        #   00 - GPIO
        #   01 - fixed alternate function

        'gpio_08_mode': "0",
        'gpio_08_function': "1",
        'gpio_08_reset': "1",

        'gpio_09_mode': "0",
        'gpio_09_function': "0",
        'gpio_09_reset': "1",

        'gpio_10_mode': "1",
        'gpio_10_function': "1",
        'gpio_10_reset': "0",

        'gpio_11_mode': "0",
        'gpio_11_function': "0",
        'gpio_11_reset': "1",

        'gpio_12_mode': "0",
        'gpio_12_function': "0",
        'gpio_12_reset': "1",

        'gpio_13_mode': "1",
        'gpio_13_function': "1",
        'gpio_13_reset': "1",

        'gpio_14_mode': "0",
        'gpio_14_function': "1",
        'gpio_14_reset': "1",

        'gpio_15_mode': "0",
        'gpio_15_function': "0",
        'gpio_15_reset': "1",

        ################
        # Analog Pin Options (and Misc)

        'clkout_divider': "1",
        'serial_rate': "115200",

        'button_00': "0",
        'button_01': "0",
        'button_02': "0",
        'button_03': "0",
        'button_04': "0",
        'button_05': "0",
        'button_06': "0",
        'button_07': "0",
        'button_08': "0",
        'button_09': "0",
        'button_10': "0",
        'button_11': "0",
        'button_12': "0",
        'button_13': "0",
        'button_14': "0",

        ################
        # Gesture Button
        #   00 - Long Press
        #   01 - Single Click
        #   02 - Double Click
        #   03 - Triple Click
        'gesture_00': "0",
        'gesture_01': "0",
        'gesture_02': "0",
        'gesture_03': "0",
    }


"""
This list defines the transforms required on the input dictionary to
produce the output dictionary items.  The first column is the output
dictionary key - the item to produce.  The second column is the encoding
function that is responsible for encoding the output data item based
on some input.  The third column is a key for the input dictionary or
some other context-dependent object.  For simple items, there may be a
straightforward transform from the input key to the output key.  For more
complex items, it may be dependent on several input items, and so the
encoding function is more complex.
"""
cp2615_fields = [
    # output key,           function,               input key (if needed)
    ('cookie', encoder.encode_object, bytearray(b'2614')),
    ('version', encoder.encode_object, 1),
    ('configLockKey', encoder.encode_configlock, None),
    ('serialStringUtf8Usb', encoder.encode_serial_string, None),
    ('checksum', encoder.encode_object, 0),
    ('length', encoder.encode_object, 0),
    ('optionID', encoder.encode_n16, 'option_id'),
    ('debugMode', encoder.encode_n8, 'debug_mode'),
    ('defaultSampleRate', encoder.encode_object, 48),
    ('clockingConfig', encoder.encode_clocking, None),
    ('audioOpts', encoder.encode_audio_opts, None),
    ('volumeAndMask', encoder.encode_n16, 'vol_and_mask'),
    ('volumeOrMask', encoder.encode_n16, 'vol_or_mask'),
    ('volumeBitStartPos', encoder.encode_n8, 'vol_bit_start'),
    ('usbPlaybackFeatureUnitVolumeMasterDefaultDb', encoder.encode_n8,
     'vol_default_master'),
    ('usbPlaybackFeatureUnitVolumeLeftDefaultDb', encoder.encode_n8,
     'vol_default_left'),
    ('usbPlaybackFeatureUnitVolumeRightDefaultDb', encoder.encode_n8,
     'vol_default_right'),
    ('usbPlaybackFeatureUnitVolumeMinDb', encoder.encode_n8, 'vol_min'),
    ('usbPlaybackFeatureUnitVolumeMinCounts', encoder.encode_n8,
     'vol_min_counts'),
    ('usbPlaybackFeatureUnitVolumeMaxDb', encoder.encode_n8, 'vol_max'),
    ('usbPlaybackFeatureUnitVolumeMaxCounts', encoder.encode_n8,
     'vol_max_counts'),
    ('usbPlaybackFeatureUnitVolumeResDbX256',
     encoder.encode_vol_resolution, 'vol_resolution'),
    ('muteConfig', encoder.encode_mute_config, None),
    ('muteMask', encoder.encode_n16, 'mute_mask'),
    ('volumeSettingForMute', encoder.encode_object, 0),
    ('ioOptions', encode_io_options, None),    # aka mfiFeatureFlags
    ('unused-1', encoder.encode_object, 0),  # aka authChipAddress
    ('unused-2', encoder.encode_object, bytearray(b'N/A\x00')),
    # aka appLaunchBundleID
    ('pinGpioMask', encoder.encode_gpio_mask, None),
    ('pinDirMask', encoder.encode_dir_mask, None),
    ('pinModeMask', encoder.encode_mode_mask, None),
    ('pinInitValue', encoder.encode_reset_mask, None),
    ('gpioAltFunctions', encoder.encode_alt_functions, None),
    ('buttonsConfiguration', encoder.encode_buttons, None),
    ('serialDataRate', encoder.encode_serial_rate, None),
    ('clkoutDivider', encoder.encode_n8, 'clkout_divider'),
    ('powerConfig', encode_power_options, None),
    ('unused-3', encoder.encode_object, 0),
    ('unused-4', encoder.encode_object, 0),
    ('unused-5', encoder.encode_object, 0),
    ('unused-6', encoder.encode_object, 0),
    ('usbDeviceDescriptor', encoder.encode_device_descriptor, None),
    ('usbConfigurationDescriptor', encode_config_descriptor, None),
    ('usbLanguageCode', encoder.encode_n16, 'usb_lang'),
    ('manufacturerStringUtf8Usb', encoder.encode_utf8usb, 'mfr'),
    ('productStringUtf8Usb', encoder.encode_utf8usb, 'prod'),
    ('serProtocolStringUtf8Usb', encoder.encode_utf8usb, 'proto_name'),
    ('unused-7', encoder.encode_object, bytearray(b'\x00\x05\x00\x00\x00')),
    ('unused-8', encoder.encode_object, bytearray(b'\xff\xff')),
    ('unused-9', encoder.encode_object, bytearray(b'\xff\xff')),
    ('gestureDownTicks', encoder.encode_object, 40),
    ('gestureUpTicks', encoder.encode_object, 9),
    ('gestureButtons', encoder.encode_gestures, None),
    ('spareConfigElements', encoder.encode_object, bytearray(b'\xFF' * 10)),
    ('delayFromStandbyDeassertToCodecInitMs', encoder.encode_n8, 'i2c_delay'),
    ('i2cCmdStrCodecInit', encoder.encode_i2c_cmdstr, 'codec_init'),
    ('i2cCmdStrCodecHighToLow', encoder.encode_i2c_cmdstr, 'codec_high_to_low'),
    ('i2cCmdStrCodecLowToHigh', encoder.encode_i2c_cmdstr, 'codec_low_to_high'),
    ('i2cCmdStrCodecStart', encoder.encode_i2c_cmdstr, 'codec_start'),
    ('i2cCmdStrCodecStop', encoder.encode_i2c_cmdstr, 'codec_stop'),
    ('i2cCmdStrSetVolumeLeftPrefix', encoder.encode_i2c_cmdstr,
     'codec_left_vol_prefix'),
    ('i2cCmdStrSetVolumeLeftSuffix', encoder.encode_i2c_cmdstr,
     'codec_left_vol_suffix'),
    ('i2cCmdStrSetVolumeRightPrefix', encoder.encode_i2c_cmdstr,
     'codec_right_vol_prefix'),
    ('i2cCmdStrSetVolumeRightSuffix', encoder.encode_i2c_cmdstr,
     'codec_right_vol_suffix'),
    ('i2cCmdStrGetMutePrefix', encoder.encode_i2c_cmdstr,
     'codec_get_mute_prefix'),
    ('i2cCmdStrSetMutePrefix', encoder.encode_i2c_cmdstr,
     'codec_set_mute_prefix'),
    ('i2cCmdStrSetMuteSuffix', encoder.encode_i2c_cmdstr,
     'codec_set_mute_suffix'),
    ('i2cCmdStrSetSampleRate44', encoder.encode_i2c_cmdstr,
     'codec_set_rate_44'),
    ('i2cCmdStrSetSampleRate48', encoder.encode_i2c_cmdstr,
     'codec_set_rate_48'),
    ('i2cCmdStrProfile0', encoder.encode_i2c_profile, 'codec_profile_0'),
    ('i2cCmdStrProfile1', encoder.encode_i2c_profile, 'codec_profile_1'),
    ('i2cCmdStrProfile2', encoder.encode_i2c_profile, 'codec_profile_2'),
    ('spareI2cCmdStr', encoder.encode_object, bytearray(b'\xFF' * 20)),
    ('endVarMarker', encoder.encode_object, bytearray(b'VEND')),
    ('endConfigMarker', encoder.encode_object, bytearray(b'STOP'))
]


def test():
    enc = ConfigEncoderCP2615()
    out_dict = enc.encode(ConfigEncoderCP2615.default_dict)
    print('[cp2615]')
    encoder.dump_dict(out_dict)

# Test driver
if __name__ == "__main__":
    test()
