from __future__ import print_function
import encoder
from usb_descriptor import *


def iap2_parm(parmid):
    """
    Create a iap2 bare parameter block (parameter header only)
    :param parmid: the iap2 parameter ID
    :return: a bytearray containing the newly created parameter block
    """
    pa = bytearray([0, 4, parmid >> 8, parmid & 0xFF])
    return pa


def iap2_parm_add_ba(pa, ba):
    """
    Add arbitrary data to a parameter block and adjust the length.
    :param pa: exiting parameter block as bytearray
    :param ba: new data to add to parameter block as bytearray
    :return: bytearray containing the updated parameter block
    """
    slen = (pa[0] << 8) + pa[1]
    slen += len(ba)
    pa[0] = slen >> 8
    pa[1] = slen & 0xFF
    pa.extend(ba)
    return pa


def iap2_parm_add_utf8(pa, utf8str):
    """
    Add a UTF8 string to an existing parameter block.
    :param pa: bytearray of existing parameter block
    :param utf8str: utf-8 string to add (will be converted to bytes)
    :return: bytearray containing updated parameter block
    """
    # make sure string is encoded to bytes
    try:
        s = utf8str.encode('utf-8')
    except UnicodeError:
        s = utf8str
    ba = bytearray(s)
    ba.extend([0])  # null terminate the string
    pa = iap2_parm_add_ba(pa, ba)
    return pa


def iap2_parm_add_n16(pa, n16):
    """
    Add 16 bit integer to existing parameter block.
    :param pa: bytearray of existing parameter block
    :param n16: value of 16 bit integer to add
    :return: bytearray containing updated parameter block
    """
    ba = bytearray([n16 >> 8, n16 & 0xFF])
    pa = iap2_parm_add_ba(pa, ba)
    return pa


def iap2_parm_utf8(parmid, utf8str):
    """
    Create a parameter block containing a UTF-8 string
    :param parmid: the iap2 parameter ID
    :param utf8str: utf-8 string
    :return: bytearray containing the created parameter block
    """
    pa = iap2_parm(parmid)
    pa = iap2_parm_add_utf8(pa, utf8str)
    return pa


def iap2_parm_n8(parmid, n8):
    """
    Create a parameter containing a single byte value
    :param parmid: the iap2 parameter ID
    :param n8: the byte value of the parameter
    :return: bytearray containing the new parameter
    """
    pa = iap2_parm(parmid)
    pa = iap2_parm_add_ba(pa, bytearray([n8]))
    return pa


def iap2_parm_n16(parmid, n16):
    """
    Add 16 bit integer to existing parameter block.
    :param parmid: the iap2 parameter ID
    :param n16: value of 16 bit integer to add
    :return: bytearray containing new parameter
    """
    return iap2_parm_add_n16(iap2_parm(parmid), n16)


def encode_mfi_features(d, _):
    """Encode the bits for the MFi features byte"""
    serial_protocol_enabled =\
        encoder.strtobool(d['serial_protocol_enabled'])
    io_protocol_enabled = encoder.strtobool(d['io_protocol_enabled'])
    now_playing_enabled = encoder.strtobool(d['enable_now_playing'])
    app_launch_enabled = encoder.strtobool(d['enable_app_launch'])

    bit_mask_value = 0
    bit_mask_value |= 0x0C if serial_protocol_enabled else 0
    bit_mask_value |= 0x10 if io_protocol_enabled else 0
    bit_mask_value |= 0x01 if now_playing_enabled else 0
    bit_mask_value |= 0x40 if app_launch_enabled else 0
    return bit_mask_value


def encode_power_options(d, _):
    """Encode the bits of the power options byte"""
    # CP2614_RCP uses max_current!=0 to set the PWR_ACC_DRAWS_POWER flag
    is_self_powered = bool(int(d['max_current_ma']) == 0)
    # is_self_powered = strtobool(d['self_powered'])
    provides_power = encoder.strtobool(d['provides_power'])
    bit_mask_value = 0
    bit_mask_value |= 0x01 if not is_self_powered else 0
    bit_mask_value |= 0x02 if provides_power else 0
    return bit_mask_value


