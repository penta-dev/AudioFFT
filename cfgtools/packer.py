#!/usr/bin/env python
#
# CP2614/CP2615 configuration packer/unpacker
#
# This module provides a set of classes that implement the packed binary
# structure of the CP2615 configuration. The classes include methods to
# transform a configuration between a dictionary of field values and the
# packed binary representation.
#

from __future__ import print_function

class UByte(object):
    def __init__(self):
        self.size = 1

    def pack_into(self, buf, offset, value):
        buf[offset] = value

    def unpack_from(self, buf, offset):
        return buf[offset]

class UShortBE(object):
    def __init__(self):
        self.size = 2

    def pack_into(self, buf, offset, value):
        buf[offset+0] = (value >> 8) & 0xFF
        buf[offset+1] = value & 0xFF

    def unpack_from(self, buf, offset):
        value = (buf[offset] << 8) + buf[offset+1]
        return value

class UIntBE(object):
    def __init__(self):
        self.size = 4

    def pack_into(self, buf, offset, value):
        buf[offset+0] = (value >> 24) & 0xFF
        buf[offset+1] = (value >> 16) & 0xFF
        buf[offset+2] = (value >>  8) & 0xFF
        buf[offset+3] = value & 0xFF

    def unpack_from(self, buf, offset):
        value = (buf[offset+0] << 24) + (buf[offset+1] << 16) + \
                (buf[offset+2] <<  8) + buf[offset+3]
        return value

class FixArray(object):
    def __init__(self, size, fill=b'\xff'):
        self.size = size
        self.fill = fill

    def pack_into(self, buf, offset, value):
        filled = value.ljust(self.size, self.fill)
        buf[offset:offset+self.size] = filled[:self.size]

    def unpack_from(self, buf, offset):
        return bytearray(buf[offset:offset+self.size])

class VarArray(object):
    def __init__(self, skip=0):
        self.skip = skip
        self.size = 4
        self._struct = UShortBE()

    def pack_into(self, buf, offset, value):
        voff = len(buf) - self.skip
        self._struct.pack_into(buf, offset+0, voff)
        self._struct.pack_into(buf, offset+2, len(value))
        buf.extend(value)

    def unpack_from(self, buf, offset):
        voff  = self._struct.unpack_from(buf, offset+0) + self.skip
        vsize = self._struct.unpack_from(buf, offset+2)
        return bytearray(buf[voff:voff+vsize])

class ConfigStruct(object):
    def __init__(self, fields):
        self.fields = fields
        self.size = sum([s.size for n, s, d in self.fields])

    def pack(self, items):
        buf = bytearray(self.size)
        offset = 0
        for name, s, default in self.fields:
            s.pack_into(buf, offset, items.get(name, default))
            offset += s.size
        return buf

    def unpack(self, buf):
        offset = 0
        for name, s, default in self.fields:
            yield name, s.unpack_from(buf, offset)
            offset += s.size

    def dump(self, buf):
        print('{')
        for name, value in self.unpack(buf):
            print("  '{}' : {},".format(name, repr(value)))
        print('}')

s_ubyte = UByte()
s_ushort = UShortBE()
s_uint = UIntBE()
s_varray = VarArray()

