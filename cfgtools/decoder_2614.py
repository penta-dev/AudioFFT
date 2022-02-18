#!/usr/bin/env python
#
# CP2614 configuration decoder
#

from __future__ import print_function
import array
import sys
import decoder


# The following are decoder function specific to the CP2614


def _ba2str(ba):
    """Internal function to convert a byte array to a UTF-8 encoded string"""
    try:
        utf8str = str(ba, encoding='utf-8')
    except TypeError:
        utf8str = str(ba)
    return utf8str


def _find_parm(ba, parmid):
    """
    Find a specific parameter within an iAP2 parameter block provided
    as a bytearray.

    :param ba: a bytearray holding the parameter block to search
    :param parmid: the parameter ID of the parameter to find
    :return: returns a tuple of the parameter (payload) length and a
        bytearray holding the parameter payload.
    """
    pa = bytearray(ba)
    while True:
        # extract the current parameter length
        parmlen = (pa[0] << 8) + pa[1]
        # extract the current parameter ID
        pid = (pa[2] << 8) + pa[3]
        if pid == parmid:
            # parameter ID matches
            # cut off the parameter header and all trailing parameters
            # and return the length and payload
            pa = pa[4:parmlen]
            return parmlen - 4, pa
        else:
            # parameter ID did not match
            # advance to the next parameter and keep searching if not at end
            pa = pa[parmlen:]
            if not len(pa) > 0:
                return 0, None


def _find_parm_utf8(ba, parmid):
    """
    Find a specific UTF-8 string parameter within an iAP2 parameter block.

    :param ba: bytearray holding the parameter block
    :param parmid: the parameter ID to find
    :return: a tuple of the parameter length and the parameter payload
    """
    # find the parameter from the parameter block
    prmlen, parray = _find_parm(ba, parmid)
    # convert it to string and chop off the trailing terminator
    # The utf-8 string parameters always have a trailing 0
    # if there is no parameter found then return None which will
    # likely cause an exception at some point
    # TODO maybe throw an exception here
    return _ba2str(parray[:-1]) if (prmlen > 0) else None


def _find_ea_protocol_group_by_id(ba, eapid):
    """
    Find an EA protocol parameter group by EA protocol ID.
    A parameter block can contain more than one EA protocol group.  But each
    protocol group will have a unique protocol ID.  Therefore the search
    for protocol group must iterate through all EA protocol groups
    and check for a specific protocol ID.

    :param ba: input bytearray holding the parameter block to search
    :param eapid: EA protocol ID to find
    :return: a tuple of the protocol group length and the group parameters
        as a bytearray
    """
    pa = bytearray(ba)
    while True:
        # search for an EA protocol group
        grplen, grparray = _find_parm(pa, 10)
        if grplen > 0:
            # found a group - now look for the protocol identifier
            # within the group
            prmlen, prmarray = _find_parm(grparray, 0)
            if prmlen == 1 and prmarray[0] == eapid:
                # we found the correct protocol group so return it
                return grplen, grparray
            else:
                # this is a protocol group but not the right protocol id
                # so keep looking for more protocol groups
                pa = pa[grplen:]  # snip off the previous protocol group
                # this will now repeat the search for the next proto group
        else:
            # no protocol group is found - quit search
            return 0, None


def decode_parm_present(out_dict, parmid):
    """Decodes if a specific iAP2 parameter is present in the identification
    parameters, and return a yes/no boolean result."""
    ba = out_dict['iap2IdentParms']
    prmlen, prmarray = _find_parm(ba, parmid)
    return 'yes' if (prmlen > 0) else 'no'


def decode_ea_protocol_name(out_dict, eapid):
    """
    Find and return the EA protocol name specified by the EA protocol ID.

    :param out_dict: output dictionary of config data
    :param eapid: the EA protocol ID to search for a protocol name
    :return: A UTF-8 encoded string of the EA protocol name, or None
    """
    ba = out_dict['iap2IdentParms']
    grplen, grparray = _find_ea_protocol_group_by_id(ba, eapid)
    return _find_parm_utf8(grparray, 1) if (grplen > 0) else 'N/A'


