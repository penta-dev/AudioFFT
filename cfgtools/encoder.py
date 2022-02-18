#!/usr/bin/env python
#
# CP261x configuration encoder base classes
#

from __future__ import print_function
from collections import OrderedDict
from usb_descriptor import DeviceDescriptor


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
    return ' '.join('{:02x}'.format(x) for x in ba)


# The following are all functions used to encode a configuration input
# dictionary item into an output dictionary item.  The encode() functions
# all take two arguments, the input dictionary and a context-dependent
# additional parameter.  In many cases the second parameters is the
# dictionary key to use for operating on the input dictionary.
#
# The input dictionary field values are always strings and the
# output dictionary fields are usually not strings.
#
# This set of functions is general and is shared between the
# CP2614 and CP2615.  Device specific encode functions are implemented
# in separate device specific files.


def encode_object(_, obj):
    """
    Encode an object directly without transformation.
    Used for encoding constants from the fields list.
    """
    return obj


def encode_copy(d, key):
    """
    Copy the input dictionary item directly to the output
    dictionary without any transform.
    """
    return d[key]


def encode_bool(d, key):
    """Encode boolean input as numerical output"""
    b = strtobool(d[key])
    return 1 if b else 0


def encode_i2c_cmdstr(d, key):
    """
    Encode the value from the input key as an I2C command string. The input
    is a string of hex digits (2 per byte) and whitespace is ignored.
    Compute and insert a length byte at the start of the command string.
    """
    cmd_bytes = bytearray.fromhex('00 ' + d[key])
    cmd_bytes[0] = len(cmd_bytes) - 1 if len(cmd_bytes) < 256 else 254
    # the following line is test-only used when generating hex files
    # to match the old CP2614 hex files - there was no limit on
    # byte0
    # cmd_bytes[0] = (len(cmd_bytes) - 1) & 0xFF
    return cmd_bytes


def encode_i2c_profile(d, key):
    """
    Encode the value from the input key as an I2C command string. If the 
    string is empty, change the length to 0xFF.
    """
    cmd_bytes = encode_i2c_cmdstr(d, key)
    if (len(cmd_bytes) - 1) < 2:
        cmd_bytes[0] = 0xFF
    return cmd_bytes


def encode_n16(d, key):
    """
    Encode the value from the input key as a 16-bit number.  The input
    number is a string representation and preceded by 0x if hex.
    """
    val = int(d[key], base=0)
    return val & 0xFFFF


def encode_n8(d, key):
    """
    Encode the value from the input key as a 8-bit number.  The input
    number is a string representation and preceded by 0x if hex.
    """
    val = int(d[key], base=0)
    return val & 0xFF


def encode_configlock(d, _):
    """Encode the configuration lock byte"""
    if strtobool(d['cfg_is_locked']):
        config_lock_key = 0
    else:
        config_lock_key = 255
    return config_lock_key


def encode_serial_string(d, _):
    """Encode the custom serial number string"""
    use_custom_sn = strtobool(d['use_custom_sn'])
    if use_custom_sn:
        sn_array = \
            encode_utf8usb(d, 'custom_sn').ljust(34, b'\x00')
    else:
        sn_array = bytearray([0xFF] * 34)
    return sn_array


def encode_utf8(d, key):
    """Encode a UTF-8 string"""
    try:
        s = d[key].encode('utf-8')
    except UnicodeError:
        s = d[key]
    ba = bytearray(s)
    # add the null terminator
    ba.extend(b'\x00')
    return ba


def encode_utf8usb(d, key):
    """
    Encode a UTF-8/USB string.  This means that the string contents are
    UTF-8, and it is to be stored in a special format that includes a
    3 byte header so that it can also be used as a USB string.
    See the firmware config.h file for more details about this format.
    """
    try:
        s = d[key].encode('utf-8')
    except UnicodeError:
        s = d[key]
    # need number of UTF-8 characters, not number of bytes
    num_chars = len(s.decode('utf-8'))
    # create the 3 byte header
    ba = bytearray([1, (num_chars * 2) + 2, 3])
    ba.extend(bytearray(s))
    # add the null terminator
    ba.extend(b'\x00')
    return ba


