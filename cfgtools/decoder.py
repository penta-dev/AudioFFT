#!/usr/bin/env python
#
# CP2615 configuration decoder
#

from __future__ import print_function
from collections import OrderedDict


def strtobool(val):
    """
    Return a boolean representing the text input value
    """
    return val.lower() in ('y', 'yes', 't', 'true', 'on', '1')


def bytearray_to_hex_bytes(ba):
    """
    Return a string of space-delimited hex bytes, representing the
    input bytearray
    """
    return ' '.join('{:02X}'.format(x) for x in ba)


# The following set of "decode_" functions are used to decode fields
# from the "output" dictionary into the the form of the "input" dictionary.
# There is a common function signature:
#
# decode_blah(out_dict, key_or_something_else)
#
# The first parameter will always be the output dictionary and most of
# the decode functions will use it although its not required.  The second
# parameter is usually an output dictionary key and the function then is
# a transform that converts the output field into an input field.  Except
# that often it is more complicated than that.  So the second parameter
# may be something else or not used at all.
#
# The input dictionary values are always strings, so all of these functions
# ultimately return a string representation of their transformed value.
#
# This set of functions is general and shared between the CP2614 and CP2615.
# Device specific decode functions are implemented in the device specific
# decoder file.


def decode_object(_, obj):
    """Return the same thing that was passed in.  This is useful
    when the transform is a constant."""
    return obj


def decode_x16(out_dict, key):
    """Return string of the form 0x1234 representing 16-bit integer"""
    val = int(out_dict[key])
    return "0x%04X" % val


def decode_n16(out_dict, key):
    """Return 16-bit integer as its string value."""
    val = int(out_dict[key])
    return str(val)


def decode_n8(out_dict, key):
    """Return an 8-bit integer as its string value."""
    return decode_n16(out_dict, key)


def decode_x8(out_dict, key):
    """Return a string of the form 0x12 representing an 8-bit integer"""
    val = int(out_dict[key])
    return "0x%02X" % val


def decode_n32(out_dict, key):
    """Return a 32-bit integer as its string value."""
    return decode_n16(out_dict, key)


def decode_s8(out_dict, key):
    """Return a signed 8-bit integer as its string value"""
    # need to treat 8 bit number as signed
    val = int(out_dict[key])
    val &= 0xFF
    if val & 0x80:
        val -= 256
    return str(val)


def decode_bool(out_dict, key):
    """Decode an integer as a boolean"""
    val = int(out_dict[key])
    return 'yes' if (val != 0) else 'no'


def decode_vid(out_dict, _):
    """Extract the USB vendor ID (VID) from the device descriptor and
    return as 16-bit hex string (0x1234)"""
    config_desc = bytearray(out_dict['usbDeviceDescriptor'])
    vid = config_desc[8] + (config_desc[9] << 8)
    return "0x%04X" % vid


def decode_pid(out_dict, _):
    """Extract the USB productr ID (PID) from the device descriptor and
    return as 16-bit hex string (0x1234)"""
    config_desc = bytearray(out_dict['usbDeviceDescriptor'])
    pid = config_desc[10] + (config_desc[11] << 8)
    return "0x%04X" % pid


def decode_use_custom_sn(out_dict, _):
    """Return boolean string to indicate if custom serial number
    is used.  It is determined by whether the first byte of the
    serial number is blank."""
    custom_sn = bytearray(out_dict['serialStringUtf8Usb'])
    return 'no' if (custom_sn[0] == 0xFF) else 'yes'


def decode_utf8usb(out_dict, key):
    """
    Decode a byte array that contains a UTF8/USB encoded string.
    This is a string that has a 3 byte header and is utf-8 encoded.
    It should also have a null terminator.  It removes the header and
    the null terminary and returns the string.
    """
    ba = bytearray(out_dict[key])
    try:
        utf8str = str(ba[3:-1], encoding='utf-8')
    except TypeError:
        utf8str = str(ba[3:-1])
    return utf8str