cp2614_fields = [
    ('cookie', FixArray(4), b'2614'),
    ('version', s_ubyte, 1),
    ('configLockKey', s_ubyte, 0xFF),
    ('serialStringUtf8Usb', FixArray(34), None),
    ('checksum', s_ushort, 0),
    ('length', s_ushort, 0),
    ('optionID', s_ushort, None),
    ('debugMode', s_ubyte, None),
    ('defaultSampleRate', s_ubyte, None),
    ('clockingConfig', s_ubyte, None),
    ('audioOpts', s_ubyte, None),
    ('volumeAndMask', s_ushort, None),
    ('volumeOrMask', s_ushort, None),
    ('volumeBitStartPos', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMasterDefaultDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeLeftDefaultDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeRightDefaultDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMinDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMinCounts', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMaxDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMaxCounts', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeResDbX256', s_ushort, None),
    ('muteConfig', s_ubyte, None),
    ('muteMask', s_ushort, None),
    ('volumeSettingForMute', s_ushort, None),
    ('mfiFeatureFlags', s_ubyte, None),
    ('authChipAddress', s_ubyte, None),
    ('appLaunchBundleID', s_varray, None),
    ('pinGpioMask', s_ushort, None),
    ('pinDirMask', s_ushort, None),
    ('pinModeMask', s_ushort, None),
    ('pinInitValue', s_ushort, None),
    ('gpioAltFunctions', FixArray(8), None),
    ('buttonsConfiguration', FixArray(16, b'\x00'), None),
    ('serialDataRate', s_uint, None),
    ('clkoutDivider', s_ubyte, None),
    ('powerConfig', s_ubyte, None),
    ('availableSupplyWhenActive', s_ushort, None),
    ('availableSupplyWhenInactive', s_ushort, None),
    ('deviceCanChargeActive', s_ubyte, None),
    ('deviceCanChargeInactive', s_ubyte, None),
    ('usbDeviceDescriptor', s_varray, None),
    ('usbConfigurationDescriptor', s_varray, None),
    ('usbLanguageCode', s_ushort, None),
    ('manufacturerStringUtf8Usb', s_varray, None),
    ('productStringUtf8Usb', s_varray, None),
    ('serProtocolStringUtf8Usb', s_varray, None),
    ('iap2IdentParms', s_varray, None),
    ('iap2NowPlayingMediaItems', s_varray, None),
    ('iap2NowPlayingPlaybackItems', s_varray, None),
    ('spareConfigElements', FixArray(16), b''),
    ('delayFromStandbyDeassertToCodecInitMs', s_ubyte, None),
    ('i2cCmdStrCodecInit', s_varray, None),
    ('i2cCmdStrCodecHighToLow', s_varray, None),
    ('i2cCmdStrCodecLowToHigh', s_varray, b'\x01\x00'),
    ('i2cCmdStrCodecStart', s_varray, None),
    ('i2cCmdStrCodecStop', s_varray, None),
    ('i2cCmdStrSetVolumeLeftPrefix', s_varray, None),
    ('i2cCmdStrSetVolumeLeftSuffix', s_varray, None),
    ('i2cCmdStrSetVolumeRightPrefix', s_varray, None),
    ('i2cCmdStrSetVolumeRightSuffix', s_varray, None),
    ('i2cCmdStrGetMutePrefix', s_varray, None),
    ('i2cCmdStrSetMutePrefix', s_varray, None),
    ('i2cCmdStrSetMuteSuffix', s_varray, None),
    ('i2cCmdStrSetSampleRate44', s_varray, None),
    ('i2cCmdStrSetSampleRate48', s_varray, None),
    ('spareI2cCmdStr', FixArray(32), b''),
    ('endVarMarker', s_varray, b'VEND'),
    ('endConfigMarker', FixArray(4), b'STOP')]

cp2615_fields = [
    ('cookie', FixArray(4), b'2614'),
    ('version', s_ubyte, 1),
    ('configLockKey', s_ubyte, 0xFF),
    ('serialStringUtf8Usb', FixArray(34), None),
    ('checksum', s_ushort, 0),
    ('length', s_ushort, 0),
    ('optionID', s_ushort, None),
    ('debugMode', s_ubyte, None),
    ('defaultSampleRate', s_ubyte, None),
    ('clockingConfig', s_ubyte, None),
    ('audioOpts', s_ubyte, None),
    ('volumeAndMask', s_ushort, None),
    ('volumeOrMask', s_ushort, None),
    ('volumeBitStartPos', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMasterDefaultDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeLeftDefaultDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeRightDefaultDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMinDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMinCounts', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMaxDb', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeMaxCounts', s_ubyte, None),
    ('usbPlaybackFeatureUnitVolumeResDbX256', s_ushort, None),
    ('muteConfig', s_ubyte, None),
    ('muteMask', s_ushort, None),
    ('volumeSettingForMute', s_ushort, None),
    ('ioOptions', s_ubyte, None),
    ('unused-1', s_ubyte, 0),
    ('unused-2', s_varray, b'N/A\x00'),
    ('pinGpioMask', s_ushort, None),
    ('pinDirMask', s_ushort, None),
    ('pinModeMask', s_ushort, None),
    ('pinInitValue', s_ushort, None),
    ('gpioAltFunctions', FixArray(8), None),
    ('buttonsConfiguration', FixArray(16, b'\x00'), None),
    ('serialDataRate', s_uint, None),
    ('clkoutDivider', s_ubyte, None),
    ('powerConfig', s_ubyte, None),
    ('unused-3', s_ushort, 0),
    ('unused-4', s_ushort, 0),
    ('unused-5', s_ubyte, 0),
    ('unused-6', s_ubyte, 0),
    ('usbDeviceDescriptor', s_varray, None),
    ('usbConfigurationDescriptor', s_varray, None),
    ('usbLanguageCode', s_ushort, None),
    ('manufacturerStringUtf8Usb', s_varray, None),
    ('productStringUtf8Usb', s_varray, None),
    ('serProtocolStringUtf8Usb', s_varray, None),
    ('unused-7', s_varray, b'\x00\x05\x00\x00\x00'),
    ('unused-8', s_varray, b'\xff\xff'),
    ('unused-9', s_varray, b'\xff\xff'),
    ('gestureDownTicks', s_ubyte, None),
    ('gestureUpTicks', s_ubyte, None),
    ('gestureButtons', FixArray(4, b'\x00'), None),
    ('spareConfigElements', FixArray(10), b''),
    ('delayFromStandbyDeassertToCodecInitMs', s_ubyte, None),
    ('i2cCmdStrCodecInit', s_varray, None),
    ('i2cCmdStrCodecHighToLow', s_varray, None),
    ('i2cCmdStrCodecLowToHigh', s_varray, b'\x01\x00'),
    ('i2cCmdStrCodecStart', s_varray, None),
    ('i2cCmdStrCodecStop', s_varray, None),
    ('i2cCmdStrSetVolumeLeftPrefix', s_varray, None),
    ('i2cCmdStrSetVolumeLeftSuffix', s_varray, None),
    ('i2cCmdStrSetVolumeRightPrefix', s_varray, None),
    ('i2cCmdStrSetVolumeRightSuffix', s_varray, None),
    ('i2cCmdStrGetMutePrefix', s_varray, None),
    ('i2cCmdStrSetMutePrefix', s_varray, None),
    ('i2cCmdStrSetMuteSuffix', s_varray, None),
    ('i2cCmdStrSetSampleRate44', s_varray, None),
    ('i2cCmdStrSetSampleRate48', s_varray, None),
    ('i2cCmdStrProfile0', s_varray, None),
    ('i2cCmdStrProfile1', s_varray, None),
    ('i2cCmdStrProfile2', s_varray, None),
    ('spareI2cCmdStr', FixArray(20), b''),
    ('endVarMarker', s_varray, b'VEND'),
    ('endConfigMarker', FixArray(4), b'STOP')]

class ConfigStructCP261x(ConfigStruct):
    def __init__(self, device):
        if '2614' in device:
            fields = cp2614_fields
        elif '2615' in device:
            fields = cp2615_fields
        else:
            raise ValueError('Unknown device: %s' % device)

        super(ConfigStructCP261x, self).__init__(fields)
        self.offsets = {}
        offset = 0
        for name, s, default in self.fields:
            self.offsets[name] = offset
            offset += s.size
            if hasattr(s, 'skip'):
                s.skip = self.size

    def checksum(self, buf):
        return sum(buf[self.offsets['length']:]) & 0xFFFF

    def length(self, buf):
        return len(buf) - self.offsets['optionID']

    def isvalid(self, buf):
        items = dict(self.unpack(buf))
        if items['cookie'] != b'2614':
            return False
        if items['checksum'] != self.checksum(buf):
            return False
        if items['length'] != self.length(buf):
            return False
        return True

    def pack(self, items):
        blob = super(ConfigStructCP261x, self).pack(items)
        items['length'] = self.length(blob)
        blob = super(ConfigStructCP261x, self).pack(items)
        items['checksum'] = self.checksum(blob)
        return super(ConfigStructCP261x, self).pack(items)

class ConfigStructCP2614(ConfigStructCP261x):
    def __init__(self):
        super(ConfigStructCP2614, self).__init__('2614')

class ConfigStructCP2615(ConfigStructCP261x):
    def __init__(self):
        super(ConfigStructCP2615, self).__init__('2615')

if __name__ == "__main__":
    from intelhex import IntelHex
    import argparse

    ap = argparse.ArgumentParser(description='CP261x config packer module.')
    ap.add_argument('cfgfile', type=argparse.FileType(), help='input config hexfile')
    ap.add_argument('-d', '--device', default='CP2615', help='device is CP2614 or CP2615')
    args = ap.parse_args()
    print(ap.description)
    print('')

    # Create structure instance for the requested device
    s_cp261x = ConfigStructCP261x(args.device)

    # Read config hexfile and unpack it
    cfg_in = IntelHex(args.cfgfile).tobinarray()
    cfg_dict = dict(s_cp261x.unpack(cfg_in))

    # Remove computed and constant fields, then repack it
    for name in ['cookie', 'checksum', 'length', 'endVarMarker', 'endConfigMarker']:
        del cfg_dict[name]
    cfg_out = s_cp261x.pack(cfg_dict)

    # Check that we got back what we started with
    if cfg_out != cfg_in:
        print("Round trip test failed!")

    # Unpack and dump the input configuration
    print('isvalid:', s_cp261x.isvalid(cfg_in))
    s_cp261x.dump(cfg_in)