def encode_ident(d, _):
    """Encode the iap2 identification parameters into byte array"""

    # figure out some conditional flags that are needed below
    np_enabled = encoder.strtobool(d['enable_now_playing'])
    hid_enabled = encoder.strtobool(d['enable_hid'])
    provides_power = encoder.strtobool(d['provides_power'])
    app_launch = encoder.strtobool(d['enable_app_launch'])
    iop_enabled = encoder.strtobool(d['io_protocol_enabled'])
    ser_proto_enabled = encoder.strtobool(d['serial_protocol_enabled'])

    # The order of parameters in the ident block below follows the logic
    # of the original RCP app.  I think the order is arbitrary so if this
    # was starting from scratch I might use a different order.  However
    # by making it match the RCP app, then we can compare the output
    # for testing.
    #
    # A lot of parameter have some kind of conditional logic.  This too
    # is copied from the RCP app.
    #
    # The ident parameter block is a byte array that contains all the
    # iAP2 identification parameters.  The parameter block/byte array
    # is built up by adding parameters to the byte array as we go.

    # first set of parameters are always present and just copy some
    # stuff from the input
    b = iap2_parm_utf8(0, d['prod'])  # accessory name
    b.extend(iap2_parm_utf8(1, d['model']))  # accessory model name
    b.extend(iap2_parm_utf8(2, d['mfr']))  # manufacturer name
    b.extend(iap2_parm_utf8(5, d['hw_version']))

    # now create the "messages sent" parameter block which has
    # some fixed and some optional values
    # The message sent parameter is one parameter of a bunch of
    # 16-bit values, but a lot of them are conditional.
    msgs_sent_parm = iap2_parm(6)
    if np_enabled:
        iap2_parm_add_n16(msgs_sent_parm, 0x5000)  # StartNowPlayingUpdates
        iap2_parm_add_n16(msgs_sent_parm, 0x5002)  # StopNowPlayingUpdates
    if hid_enabled:
        iap2_parm_add_n16(msgs_sent_parm, 0x6800)  # StartHid
        iap2_parm_add_n16(msgs_sent_parm, 0x6802)  # AccessoryHidReport
        iap2_parm_add_n16(msgs_sent_parm, 0x6803)  # StopHid
    iap2_parm_add_n16(msgs_sent_parm, 0xAE00)      # StartPowerUpdates
    iap2_parm_add_n16(msgs_sent_parm, 0xAE02)      # StopPowerUpdates
    if provides_power:
        iap2_parm_add_n16(msgs_sent_parm, 0xAE03)  # PowerSourceUpdate
    if app_launch:
        iap2_parm_add_n16(msgs_sent_parm, 0xEA02)  # RequestAppLaunch
    # thats all of the "Sent" messages.  Add to ident parameter block
    b.extend(msgs_sent_parm)

    # create the "messages received" parameter block
    # same as above - it has some fixed and some optional pieces
    msgs_rcvd_parm = iap2_parm(7)
    if hid_enabled:
        iap2_parm_add_n16(msgs_rcvd_parm, 0x6801)  # DeviceHidReport
    iap2_parm_add_n16(msgs_rcvd_parm, 0xAE01)      # PowerUpdate
    if iop_enabled:
        iap2_parm_add_n16(msgs_rcvd_parm, 0xEA00)  # StartEaProtocol
        iap2_parm_add_n16(msgs_rcvd_parm, 0xEA01)  # StopEaProtocol
    if np_enabled:
        iap2_parm_add_n16(msgs_rcvd_parm, 0x5001)  # NowPlayingUpdate
    # thats all of the "Received" messages.  Add to ident
    b.extend(msgs_rcvd_parm)

    # the PowerSourceType parameter.  This is dependent on whether the
    # accessory can provide power.
    pwr_source_type = 0x02 if provides_power else 0
    b.extend(iap2_parm_n8(8, pwr_source_type))

    # max power parameter - just get whatever the user provided
    # for an mfi accessory this is limited to 100 ma which fits in
    # an 8-bit value.
    max_power = int(d['max_current_ma'])
    b.extend(iap2_parm_n16(9, max_power))

    # mfi language is the two-character international language
    # code.  It is expressed as utf8 parameter in the ident block.
    # We count on the user or the input tool to ensure the user
    # places a correct value for this.
    # There are two related parameters - current language and
    # supported language.  There can be multiple parameters for supported
    # language but we only support one language and it is the same as
    # current language
    mfi_lang = d['mfi_lang']
    b.extend(iap2_parm_utf8(12, mfi_lang))  # current language
    b.extend(iap2_parm_utf8(13, mfi_lang))  # support language

    # Some parameters for the iAP2 ident block are parameter "groups".
    # A parameter group is a set of parameters wrapped by another parameter
    # header.  Below, to create parameter group(s) you will see parameters
    # being added to parameters.

    # USBHostTransportComponent group contains a
    # component ID and component name
    usb_group = iap2_parm(16)  # USBHostTransportComponent
    usb_id = iap2_parm_n16(0, 1)  # TransportComponentIdentifier (always 1)
    usb_name = iap2_parm_utf8(1, 'iAP2 Accessory')  # TransportComponentName
    # the following parameter presence is required - contains no value
    usb_iap2 = iap2_parm(2)  # TransportSupportsiAP2Connection
    usb_group = iap2_parm_add_ba(usb_group, usb_id)
    usb_group = iap2_parm_add_ba(usb_group, usb_name)
    usb_group = iap2_parm_add_ba(usb_group, usb_iap2)
    b.extend(usb_group)

    # iAP2HIDComponent contains and ID, name, and function
    # these are all fixed values not controlled by user except
    # for enablement
    if hid_enabled:
        hid_group = iap2_parm(18)  # iAP2HIDComponent
        hid_id = iap2_parm_n16(0, 2)  # HIDComponentIdentifier (always 2)
        hid_name = iap2_parm_utf8(1, 'Media Playback Remote')
        # HID function is enumeration, we use 1 - media playback remote
        hid_func = iap2_parm_n8(2, 1)  # HIDComponentFunction
        hid_group = iap2_parm_add_ba(hid_group, hid_id)
        hid_group = iap2_parm_add_ba(hid_group, hid_name)
        hid_group = iap2_parm_add_ba(hid_group, hid_func)
        b.extend(hid_group)

    # if EA protocol is enabled, then a parameter group is needed to identify
    # the EA protocol to the iOS host
    if iop_enabled:
        iop_group = iap2_parm(10)  # SupportedExternalAccessoryProtocol
        iop_id = iap2_parm_n8(0, 1)  # ExternalAccessoryProtocolIdentifier
        iop_name = iap2_parm_utf8(1, d['io_proto_name'])
        iop_action = iap2_parm_n8(2, int(d['io_proto_match']))
        iop_group = iap2_parm_add_ba(iop_group, iop_id)
        iop_group = iap2_parm_add_ba(iop_group, iop_name)
        iop_group = iap2_parm_add_ba(iop_group, iop_action)
        b.extend(iop_group)

    # same for serial protocol.  Serial protocol has additional parameter
    # to identify it as a native transport
    if ser_proto_enabled:
        ser_group = iap2_parm(10)  # SupportedExternalAccessoryProtocol
        ser_id = iap2_parm_n8(0, 2)  # ExternalAccessoryProtocolIdentifier
        ser_name = iap2_parm_utf8(1, d['serial_proto_name'])
        ser_action = iap2_parm_n8(2, int(d['serial_proto_match']))
        ser_native = iap2_parm_n16(3, 1)  # NativeTransportComponentIdentifier
        ser_group = iap2_parm_add_ba(ser_group, ser_id)
        ser_group = iap2_parm_add_ba(ser_group, ser_name)
        ser_group = iap2_parm_add_ba(ser_group, ser_action)
        ser_group = iap2_parm_add_ba(ser_group, ser_native)
        b.extend(ser_group)

    # thats all of the identification parameters
    return b