def decode_utf8(out_dict, key):
    """Decode a bytearray that contains a UTF-8 string.  It removes
    the null terminator and returns the resulting string"""
    ba = bytearray(out_dict[key])
    try:
        utf8str = str(ba[:-1], encoding='utf-8')
    except TypeError:
        utf8str = str(ba[:-1])
    return utf8str


def decode_custom_sn(out_dict, _):
    """Decodes the custom serial number into a string, if it is
    present.  If it is not present then it returns a generic string.
    All trailing zeroes are strippped off."""
    custom_sn = bytearray(out_dict['serialStringUtf8Usb'])
    sn_present = custom_sn[0]
    if sn_present == 0xFF:
        sn_str = 'N/A: using internal SN'
    else:
        sn_str = decode_utf8usb(out_dict, 'serialStringUtf8Usb')
    return sn_str.rstrip('\0')


def decode_config_lock(out_dict, _):
    """Decodes the meaning of the lock byte to indicate if the
    configuration is locked or not."""
    lock = int(out_dict['configLockKey'])
    return 'yes' if (lock == 0) else 'no'


def build_desc_list(all_desc):
    """Function to build a list of USB descriptors given
    a bytearray blob containing all the USB descriptors"""
    desc_list = []
    while len(all_desc) != 0:
        desc_len = all_desc[0]
        new_desc = all_desc[:desc_len]
        all_desc = all_desc[desc_len:]
        desc_list += [new_desc]
    return desc_list


def _build_ep_list(desc_list):
    """
    Internal function to extract a list of audio streaming endpoints
    from an input list of USB descriptors.  It builds a new list of tuples
    with one entry per endpoint.  The tuple for each endpoint is:
    (interface number, interface alt value, endpoint address, EP sync mode)
    """
    ep_list = []  # ifnum, alt, addr, sync
    if_num = 0
    if_alt = 0
    for desc in desc_list:
        # find audiostreaming interface
        if ((desc[0] == 9) and  # len 9
            (desc[1] == 4) and  # type interface
            (desc[5] == 1) and  # class audio
            (desc[6] == 2)):    # subclass audio streaming

            if_num = desc[2]  # save interface number
            if_alt = desc[3]  # save alt number

        elif (desc[0] == 9) and (desc[1] == 5):  # type endpoint
            ep_addr = desc[2]
            ep_sync = desc[3] & 0x0C
            new_ep = [(if_num, if_alt, ep_addr, ep_sync)]
            ep_list += new_ep

    return ep_list


def _get_matching_eps(ep_list, alt, addr):
    """Given a list of endpoints (from _build_ep_list()), returns
    a subset list containing the endpoints that match the specified
    alt and EP address values."""
    match_list = []
    for ep in ep_list:
        if ep[1] == alt and ep[2] == addr:
            match_list.append(ep)
    return match_list