def encode_clocking(d, _):
    """Encode the bits of the clocking config byte."""
    # CP2615_RCP always sets the AUTH_LOWPWR_DEASSERT flag
    bit_mask_value = 0x80
    mclk_active = strtobool(d['mclk_active'])
    lrck_active = strtobool(d['lrck_active'])
    # deassert_lowpwr is CP2614-specific, but has no effect for CP2615
    deassert_lowpwr = strtobool(d.get('deassert_lowpwr_in_auth', 'no'))
    bit_mask_value |= 0x20 if mclk_active else 0
    bit_mask_value |= 0x40 if lrck_active else 0
    bit_mask_value |= 0x80 if deassert_lowpwr else 0
    return bit_mask_value


def encode_audio_opts(d, _):
    """Encode the bits of the audio options byte"""
    vol_reg_size = int(d['vol_reg_size'])
    if vol_reg_size < 1 or vol_reg_size > 2:
        raise Exception("vol_reg_size is out of range")
    vol_is_signed = strtobool(d['vol_is_signed'])
    audio_if = int(d['audio_if'])
    audio_is_output = (audio_if == 3) or (audio_if == 4) or (
        audio_if == 5) or (audio_if == 7)
    audio_is_input = (audio_if == 1) or (audio_if == 2) or (
        audio_if == 5) or (audio_if == 6)
    use_async = strtobool(d['use_async'])
    bit_mask_value = 0
    bit_mask_value |= 0x01 if (vol_reg_size == 2) else 0
    bit_mask_value |= 0x02 if vol_is_signed else 0
    bit_mask_value |= 0x04 if audio_is_output else 0
    bit_mask_value |= 0x08 if audio_is_input else 0
    bit_mask_value |= 0x10 if use_async else 0
    return bit_mask_value


def encode_vol_resolution(d, key):
    """
    Encode the volume resolution.  The input is a floating point number
    in units of dB per bit.  This is represented in fixed point in the
    configuration as dB * 256.
    """
    res = float(d[key])
    return int(res * 256) & 0xFFFF


def encode_mute_config(d, _):
    """Encode the bits for the mute configuration byte"""
    mute_by_reg = strtobool(d['mute_by_reg'])
    mute_polarity = d['mute_polarity']
    # CP2615_RCP always sets the MUTE_REC_USING_ZERO_SAMPLE_VALUES flag
    bit_mask_value = 0x20
    bit_mask_value |= 0x01 if mute_by_reg else 0
    bit_mask_value |= 0x10 if (mute_polarity == '1') else 0
    return bit_mask_value


# For the following GPIO options.  GPIO functions are specified in
# the input dictionary with several options.
# See the input dictionary spec for each device for details on the
# input key values.


def encode_gpio_mask(d, _):
    """
    Encode the 16-bit bit mask that represents GPIO pin function.
    output bits: 1-gpio, 0-alt function
    input gpio_nn_function: 0-GPIO
    """
    gpio_mask = 0
    bit = 1
    for g in range(0, 16):
        key = "gpio_%02d_function" % g
        gpio_mode = int(d[key], base=0)
        if gpio_mode == 0:
            gpio_mask |= bit
        bit <<= 1
    return gpio_mask


def encode_dir_mask(d, _):
    """
    Encode the GPIO pin direction bit mask (16-bits)
    output bits: 1-output, 0-input
    input gpio_nn_mode: 0-input, 1/2 - output
    """
    dir_mask = 0
    bit = 1
    for g in range(0, 16):
        key = "gpio_%02d_mode" % g
        gpio_mode = int(d[key])
        if (gpio_mode == 1) or (gpio_mode == 2):
            dir_mask |= bit
        bit <<= 1
    return dir_mask


