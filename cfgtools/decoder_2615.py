#!/usr/bin/env python
#
# CP2615 configuration decoder
#

from __future__ import print_function
import decoder


# the following are decoder specific functions for the CP2615.


def decode_io_enabled(out_dict, _):
    """Decodes whether IO protocol interface is enabled."""
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    desc_list = decoder.build_desc_list(cfg_desc)

    io_enabled = 'no'
    for desc in desc_list:
        # search for interface num 1 alt 2
        if desc[0] == 9 and desc[1] == 4 and desc[2] == 1 and desc[3] == 2:
            io_enabled = 'yes'
            break
    return io_enabled


class ConfigDecoderCP2615(decoder.ConfigDecoder):
    """Device specific configuration decoder class.  Derived from the
    common configuration decoder class.  This class implements decode
    items that are specific to the CP2615."""

    def __init__(self):
        super(ConfigDecoderCP2615, self).__init__(cp2615_out_fields)


# decode field list
# (input_dict_key, decode_fn, extra_arg)
cp2615_out_fields = [
    # output key,               function,               input key (if needed)
    ('vid', decoder.decode_vid, None),
    ('pid', decoder.decode_pid, None),
    ('usb_lang', decoder.decode_x16, 'usbLanguageCode'),
    ('use_custom_sn', decoder.decode_use_custom_sn, None),
    ('custom_sn', decoder.decode_custom_sn, None),
    ('mfr', decoder.decode_utf8usb, 'manufacturerStringUtf8Usb'),
    ('prod', decoder.decode_utf8usb, 'productStringUtf8Usb'),
    ('cfg_is_locked', decoder.decode_config_lock, None),
    ('option_id', decoder.decode_x16, 'optionID'),
    ('debug_mode', decoder.decode_n8, 'debugMode'),
    ('audio_if', decoder.decode_audio_if, None),
    ('use_async', decoder.decode_bool_bit, ('audioOpts', 0x10)),
    ('sample_rate', decoder.decode_sample_rate, None),
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
    ('codec_profile_0', decoder.decode_i2c_cmdstr, 'i2cCmdStrProfile0'),
    ('codec_profile_1', decoder.decode_i2c_cmdstr, 'i2cCmdStrProfile1'),
    ('codec_profile_2', decoder.decode_i2c_cmdstr, 'i2cCmdStrProfile2'),
    ('serial_protocol_enabled', decoder.decode_bool_bit, ('ioOptions', 4)),
    # ('io_protocol_enabled',     decode_bool_bit,        ('ioOptions', 0x10)),
    ('io_protocol_enabled', decode_io_enabled, None),
    ('proto_name', decoder.decode_utf8usb, 'serProtocolStringUtf8Usb'),
    ('self_powered', decoder.decode_self_powered, None),
    ('max_current_ma', decoder.decode_max_current, None),
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

    ('gesture_00', decoder.decode_gesture, 0),
    ('gesture_01', decoder.decode_gesture, 1),
    ('gesture_02', decoder.decode_gesture, 2),
    ('gesture_03', decoder.decode_gesture, 3),
]


# Test driver
if __name__ == "__main__":
    from silabs.cfgtools import encoder_2615, encoder
    import argparse
    try:
        import ConfigParser
    except ImportError:
        import configparser as ConfigParser

    descr = ("CP2615 configuration decoder.  Decodes an output dictionary "
             "into an input dictionary.  The output dictionary is generated "
             "from a test input dictionary which must be provided on command line")
    epilog = "Prints the input dictionary to stdout"
    ap = argparse.ArgumentParser(description=descr, epilog=epilog)
    ap.add_argument('--cfgfile', type=argparse.FileType(), help='test configuration file')
    args = ap.parse_args()
    if args.cfgfile is not None:
        in_config = ConfigParser.RawConfigParser(encoder_2615.ConfigEncoderCP2615.default_dict)
        in_config.optionxform = str
        in_config.readfp(fp=args.cfgfile)
        in_dict = dict(in_config.items('cp2615'))
    else:
        in_dict = encoder_2615.ConfigEncoderCP2615.default_dict
    e = encoder_2615.ConfigEncoderCP2615()
    output_dict = e.encode(in_dict)
    if args.cfgfile is not None:
        args.cfgfile.close()

    decoder = ConfigDecoderCP2615()
    new_dict = decoder.decode(output_dict)
    encoder.dump_dict(new_dict)