def decode_audio_if(out_dict, _):
    """
    Heuristic to determine the audio_if value:

    - if audio control interface no present, then no audio --> 0
    - audio control interface:
        - len 9, type 4, if num 2, class 1, subclass 1

    Remaining configs can be determined by looking at number of endpoints
    and ep addresses after the audio control interface.

    - endpoint:
        - len 9 type 5, ep address idx 2

    This table shows the number of audio endpoints for each kind of
    audio_if IN/OUT configuration and sync mode.  The entries in the
    table show all of the EP alt nums/epaddr for the given config.

    config      | sync            | async
    ------------|-----------------|------
    1 (16in)    | 1/83            | 1/83
    2 (24/16in) | 1/83 2/83       | 1/83 2/83
    3 (16out)   | 1/03            | 1/03 1/83 (if3)
    4 (24/16out)| 1/03 2/03       | 1/03 2/03 1/83 2/82
    5 (16in/out)| 1/03(3) 1/83(4) | 1/03(3) 1/83(4)
    6 (24in)    | 2/83            | 2/83
    7 (24out)   | 2/03            | 2/03 2/82
    """

    # get the configuration descriptor and extract a list of all
    # the audio streaming endpoints
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    desc_list = build_desc_list(cfg_desc)
    ep_list = _build_ep_list(desc_list)

    # make some ep lists with various alt and ep addresses
    ep103 = _get_matching_eps(ep_list, 1, 0x03)
    ep183 = _get_matching_eps(ep_list, 1, 0x83)
    ep203 = _get_matching_eps(ep_list, 2, 0x03)
    ep283 = _get_matching_eps(ep_list, 2, 0x83)
    ep282 = _get_matching_eps(ep_list, 2, 0x82)

    audio_if = 0
    # if there are no endpoints, then there is no audio streaming
    if len(ep_list) == 0:
        audio_if = 0

    # the remaining elifs below test the endpoint configuration
    # required for each audio_if IN/OUT configuration
    # for example, for this one: if there is only 1 endpoint in the
    # list, and it is alt 1 with ep address 0x83, then we know this
    # means it is audio_if 1.  Similar logic is followed below for
    # each case.
    elif len(ep_list) == 1 and len(ep183) == 1:
        audio_if = 1

    elif len(ep_list) == 2 and len(ep183) == 1 and len(ep283) == 1:
        audio_if = 2

    elif ((len(ep_list) == 1 and len(ep103) == 1) or
          (len(ep_list) == 2) and len(ep183) == 1 and ep183[0][0] == 3):
        audio_if = 3

    elif ((len(ep_list) == 2 or len(ep_list) == 4) and
          len(ep103) == 1 and len(ep203)):
        audio_if = 4

    elif (len(ep_list) == 2 and len(ep103) == 1 and len(ep183) == 1 and
          len(ep103) == 1 and ep103[0][0] == 3 and len(ep183) == 1 and
          ep183[0][0] == 4):
        audio_if = 5

    elif len(ep_list) == 1 and len(ep283) == 1:
        audio_if = 6

    elif ((len(ep_list) == 1 and len(ep203) == 1) or
          (len(ep_list) == 2 and len(ep203) == 1 and len(ep282) == 1)):
        audio_if = 7

    return str(audio_if)


def decode_sample_rate(out_dict, _):
    """Determines the supported samples rates by examining some audio
    descriptors.  Returns the enumeration value for the sample rate of
    0, 1, or 2."""
    # build the list of USB descriptors
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    desc_list = build_desc_list(cfg_desc)

    # search for an audio format descriptor
    sample_rate = 0
    for desc in desc_list:
        if (desc[0] == 11 and desc[1] == 36 and desc[2] == 2 and desc[3] == 1
                and desc[7] == 1):
            # found audio format descriptor that contains one sample rate
            # so figure out if that one sample rate is 44 or 48
            freq0 = desc[8]
            if freq0 == 0x80:
                sample_rate = 0
            else:
                sample_rate = 1
            break
        if (desc[0] == 14 and desc[1] == 36 and desc[2] == 2 and desc[3] == 1
                and desc[7] == 2):
            # found an audio format descriptor that contains two sample
            # rates so that must mean we support 44 and 48
            sample_rate = 2
            break

    return str(sample_rate)


def decode_enable_fu(out_dict, _):
    """Returns boolean indication if the feature unit is present.
    Examples the USB configuration descriptor for a feature unit
    descriptor."""
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    desc_list = build_desc_list(cfg_desc)

    enable_fu = 'no'

    # search for a feature unit descriptor
    for desc in desc_list:
        if desc[0] == 13 and desc[1] == 36 and desc[2] == 6:
            enable_fu = 'yes'
            break
    return enable_fu


def decode_output_terminal(out_dict, _):
    """Decodes the output terminal type (headphones, speaker, etc)
    by examining the output terminal descriptor.  It returns a
    string representation of the enumeration value of the terminal type"""
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    desc_list = build_desc_list(cfg_desc)

    out_term_val = 0  # headphones is default

    # search for output terminal
    for desc in desc_list:
        if desc[0] == 9 and desc[1] == 36 and desc[2] == 3 and desc[3] == 2:
            out_term_type = desc[4] + (desc[5] << 8)
            if out_term_type == 0x0302:  # headphones
                out_term_val = 0
            elif out_term_type == 0x0301:  # speaker
                out_term_val = 1
            elif out_term_type == 0x0603:  # line
                out_term_val = 2
            break
    return str(out_term_val)