def encode_now_playing_items(d, item_dict):
    """Encode multiple now playing items into a list of 16-bit
    integers.  The input dictionary is queried for each possible
    item, and if it is enabled then it is added to the list."""
    ba = bytearray()
    for key in item_dict:
        item_enabled = encoder.strtobool(d[key])
        if item_enabled:
            item_val = item_dict[key]
            ba.extend([item_val >> 8, item_val & 0xFF])
    ba.extend([0xFF, 0xFF])
    return ba


def encode_now_playing_media_items(d, _):
    """Encode the now playing "media" items."""
    item_map = {
        'np_mediaitem_title': 1,
        'np_mediaitem_duration': 4,
        'np_mediaitem_album_title': 6,
        'np_mediaitem_track': 7,
        'np_mediaitem_track_count': 8,
        'np_mediaitem_artist': 12,
        'np_mediaitem_genre': 16,
        'np_mediaitem_composer': 18,
        'np_mediaitem_is_liked': 23,
        'np_mediaitem_is_banned': 24,
        'np_mediaitem_chapter_count': 27}
    return encode_now_playing_items(d, item_map)


def encode_now_playing_playback_items(d, _):
    """Encode the now playing "playback" items."""
    item_map = {
        'np_pbitem_status': 0,
        'np_pbitem_elapsed': 1,
        'np_pbitem_queue_index': 2,
        'np_pbitem_queue_count': 3,
        'np_pbitem_queue_chap_index': 4,
        'np_pbitem_shuffle_mode': 5,
        'np_pbitem_repeat_mode': 6,
        'np_pbitem_app_name': 7,
        'np_pbitem_itunes_radio_ad': 9,
        'np_pbitem_itunes_radio_name': 10,
        'np_pbitem_speed': 12,
        'np_pbitem_app_bundle': 16}
    return encode_now_playing_items(d, item_map)