def encode_mode_mask(d, _):
    """
    Encode the GPIO pin mode bit mask
    output bits: 1-push-pull, 0-open drain
    input gpio_nn_mode: 0-input, 1-out pp, 2-out od
    """
    mode_mask = 0
    bit = 1
    for g in range(0, 16):
        key = "gpio_%02d_mode" % g
        gpio_mode = int(d[key])
        if gpio_mode == 1:  # open drain output
            mode_mask |= bit
        bit <<= 1
    return mode_mask


def encode_reset_mask(d, _):
    """Encode the GPIO pin reset value bit mask"""
    reset_mask = 0
    bit = 1
    for g in range(0, 16):
        key = "gpio_%02d_reset" % g
        gpio_reset = int(d[key])
        if gpio_reset == 1:
            reset_mask |= bit
        bit <<= 1
    return reset_mask


def encode_alt_functions(d, _):
    """
    Encode a byte array of 8 bytes, where each byte represents the
    pin alternate function selection.
    """
    alt_fn = bytearray()
    for g in range(0, 8):
        key = "gpio_%02d_function" % g
        gpio_altsel = int(d[key], base=0)
        # All non-button values are offset by 1 so that GPIO=0 in the UI.
        # All buttons have bit 7 set and are *not* offset by 1.
        # If it is not GPIO(0) and not a button, then need to adjust back to
        # values expected by firmware
        if gpio_altsel != 0 and gpio_altsel < 0x80:
            gpio_altsel -= 1

        alt_fn.append(gpio_altsel)
    return alt_fn


def encode_buttons(d, _):
    """
    Encode a byte array of 16 bytes where each byte represents the
    analog button pin function selection.
    """
    buttons_fn = bytearray(16)
    # Slot 15 is not used and must always be 0
    for b in range(0, 15):
        key = "button_%02d" % b
        buttons_fn[b] = int(d[key], base=0)
    return buttons_fn


def encode_gestures(d, _):
    """
    Encode a byte array of 4 bytes where each byte represents the
    button to associate with a gesture:
    0=Long Press, 1=Single Click, 2=Double click, 3=Triple Click.
    """
    gesture_fn = bytearray(4)
    for g in range(4):
        key = "gesture_%02d" % g
        gesture_fn[g] = int(d[key], base=0)
    return gesture_fn


def encode_serial_rate(d, _):
    """Encode serial data rate"""
    # assume it is always provided as decimal
    rate = int(d['serial_rate'])
    return rate


def encode_device_descriptor(d, _):
    """Create the USB device descriptor"""
    vid = int(d['vid'], base=0)
    pid = int(d['pid'], base=0)
    dd = DeviceDescriptor(vid, pid, max_packet=64, iMfr=1, iProd=2, iSer=3,
                          num_configs=1)
    return dd.get_bytearray()


class ConfigEncoder(object):
    """
    Class to provide an encoder for converting an input dictionary
    containing feature-centric device configuration, into an output
    dictionary containing the configuration-specific fields.
    """
    def __init__(self, fields):
        """
        Instantiate a CP261x configuration encoder.
        """
        self._fields = fields

    def encode(self, input_dict):
        """
        Perform the encoding on an input dictionary containing the
        feature-centric keys and values.

        :param input_dict: The input dictionary.
        :return: an output dictionary of key value pairs.  The output keys are
        specified in the field list that was provided when the ConfigEncoder
        was constructed.
        """
        output_dict = OrderedDict()
        for name, enc_method, key in self._fields:
            # print(name)
            output_dict[name] = enc_method(input_dict, key)

        return output_dict


def dump_dict(the_dict):
    """A simple function to print a dictionary in human readable form"""
    for name, value in the_dict.items():
        if isinstance(value, bytearray):
            print("{} = {}".format(name, ' '.join("{:02X}".format(c)
                                                  for c in value)))
        else:
            print("{} = {}".format(name, value))


def test():
    test_fields = [('cookie', encode_object, bytearray(b'2614'))]
    test_dict = {'vid': "0x10C4"}

    # can add more test fields and test dict as needed to test all
    # the encode functions

    encoder = ConfigEncoder(test_fields)
    out_dict = encoder.encode(test_dict)
    dump_dict(out_dict)

# Test driver
if __name__ == "__main__":
    test()