def decode_input_terminal(out_dict, _):
    """Decodes the input terminal type (linbe, microphone, etc)
    by examining the input terminal descriptor.  It returns a
    string representation of the enumeration value of the terminal type"""
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    desc_list = build_desc_list(cfg_desc)

    in_term_val = 0  # line input is default

    # search for input terminal
    for desc in desc_list:
        if desc[0] == 12 and desc[1] == 36 and desc[2] == 2 and desc[3] == 4:
            in_term_type = desc[4] + (desc[5] << 8)
            if in_term_type == 0x0603:  # line
                in_term_val = 0
            elif in_term_type == 0x0201:  # microphone
                in_term_val = 1
            break
    return str(in_term_val)


def decode_bool_bit(out_dict, key_tuple):
    """Decodes a bit in a byte as a boolean value (yes/no).
    The second parameter must be a tuple of (key, bit mask),
    where key is the dictionary key of the byte field and the
    bitmask is the bit mask of the bit in the bit field."""
    val = int(out_dict[key_tuple[0]])
    return 'yes' if val & key_tuple[1] else 'no'


def decode_vol_resolution(out_dict, _):
    """Decodes the volume resolution.  The volume resolution is
    a fixed point integer in the output dictionary but a floating
    point number (as a string) in the input dictionary.  This function
    transforms the fixed point value to floating point."""
    resint = int(out_dict['usbPlaybackFeatureUnitVolumeResDbX256'])
    resf = float(resint) / float(256)
    return str(resf)


def decode_vol_counts(out_dict, key):
    """
    Volume counts are 8 bit and are signed or unsigned depending on
    the value of bit 0x02 of audioOpts
    """
    is_signed = strtobool(decode_bool_bit(out_dict, ('audioOpts', 2)))
    val = int(out_dict[key]) & 0xFF
    if is_signed and (val & 0x80):
        val -= 256
    return str(val)


def decode_reg_size(out_dict, _):
    """Decode the codec register size (1 or 2 bytes)"""
    audio_opts = int(out_dict['audioOpts'])
    reg_size = 2 if audio_opts & 0x01 else 1
    return str(reg_size)


def decode_mute_polarity(out_dict, _):
    """Decode the mute polarity value (1 or 0) from a bit in
    the muteConfig byte"""
    val = int(out_dict['muteConfig'])
    mute_polarity = 1 if val & 0x10 else 0
    return str(mute_polarity)


def decode_i2c_cmdstr(out_dict, key):
    """Decode an I2C command string contained in a bytearray into a
    string of hex bytes"""
    cmd_bytes = bytearray(out_dict[key])
    cmd_bytes = cmd_bytes[1:]  # remove leading length byte
    return bytearray_to_hex_bytes(cmd_bytes)


def decode_self_powered(out_dict, _):
    """Decodes whether the device is self powered by examining
    the attributes of the configuration descriptor"""
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    attrs = cfg_desc[7]
    return 'yes' if attrs & 0x40 else 'no'


def decode_max_current(out_dict, _):
    """Decodes the max current by reading it from the USB
    configuration descriptor."""
    cfg_desc = bytearray(out_dict['usbConfigurationDescriptor'])
    max_power = cfg_desc[8]
    max_power *= 2
    return str(max_power)


def decode_gpio_mode(out_dict, num):
    """Decodes the GPIO mode enumeration by reading the
    GPIO direction and mode mask.  The input parameter num is the
    GPIO pin number."""
    dir_mask = int(out_dict['pinDirMask'])
    mode_mask = int(out_dict['pinModeMask'])

    bit_mask = 1 << num
    if (dir_mask & bit_mask) == 0:  # input
        mode = 0
    elif mode_mask & bit_mask:  # output and pp
        mode = 1
    else:
        mode = 2                # output and od
    return str(mode)