def encode_config_descriptor(d, _):
    """Create the USB configuration descriptor"""
    is_self_powered = encoder.strtobool(d['self_powered'])
    max_current = int(d['max_current_ma'])
    # we always have a minimum of 1 interface (iAP2) and also
    # variable interfaces: EA serial, audio IN and OUT, and audio control
    num_interfaces = 1
    serial_protocol_enabled = encoder.strtobool(d['serial_protocol_enabled'])
    if serial_protocol_enabled:
        num_interfaces += 1
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
                                 iConf=0, self_powered=is_self_powered,
                                 max_power=max_current)
    cd.set_comment('Configuration descriptor')

    # next is the iAP interface which is always present.  It is a bulk
    # interface with IN and OUT endpoints
    iap_if = InterfaceDescriptor(0, alt=0, num_eps=2,
                                 if_class=0xFF, if_subclass=0xF0,
                                 if_protocol=0, iIface=4)
    iap_if.set_comment('iAP2 interface')
    iap_in_ep = EndpointDescriptor(1, EndpointDescriptor.DIR_INPUT, 64,
                                   xfer_type=EndpointDescriptor.XFER_BULK)
    iap_in_ep.set_comment('iAP2 bulk IN endpoint')
    iap_if.add_child(iap_in_ep)
    iap_out_ep = EndpointDescriptor(1, EndpointDescriptor.DIR_OUTPUT, 64,
                                    xfer_type=EndpointDescriptor.XFER_BULK)
    iap_out_ep.set_comment('iAP2 bulk OUT endpoint')
    iap_if.add_child(iap_out_ep)
    cd.add_child(iap_if)  # add the iAP2 interface to the config descriptor

    # next is EA serial bulk interface
    # if EA serial is enabled, then there is an alt 0 and and alt 1
    # with two bulk endpoints
    if serial_protocol_enabled:
        # create alt 0 with no endpoints and add to config desc
        ser_if0 = InterfaceDescriptor(1, alt=0, num_eps=0, if_class=0xFF,
                                      if_subclass=0xF0, if_protocol=1,
                                      iIface=5)
        ser_if0.set_comment('EA serial bulk interface alt 0')
        cd.add_child(ser_if0)  # add to config descriptor

        # create alt 1 with 2 bulk endpoints
        ser_if1 = InterfaceDescriptor(1, alt=1, num_eps=2, if_class=0xFF,
                                      if_subclass=0xF0, if_protocol=1,
                                      iIface=5)
        ser_if1.set_comment('EA serial bulk interface alt 1')
        ser_in_ep = EndpointDescriptor(2, EndpointDescriptor.DIR_INPUT, 32,
                                       xfer_type=EndpointDescriptor.XFER_BULK)
        ser_in_ep.set_comment('EA serial bulk IN endpoint')
        ser_if1.add_child(ser_in_ep)
        ser_out_ep = EndpointDescriptor(2, EndpointDescriptor.DIR_OUTPUT, 32,
                                        xfer_type=EndpointDescriptor.XFER_BULK)
        ser_out_ep.set_comment('EA serial bulk OUT endpoint')
        ser_if1.add_child(ser_out_ep)
        cd.add_child(ser_if1)  # add to the config descriptor

    # next is the audio interfaces
    # if any audio is enabled, then there will be an audio control interface
    if audio_if > 0:
        audio_out_is_enabled = (audio_if == 3) or (audio_if == 4) or (
            audio_if == 5) or (audio_if == 7)
        audio_in_is_enabled = (audio_if == 1) or (audio_if == 2) or (
            audio_if == 5) or (audio_if == 6)

        # the interface number depends on whether there is a serial if
        audio_if_num = 2 if serial_protocol_enabled else 1
        audio_ctrl_if =\
            InterfaceDescriptor(audio_if_num, alt=0, num_eps=0,
                                if_class=InterfaceDescriptor.CLASS_AUDIO,
                                if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOCONTROL)
        audio_ctrl_if.set_comment('Audio control interface')

        # audio control interface has an audio control header
        #
        # need to build the interfaces collection.  There is at least
        # one CS interface if we have any audio.  If we have bi-directional,
        # then there is another.  the numbering depends on whether there
        # was EA serial interface.  It should start with the next number after
        # the audio control interface number.
        # Bi-directional is enabled if the audio_if choice is 5
        audio_if_num += 1
        ifaces = [audio_if_num, audio_if_num+1] if (audio_if == 5)\
            else [audio_if_num]
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
        # in cp2614 there is no choice of sample rates - it always supports
        # 44 and 48
        # sample_rate = int(d['sample_rate'])
        sample_rate = 2
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
            # audio_if_num has the next interface number to use
            audio_out_alt0 =\
                InterfaceDescriptor(audio_if_num, alt=0, num_eps=0,
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
                    audio_if_num, alt=1, terminal_link=1, subframe_size=2,
                    ep_addr=3, ep_dir=EndpointDescriptor.DIR_OUTPUT,
                    max_packet=pkt_size,
                    sync_type=sync_type, rates=audio_rates, format_delay=2,
                    interval=1, lock_delay=lock_delay,
                    explicit_feedback=explicit_fb,
                    implicit_feedback=implicit_fb)
                audio_out_alt1.set_comment('Streaming OUT alt 1 - 16-bit')
            else:
                audio_out_alt1 =\
                    InterfaceDescriptor(audio_if_num, alt=1, num_eps=0,
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

                audio_out_alt2 = AudioStreamingSubtree(audio_if_num, alt=2,
                    terminal_link=1, subframe_size=3, ep_addr=3,
                    ep_dir=EndpointDescriptor.DIR_OUTPUT,
                    max_packet=pkt_size,
                    sync_type=sync_type, rates=audio_rates, format_delay=2,
                    interval=1, lock_delay=lock_delay,
                    explicit_feedback=explicit_fb, implicit_feedback=0)
                audio_out_alt2.set_comment('Streaming OUT alt 2 - 24-bit')
                cd.add_child(audio_out_alt2)

            audio_if_num += 1  # advance the interface number

        # finally, audio streaming IN interface
        if audio_in_is_enabled:
            in_if = audio_if_num  # next interface number
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


class ConfigEncoderCP2614(encoder.ConfigEncoder):
    """
    Device specific configuration encoder class.  This is derived from the
    common configuration ConfigEncoder class.  This class implements
    encode features specific to the CP2614.
    """
    def __init__(self):
        super(ConfigEncoderCP2614, self).__init__(cp2614_fields)

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
        'pid': "0xEAC0",
        'usb_lang': "0x0409",
        # mfi language is two-char language code
        # although it should probably match usb_lang, they are two
        # different configuration items
        'mfi_lang': "en",

        # Custom serial number can be enabled (yes | no)
        # SN is a UTF-8 string max 31 bytes.  Note that an UTF-8 character
        # may be more than 1 byte for non-ascii characters
        'use_custom_sn': "no",
        'custom_sn': "N/A: using internal SN",

        'mfr': "Silicon Labs",
        'prod': "CP2614 Accessory Audio Bridge EVB",

        'model': "MFI-SL-CP2614-EK",
        'hw_version': "4.0.0",

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
        # 'sample_rate': "2", --- CP2614 does not support this option

        # enable or disable feature unit (default should be yes)
        'enable_fu': "yes",

        # input terminal type: 0-line input, 1-microphone
        'input_terminal': "0",

        # output terminal type: 0-headphones, 1-speaker, 2-line output
        'output_terminal': "0",

        # I2S output clocks can be active when not streaming (yes|no)
        'mclk_active': "yes",
        'lrck_active': "no",

        # volume settings are in dB
        'vol_default_master': "-60",
        'vol_default_left': "-60",
        'vol_default_right': "-60",
        'vol_min': "-60",
        'vol_max': "0",
        'vol_min_counts': "-60",
        'vol_max_counts': "0",

        # dB per count, floating point number
        'vol_resolution': "0.5",

        ################
        # Codec configuration items

        # volume register size in bytes, 1 or 2
        'vol_reg_size': "1",

        # volume register can be signed (yes) or unsigned (no)
        'vol_is_signed': "yes",

        # starting bit position of volume field
        'vol_bit_start': "0",

        # volume register mask values
        'vol_and_mask': "0x007F",
        'vol_or_mask': "0x0000",

        # mute controls
        # playback mute uses codec register
        'mute_by_reg': "yes",

        # mute polarity is 0-low, 1-high
        'mute_polarity': "1",

        # mute bits in register
        'mute_mask': "0x0300",

        # I2C startup delay - milliseconds
        'i2c_delay': "5",

        # Codec I2C strings

        'codec_init':
            "43 44 02 00 63 57 03 94 00 99 50 57 03 94 2E 30 "
            "50 57 08 94 B2 07 FF F8 DC FC AC 50 57 03 94 3A "
            "F8 50 57 06 94 BC D3 23 81 46 50 57 03 94 00 00 "
            "50 57 03 94 03 5A 50 57 04 94 84 02 09 50 57 06 "
            "94 9A 44 44 44 44 50 57 03 94 2A 00 50 57 03 94 "
            "06 10 50 57 03 94 02 00 50 44 1E 00 57 04 94 9C "
            "7D 7D 50 00",
        'codec_high_to_low':
            "57 06 94 9A C4 C4 C4 C4 50 57 03 94 02 0F 50 43 00",
        'codec_low_to_high':
            "57 03 94 02 00 50 00",
        'codec_start':
            "00",
        'codec_stop':
            "00",
        'codec_left_vol_prefix':
            "57 03 94 1A",
        'codec_left_vol_suffix':
            "50 00",
        'codec_right_vol_prefix':
            "57 03 94 1B",
        'codec_right_vol_suffix':
            "50 00",
        'codec_get_mute_prefix':
            "57 02 94 0F 50 52 01 94 50 00",
        'codec_set_mute_prefix':
            "57 03 94 0F",
        'codec_set_mute_suffix':
            "50 00",
        'codec_set_rate_44':
            "57 03 94 05 0B 50 00",
        'codec_set_rate_48':
            "57 03 94 05 09 50 00",

        ################
        # MFi Options

        # app launch options
        'enable_app_launch': "yes",
        'app_bundle_id': "com.silabs.CP2614-DemoApp",

        # io protocol options
        'io_protocol_enabled': "yes",
        'io_proto_name': "com.silabs.cp2614.io",
        # match action options:
        # 0 - no action
        # 1 - optional action
        # 2 - no alert
        'io_proto_match': "0",

        # serial protocol options
        'serial_protocol_enabled': "no",
        'serial_proto_name': "com.silabs.cp2614.ser",
        'serial_proto_match': "0",

        'enable_hid': "yes",

        # auth chip is either 0x20 or 0x22, no other options
        'auth_chip_address': "0x20",
        'deassert_lowpwr_in_auth': "yes",

        ################
        # Now Playing options
        'enable_now_playing': "yes",

        # Now playing "media item" group
        # each item can be enabled or disabled
        'np_mediaitem_title': "yes",
        'np_mediaitem_duration': "yes",
        'np_mediaitem_album_title': "yes",
        'np_mediaitem_track': "yes",
        'np_mediaitem_track_count': "no",
        'np_mediaitem_artist': "yes",
        'np_mediaitem_genre': "no",
        'np_mediaitem_composer': "no",
        'np_mediaitem_is_liked': "no",
        'np_mediaitem_is_banned': "no",
        'np_mediaitem_chapter_count': "no",

        # now playing "playback item" group
        'np_pbitem_status': "yes",
        'np_pbitem_elapsed': "yes",
        'np_pbitem_queue_index': "no",
        'np_pbitem_queue_count': "no",
        'np_pbitem_queue_chap_index': "no",
        'np_pbitem_shuffle_mode': "no",
        'np_pbitem_repeat_mode': "no",
        # app name is required - can show to user but do not allow disable
        'np_pbitem_app_name': "yes",
        'np_pbitem_itunes_radio_ad': "no",
        'np_pbitem_itunes_radio_name': "no",
        'np_pbitem_speed': "no",
        # app bundle is required - can show to user but cannot disable
        'np_pbitem_app_bundle': "yes",

        ################
        # Power Options
        'self_powered': "yes",
        'provides_power': "no",
        'max_current_ma': "100",
        'charge_when_active': "no",
        # active and inactive supply is in mA
        'active_supply': "0",
        'charge_when_inactive': "no",
        'inactive_supply': "0",

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
        #   88 - SHUFFLE (I)
        #   89 - REPEAT (I)
        #   8A - SPEED_DEFAULT (I)
        #   8B - SPEED_FAST (I)
        #   8C - SPEED_SLOW (I)
        #   8D - RECMUTE (I)
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
cp2614_fields = [
    # output key,           function,               input key (if needed)
    ('cookie', encoder.encode_object, bytearray(b'2614')),
    ('version', encoder.encode_object, 1),
    ('configLockKey', encoder.encode_configlock, None),
    ('serialStringUtf8Usb', encoder.encode_serial_string, None),
    ('checksum', encoder.encode_object, 0),
    ('length', encoder.encode_object, 0),
    ('optionID', encoder.encode_n16, 'option_id'),
    ('debugMode', encoder.encode_n8, 'debug_mode'),
    ('defaultSampleRate', encoder.encode_object, 44),
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
    ('usbPlaybackFeatureUnitVolumeMinDb', encoder.encode_n8,
     'vol_min'),
    ('usbPlaybackFeatureUnitVolumeMinCounts', encoder.encode_n8,
     'vol_min_counts'),
    ('usbPlaybackFeatureUnitVolumeMaxDb', encoder.encode_n8,
     'vol_max'),
    ('usbPlaybackFeatureUnitVolumeMaxCounts', encoder.encode_n8,
     'vol_max_counts'),
    ('usbPlaybackFeatureUnitVolumeResDbX256',
     encoder.encode_vol_resolution, 'vol_resolution'),
    ('muteConfig', encoder.encode_mute_config, None),
    ('muteMask', encoder.encode_n16, 'mute_mask'),
    ('volumeSettingForMute', encoder.encode_object, 0),
    ('mfiFeatureFlags', encode_mfi_features, None),
    ('authChipAddress', encoder.encode_n8, 'auth_chip_address'),
    ('appLaunchBundleID', encoder.encode_utf8, 'app_bundle_id'),
    ('pinGpioMask', encoder.encode_gpio_mask, None),
    ('pinDirMask', encoder.encode_dir_mask, None),
    ('pinModeMask', encoder.encode_mode_mask, None),
    ('pinInitValue', encoder.encode_reset_mask, None),
    ('gpioAltFunctions', encoder.encode_alt_functions, None),
    ('buttonsConfiguration', encoder.encode_buttons, None),
    ('serialDataRate', encoder.encode_serial_rate, None),
    ('clkoutDivider', encoder.encode_n8, 'clkout_divider'),
    ('powerConfig', encode_power_options, None),
    ('availableSupplyWhenActive', encoder.encode_n16, 'active_supply'),
    ('availableSupplyWhenInactive', encoder.encode_n16, 'inactive_supply'),
    ('deviceCanChargeActive', encoder.encode_bool, 'charge_when_active'),
    ('deviceCanChargeInactive', encoder.encode_bool, 'charge_when_inactive'),
    ('usbDeviceDescriptor', encoder.encode_device_descriptor, None),
    ('usbConfigurationDescriptor', encode_config_descriptor, None),
    ('usbLanguageCode', encoder.encode_n16, 'usb_lang'),
    ('manufacturerStringUtf8Usb', encoder.encode_utf8usb, 'mfr'),
    ('productStringUtf8Usb', encoder.encode_utf8usb, 'prod'),
    ('serProtocolStringUtf8Usb', encoder.encode_utf8usb, 'serial_proto_name'),
    ('iap2IdentParms', encode_ident, None),
    ('iap2NowPlayingMediaItems', encode_now_playing_media_items, None),
    ('iap2NowPlayingPlaybackItems', encode_now_playing_playback_items, None),
    ('spareConfigElements', encoder.encode_object, bytearray(b'\xFF' * 16)),
    ('delayFromStandbyDeassertToCodecInitMs', encoder.encode_n8,
     'i2c_delay'),
    ('i2cCmdStrCodecInit', encoder.encode_i2c_cmdstr, 'codec_init'),
    ('i2cCmdStrCodecHighToLow', encoder.encode_i2c_cmdstr,
     'codec_high_to_low'),
    ('i2cCmdStrCodecLowToHigh', encoder.encode_i2c_cmdstr,
     'codec_low_to_high'),
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
    ('spareI2cCmdStr', encoder.encode_object, bytearray(b'\xFF' * 32)),
    ('endVarMarker', encoder.encode_object, bytearray(b'VEND')),
    ('endConfigMarker', encoder.encode_object, bytearray(b'STOP'))
]


def test():
    enc = ConfigEncoderCP2614()
    out_dict = enc.encode(ConfigEncoderCP2614.default_dict)
    print('[cp2614]')
    encoder.dump_dict(out_dict)

# Test driver
if __name__ == "__main__":
    test()