def decode_ea_protocol_match(out_dict, eapid):
    """
    Find and return the EA protocol match value for the protocol specified
    by the EA protocol ID.

    :param out_dict: output dictionary of config data
    :param eapid: the EA protocol ID to search for a protocol match
    :return: the protocol match value as a string
    """
    ba = out_dict['iap2IdentParms']
    grplen, grparray = _find_ea_protocol_group_by_id(ba, eapid)
    return str(_find_parm(grparray, 2)[0]) if (grplen > 0) else str(0)


def decode_ident_parm_utf8(out_dict, parmid):
    """Extract a string parameter from the identification parameter
    block and return it as a utf-8 encoded string."""
    ba = out_dict['iap2IdentParms']
    prmlen, parray = _find_parm(ba, parmid)
    if prmlen > 0:
        parmval = _ba2str(parray[:-1])
    else:
        parmval = None
    return parmval


def decode_ident_group_parm_utf8(out_dict, group_and_parm):
    """Extract a string parameter from the identification parameter
    block, that is within a parameter group.  Return the string as
    utf-8 encoded string.  The group ID and parameter ID are provided
    as an input tuple."""
    ba = out_dict['iap2IdentParms']
    groupid, parmid = group_and_parm
    grplen, grp = _find_parm(ba, groupid)
    prmlen, parray = _find_parm(grp, parmid)
    if prmlen > 0:
        parmval = _ba2str(parray[:-1])
    else:
        parmval = None
    return parmval


def decode_ident_group_parm_n8(out_dict, group_and_parm):
    """Extract an 8-bit integer parameter from a parameter group.
    The group ID and parameter ID are provided as an input tuple."""
    ba = out_dict['iap2IdentParms']
    groupid, parmid = group_and_parm
    grplen, grp = _find_parm(ba, groupid)
    prmlen, parray = _find_parm(grp, parmid)
    if prmlen > 0:
        parmval = parray[0]
    else:
        parmval = None
    return parmval


def _decode_np_item(ba, itemid):
    """Internal function to check for presence of a now-playing item
    from a list in the input bytearray.  Returns a yes/no presence
    indicator."""
    wa = array.array('H', ba)
    if sys.byteorder == 'little':
        wa.byteswap()
    for item in wa:
        if item == itemid:
            return 'yes'
    return 'no'


def decode_np_media_item(out_dict, itemid):
    """Decode presence of now playing media item from the list
    of now-playing media items.  Returns yes/no."""
    ba = out_dict['iap2NowPlayingMediaItems']
    return _decode_np_item(ba, itemid)


def decode_np_playback_item(out_dict, itemid):
    """Decode presence of now playing playback item from the list
    of now-playing playback items.  Returns yes/no."""
    ba = out_dict['iap2NowPlayingPlaybackItems']
    return _decode_np_item(ba, itemid)


class ConfigDecoderCP2614(decoder.ConfigDecoder):
    """Device specific configuration decoder class.  Derived from the
    common configuration decoder class.  This class implements decode
    items that are specific to the CP2614."""
    def __init__(self):
        super(ConfigDecoderCP2614, self).__init__(cp2614_out_fields)