def decode_gpio_function(out_dict, num):
    """Decodes the alt function value for the specified GPIO pin (num).
    The returned value is a string representation of the enumeration.
    It is 0 if the function is GPIO, otherwise it is the alt function
    value."""
    gpio_mask = int(out_dict['pinGpioMask'])
    alt_fn = bytearray(out_dict['gpioAltFunctions'])
    bit_mask = 1 << num

    if gpio_mask & bit_mask:    # gpio selected?
        fn = 0
    elif num > 7:               # not gpio, for 8-15
        fn = 1
    else:                       # not gpio, 0-7
        fn = alt_fn[num]        # read function value from alt fn array
        if fn < 0x80:           # if not a button
            fn += 1             # adjust for GPIO selection value in GUI (0)
    return "0x%02X" % fn


def decode_gpio_reset(out_dict, num):
    """Decodes the GPIO reset value for a GPIO pin specified by num"""
    init_mask = int(out_dict['pinInitValue'])
    bit_mask = 1 << num
    return '1' if init_mask & bit_mask else '0'


def decode_button(out_dict, num):
    """Decodes the button function for the specified button num"""
    button_cfg = bytearray(out_dict['buttonsConfiguration'])
    return "0x%02X" % button_cfg[num]


def decode_gesture(out_dict, num):
    """Decodes the button function for the specified gesture num"""
    gesture_cfg = bytearray(out_dict['gestureButtons'])
    return "0x%02X" % gesture_cfg[num]


class ConfigDecoder(object):
    """A configuration decoder class, used for decoding the output
    dictionary for CP2614 or CP2615 configuration blobs.  The device is
    determined by the field list passed to the constructor.  This is
    meant to be subclassed to a device-specific decoder.

    Here is some additional explanation about input vs output dictionary.
    The CP261x encoder/decoder process has the concept of input dictionary
    and output dictionary.  The input dictionary is the input to the
    encode process.  It most closely matches all the configurator
    UI elements and choices.  The Encoder will transform the input
    dictionary into an output dictionary.  The output dictionary
    matches the fields of the CP261x configuration blob.

    Therefore, the Decoder is transforming the output dictionary back
    into the input dictionary.  This should be kept in mind as the
    input and output terms refer to which dictionary it is, and not
    whether it is the input or output of the decoder (the output
    dictionary is the input to the decoder).
    """
    def __init__(self, fields):
        """
        Create a new ConfigDecoder.  The field decode list must be
        provided.  The field decode list is a list of tuples of the form
        of (key, decoder function, decode parameter)
        where the key is the "input" dictionary key that we are decoding
        to - ie the target of the decode transformation;
        decoder function is the decode function that will perform the
        transform;
        decode parameter is an extra parameter that will be passed to
        the decode function.  It is often a dictionary key but may be
        another value depending on the decode function.
        :param fields:
        """
        self.fields = fields

    def decode(self, out_dict):
        """
        Decode an output dictionary into an input dictionary.
        :param out_dict: a device output dictionary to convert
        :return: the converted input dictionary
        """
        in_dict = OrderedDict()
        for name, decoder, key in self.fields:
            in_dict[name] = decoder(out_dict, key)

        return in_dict


def dump_dict(the_dict):
    """A simple function to print a dictionary in human readable form"""
    for name, value in the_dict.items():
        if isinstance(value, bytearray):
            print("{} = {}".format(name, ' '.join(
                "{:02X}".format(c) for c in value)))
        else:
            print("{} = {}".format(name, value))


def test():
    test_fields = [('usb_lang', decode_x16, 'usbLanguageCode')]
    test_dict = {'usbLanguageCode': 0x0409}

    decoder = ConfigDecoder(test_fields)
    output_dict = decoder.decode(test_dict)
    dump_dict(output_dict)

# Test driver
if __name__ == "__main__":
    test()