# decode field list
# (input_dict_key, decode_fn, extra_arg)
cp2614_out_fields = [
    # output key,               function,               input key (if needed)
    ('vid', decoder.decode_vid, None),
    ('pid', decoder.decode_pid, None),
    ('usb_lang', decoder.decode_x16, 'usbLanguageCode'),
    ('mfi_lang', decode_ident_parm_utf8, 12),
    ('use_custom_sn', decoder.decode_use_custom_sn, None),
    ('custom_sn', decoder.decode_custom_sn, None),
    ('mfr', decoder.decode_utf8usb, 'manufacturerStringUtf8Usb'),
    ('prod', decoder.decode_utf8usb, 'productStringUtf8Usb'),
    ('model', decode_ident_parm_utf8, 1),
    ('hw_version', decode_ident_parm_utf8, 5),
    ('cfg_is_locked', decoder.decode_config_lock, None),
    ('option_id', decoder.decode_x16, 'optionID'),
    ('debug_mode', decoder.decode_n8, 'debugMode'),
    ('audio_if', decoder.decode_audio_if, None),
    ('use_async', decoder.decode_bool_bit, ('audioOpts', 0x10)),
    # 2614 has no sample rate option
    # ('sample_rate', decoder.decode_sample_rate, None),
    ('enable_fu', decoder.decode_enable_fu, None),
    ('input_terminal', decoder.decode_input_terminal, None),
    ('output_terminal', decoder.decode_output_terminal, None),
    ('mclk_active', decoder.decode_bool_bit, ('clockingConfig', 0x20)),
    ('lrck_active', decoder.decode_bool_bit, ('clockingConfig', 0x40)),
    ('vol_default_master', decoder.decode_s8,
     'usbPlaybackFeatureUnitVolumeMasterDefaultDb'),
    ('vol_default_left', decoder.decode_s8,
     'usbPlaybackFeatureUnitVolumeLeftDefaultDb'),
    ('vol_default_right', decoder.decode_s8,
     'usbPlaybackFeatureUnitVolumeRightDefaultDb'),
    ('vol_min', decoder.decode_s8, 'usbPlaybackFeatureUnitVolumeMinDb'),
    ('vol_max', decoder.decode_s8, 'usbPlaybackFeatureUnitVolumeMaxDb'),
    ('vol_min_counts', decoder.decode_vol_counts,
     'usbPlaybackFeatureUnitVolumeMinCounts'),
    ('vol_max_counts', decoder.decode_vol_counts,
     'usbPlaybackFeatureUnitVolumeMaxCounts'),
    # TODO negative not handled correctly
    ('vol_resolution', decoder.decode_vol_resolution, None),
    ('vol_reg_size', decoder.decode_reg_size, None),
    ('vol_is_signed', decoder.decode_bool_bit, ('audioOpts', 0x02)),
    ('vol_bit_start', decoder.decode_n8, 'volumeBitStartPos'),
    ('vol_and_mask', decoder.decode_x16, 'volumeAndMask'),
    ('vol_or_mask', decoder.decode_x16, 'volumeOrMask'),
    ('mute_by_reg', decoder.decode_bool_bit, ('muteConfig', 0x01)),
    ('mute_polarity', decoder.decode_mute_polarity, None),
    ('mute_mask', decoder.decode_x16, 'muteMask'),
    ('i2c_delay', decoder.decode_n8, 'delayFromStandbyDeassertToCodecInitMs'),
    ('codec_init', decoder.decode_i2c_cmdstr, 'i2cCmdStrCodecInit'),
    ('codec_high_to_low', decoder.decode_i2c_cmdstr, 'i2cCmdStrCodecHighToLow'),
    ('codec_low_to_high', decoder.decode_i2c_cmdstr, 'i2cCmdStrCodecLowToHigh'),
    ('codec_start', decoder.decode_i2c_cmdstr, 'i2cCmdStrCodecStart'),
    ('codec_stop', decoder.decode_i2c_cmdstr, 'i2cCmdStrCodecStop'),
    ('codec_left_vol_prefix', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetVolumeLeftPrefix'),
    ('codec_left_vol_suffix', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetVolumeLeftSuffix'),
    ('codec_right_vol_prefix', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetVolumeRightPrefix'),
    ('codec_right_vol_suffix', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetVolumeRightSuffix'),
    ('codec_get_mute_prefix', decoder.decode_i2c_cmdstr,
     'i2cCmdStrGetMutePrefix'),
    ('codec_set_mute_prefix', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetMutePrefix'),
    ('codec_set_mute_suffix', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetMuteSuffix'),
    ('codec_set_rate_44', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetSampleRate44'),
    ('codec_set_rate_48', decoder.decode_i2c_cmdstr,
     'i2cCmdStrSetSampleRate48'),
    ('enable_app_launch', decoder.decode_bool_bit, ('mfiFeatureFlags', 0x40)),
    ('app_bundle_id', decoder.decode_utf8, 'appLaunchBundleID'),
    ('io_protocol_enabled', decoder.decode_bool_bit, ('mfiFeatureFlags', 0x10)),
    ('io_proto_name', decode_ea_protocol_name, 1),
    ('io_proto_match', decode_ea_protocol_match, 1),
    ('serial_protocol_enabled', decoder.decode_bool_bit, ('mfiFeatureFlags', 0x0C)),
    # could also use decode_ea_protocol_name
    ('serial_proto_name', decoder.decode_utf8usb, 'serProtocolStringUtf8Usb'),
    ('serial_proto_match', decode_ea_protocol_match, 2),
    ('enable_hid', decode_parm_present, 18),  # iAP2HIDComponent
    ('auth_chip_address', decoder.decode_x8, 'authChipAddress'),
    ('deassert_lowpwr_in_auth', decoder.decode_bool_bit,
     ('clockingConfig', 0x80)),
    ('enable_now_playing', decoder.decode_bool_bit, ('mfiFeatureFlags', 0x01)),
    ('np_mediaitem_title', decode_np_media_item, 1),
    ('np_mediaitem_duration', decode_np_media_item, 4),
    ('np_mediaitem_album_title', decode_np_media_item, 6),
    ('np_mediaitem_track', decode_np_media_item, 7),
    ('np_mediaitem_track_count', decode_np_media_item, 8),
    ('np_mediaitem_artist', decode_np_media_item, 12),
    ('np_mediaitem_genre', decode_np_media_item, 16),
    ('np_mediaitem_composer', decode_np_media_item, 18),
    ('np_mediaitem_is_liked', decode_np_media_item, 23),
    ('np_mediaitem_is_banned', decode_np_media_item, 24),
    ('np_mediaitem_chapter_count', decode_np_media_item, 27),
    ('np_pbitem_status', decode_np_playback_item, 0),
    ('np_pbitem_elapsed', decode_np_playback_item, 1),
    ('np_pbitem_queue_index', decode_np_playback_item, 2),
    ('np_pbitem_queue_count', decode_np_playback_item, 3),
    ('np_pbitem_queue_chap_index', decode_np_playback_item, 4),
    ('np_pbitem_shuffle_mode', decode_np_playback_item, 5),
    ('np_pbitem_repeat_mode', decode_np_playback_item, 6),
    ('np_pbitem_app_name', decode_np_playback_item, 7),
    ('np_pbitem_itunes_radio_ad', decode_np_playback_item, 9),
    ('np_pbitem_itunes_radio_name', decode_np_playback_item, 10),
    ('np_pbitem_speed', decode_np_playback_item, 12),
    ('np_pbitem_app_bundle', decode_np_playback_item, 16),
    ('self_powered', decoder.decode_self_powered, None),
    ('provides_power', decoder.decode_bool_bit, ('powerConfig', 0x02)),
    ('max_current_ma', decoder.decode_max_current, None),
    ('charge_when_active', decoder.decode_bool, 'deviceCanChargeActive'),
    ('active_supply', decoder.decode_n16, 'availableSupplyWhenActive'),
    ('charge_when_inactive', decoder.decode_bool, 'deviceCanChargeInactive'),
    ('inactive_supply', decoder.decode_n16, 'availableSupplyWhenInactive'),
    ('gpio_00_mode', decoder.decode_gpio_mode, 0),
    ('gpio_00_function', decoder.decode_gpio_function, 0),
    ('gpio_00_reset', decoder.decode_gpio_reset, 0),
    ('gpio_01_mode', decoder.decode_gpio_mode, 1),
    ('gpio_01_function', decoder.decode_gpio_function, 1),
    ('gpio_01_reset', decoder.decode_gpio_reset, 1),
    ('gpio_02_mode', decoder.decode_gpio_mode, 2),
    ('gpio_02_function', decoder.decode_gpio_function, 2),
    ('gpio_02_reset', decoder.decode_gpio_reset, 2),
    ('gpio_03_mode', decoder.decode_gpio_mode, 3),
    ('gpio_03_function', decoder.decode_gpio_function, 3),
    ('gpio_03_reset', decoder.decode_gpio_reset, 3),
    ('gpio_04_mode', decoder.decode_gpio_mode, 4),
    ('gpio_04_function', decoder.decode_gpio_function, 4),
    ('gpio_04_reset', decoder.decode_gpio_reset, 4),
    ('gpio_05_mode', decoder.decode_gpio_mode, 5),
    ('gpio_05_function', decoder.decode_gpio_function, 5),
    ('gpio_05_reset', decoder.decode_gpio_reset, 5),
    ('gpio_06_mode', decoder.decode_gpio_mode, 6),
    ('gpio_06_function', decoder.decode_gpio_function, 6),
    ('gpio_06_reset', decoder.decode_gpio_reset, 6),
    ('gpio_07_mode', decoder.decode_gpio_mode, 7),
    ('gpio_07_function', decoder.decode_gpio_function, 7),
    ('gpio_07_reset', decoder.decode_gpio_reset, 7),
    ('gpio_08_mode', decoder.decode_gpio_mode, 8),
    ('gpio_08_function', decoder.decode_gpio_function, 8),
    ('gpio_08_reset', decoder.decode_gpio_reset, 8),
    ('gpio_09_mode', decoder.decode_gpio_mode, 9),
    ('gpio_09_function', decoder.decode_gpio_function, 9),
    ('gpio_09_reset', decoder.decode_gpio_reset, 9),
    ('gpio_10_mode', decoder.decode_gpio_mode, 10),
    ('gpio_10_function', decoder.decode_gpio_function, 10),
    ('gpio_10_reset', decoder.decode_gpio_reset, 10),
    ('gpio_11_mode', decoder.decode_gpio_mode, 11),
    ('gpio_11_function', decoder.decode_gpio_function, 11),
    ('gpio_11_reset', decoder.decode_gpio_reset, 11),
    ('gpio_12_mode', decoder.decode_gpio_mode, 12),
    ('gpio_12_function', decoder.decode_gpio_function, 12),
    ('gpio_12_reset', decoder.decode_gpio_reset, 12),
    ('gpio_13_mode', decoder.decode_gpio_mode, 13),
    ('gpio_13_function', decoder.decode_gpio_function, 13),
    ('gpio_13_reset', decoder.decode_gpio_reset, 13),
    ('gpio_14_mode', decoder.decode_gpio_mode, 14),
    ('gpio_14_function', decoder.decode_gpio_function, 14),
    ('gpio_14_reset', decoder.decode_gpio_reset, 14),
    ('gpio_15_mode', decoder.decode_gpio_mode, 15),
    ('gpio_15_function', decoder.decode_gpio_function, 15),
    ('gpio_15_reset', decoder.decode_gpio_reset, 15),
    ('clkout_divider', decoder.decode_n8, 'clkoutDivider'),
    ('serial_rate', decoder.decode_n32, 'serialDataRate'),
    ('button_00', decoder.decode_button, 0),
    ('button_01', decoder.decode_button, 1),
    ('button_02', decoder.decode_button, 2),
    ('button_03', decoder.decode_button, 3),
    ('button_04', decoder.decode_button, 4),
    ('button_05', decoder.decode_button, 5),
    ('button_06', decoder.decode_button, 6),
    ('button_07', decoder.decode_button, 7),
    ('button_08', decoder.decode_button, 8),
    ('button_09', decoder.decode_button, 9),
    ('button_10', decoder.decode_button, 10),
    ('button_11', decoder.decode_button, 11),
    ('button_12', decoder.decode_button, 12),
    ('button_13', decoder.decode_button, 13),
    ('button_14', decoder.decode_button, 14),
]


# Test driver
if __name__ == "__main__":
    from silabs.cfgtools import encoder_2614, encoder
    import argparse
    try:
        import ConfigParser
    except ImportError:
        import configparser as ConfigParser

    desc = ("CP2614 configuration decoder.  Decodes an output dictionary "
            "into an input dictionary.  The output dictionary is generated "
            "from a test input dictionary which must be provided on command line")
    epilog = "Prints the input dictionary to stdout"
    ap = argparse.ArgumentParser(description=desc, epilog=epilog)
    ap.add_argument('--cfgfile', type=argparse.FileType(), help='test configuration file')
    args = ap.parse_args()
    if args.cfgfile is not None:
        in_config = ConfigParser.RawConfigParser(encoder_2614.ConfigEncoderCP2614.default_dict)
        in_config.optionxform = str
        in_config.readfp(fp=args.cfgfile)
        in_dict = dict(in_config.items('cp2614'))
    else:
        in_dict = encoder_2614.ConfigEncoderCP2614.default_dict
    e = encoder_2614.ConfigEncoderCP2614()
    output_dict = e.encode(in_dict)
    if args.cfgfile is not None:
        args.cfgfile.close()

    decoder = ConfigDecoderCP2614()
    new_dict = decoder.decode(output_dict)
    encoder.dump_dict(new_dict)
