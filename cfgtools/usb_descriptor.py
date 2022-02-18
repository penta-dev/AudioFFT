
from __future__ import print_function


def bytearray_to_hex_bytes(ba):
    return ' '.join('{:02x}'.format(x) for x in ba)


class DescriptorField(object):
    def __init__(self, field_name, field_decoder, field_length):
        self.fname = field_name
        self.decoder = field_decoder
        self.flen = field_length

    def decode(self, inst, ba, idx):
        decode_str = "%-20s : " % self.fname
        decode_str += self.decoder(inst, ba, idx)
        return decode_str + '\n'

    def get_len(self):
        return self.flen

    def get_name(self):
        return self.fname


class UsbDescriptor(object):
    DEVICE = int(1)
    CONFIGURATION = int(2)
    STRING = int(3)
    INTERFACE = int(4)
    ENDPOINT = int(5)
    HID = int(0x21)
    HIDREPORT = int(0x22)
    CS_INTERFACE = int(0x24)
    CS_ENDPOINT = int(0x25)
    type_names = ['unknown'] * 0x26
    type_names[0] = 'NONE'
    type_names[DEVICE] = 'DEVICE'
    type_names[CONFIGURATION] = 'CONFIGURATION'
    type_names[STRING] = 'STRING'
    type_names[INTERFACE] = 'INTERFACE'
    type_names[ENDPOINT] = 'ENDPOINT'
    type_names[HID] = 'HID'
    type_names[HIDREPORT] = 'HIDREPORT'
    type_names[CS_INTERFACE] = 'CS_INTERFACE'
    type_names[CS_ENDPOINT] = 'CS_ENDPOINT'

    def decode_b(self, ba, idx):
        # print("decode_b: idx=%d, %s\n" % (idx, str(ba)))
        return "%d" % ba[idx]

    def decode_xb(self, ba, idx):
        return "0x%02X" % ba[idx]

    def decode_w(self, ba, idx):
        return "%d" % (ba[idx] + (ba[idx+1] << 8))

    def decode_xw(self, ba, idx):
        return "0x%04X" % (ba[idx] + (ba[idx+1] << 8))

    def decode_type(self, ba, idx):
        desc_type = ba[idx]
        if desc_type < len(UsbDescriptor.type_names):
            return "%d (%s)" % (desc_type, UsbDescriptor.type_names[desc_type])
        else:
            return "%d (unknown)" % desc_type

    def decode_bcd(self, ba, idx):
        decode_str = "0x%04X" % (ba[idx] + (ba[idx+1] << 8))
        decode_str += " (%d.%d)" % (ba[idx+1], ba[idx])
        return decode_str

    fields = [DescriptorField('bLength', decode_b, 1),
              DescriptorField('bDescriptorType', decode_type, 1)]

    def __init__(self, type, length):
        self.fields = list(UsbDescriptor.fields)
        self.type = type
        self.length = length
        self.children = []
        self.desc_array = bytearray(2)
        self.desc_array[0] = self.length
        self.desc_array[1] = self.type
        self.comment = ""

    def add_child(self, child_desc):
        self.children.append(child_desc)

    def set_comment(self, comment_str):
        self.comment = comment_str

    def get_bytearray(self):
        outbytes = bytearray()
        outbytes.extend(self.desc_array)
        for child in self.children:
            outbytes.extend(child.get_bytearray())
        return outbytes

    def get_length(self):
        total_len = len(self.desc_array)
        for child in self.children:
            total_len += child.get_length()
        return total_len

    def __repr__(self, lev=0):
        repstr = ' ' * (lev * 2)
        repstr += ' '.join('{:02x}'.format(x) for x in self.desc_array)
        repstr += '\n'
        if len(self.children) != 0:
            # repstr += '\n{\n'
            for child in self.children:
                repstr += child.__repr__(lev=lev+1)
            # repstr += '\n}\n'
        return repstr

    def __str__(self, lev=0):
        repstr = ' ' * (lev * 2) + '{\n'
        if len(self.comment) > 0:
            repstr += '  ' + ' ' * (lev * 2)
            repstr += "%-20s : \"%s\"\n" % ('comment', self.comment)
        bindex = 0
        for field in self.fields:
            repstr += '  ' + ' ' * (lev * 2)
            repstr += field.decode(self, self.desc_array, bindex)
            bindex += field.get_len()
#            if bindex >= len(self.desc_array):
#                break
        if len(self.children) != 0:
            for child in self.children:
                repstr += child.__str__(lev=lev+1)
        repstr += ' ' * (lev * 2) + '}\n'
        return repstr

    def get_c(self):
        cstr = ''
        if len(self.comment) > 0:
            cstr += "    // %-20s : \"%s\"\n" % ('comment', self.comment)
        bindex = 0
        for field in self.fields:
            cstr += '    // '
            cstr += field.decode(self, self.desc_array, bindex)
            bindex += field.get_len()
        cstr += '    ' + ','.join('{:02x}'.format(x) for x in self.desc_array)
        cstr += ',\n\n'
        if len(self.children) > 0:
            for child in self.children:
                cstr += child.get_c()
        return cstr


class DeviceDescriptor(UsbDescriptor):

    fields = UsbDescriptor.fields \
           + [DescriptorField('bcdUsb', UsbDescriptor.decode_bcd, 2),
              DescriptorField('bDeviceClass', UsbDescriptor.decode_xb, 1),
              DescriptorField('bDeviceSubClass', UsbDescriptor.decode_xb, 1),
              DescriptorField('bDeviceProtocol', UsbDescriptor.decode_xb, 1),
              DescriptorField('bMaxPacketSize0', UsbDescriptor.decode_b, 1),
              DescriptorField('idVendor', UsbDescriptor.decode_xw, 2),
              DescriptorField('idProduct', UsbDescriptor.decode_xw, 2),
              DescriptorField('bcdDevice', UsbDescriptor.decode_bcd, 2),
              DescriptorField('iManufacturer', UsbDescriptor.decode_b, 1),
              DescriptorField('iProduct', UsbDescriptor.decode_b, 1),
              DescriptorField('iSerialNumber', UsbDescriptor.decode_b, 1),
              DescriptorField('bNumConfigurations', UsbDescriptor.decode_b, 1)]

    def __init__(self, vid, pid, usb_ver=0x0200, dev_class=0, dev_subclass=0,
                 dev_proto=0, max_packet=64, dev_ver=0x0100,
                 iMfr=0, iProd=0, iSer=0, num_configs=1):
        super(DeviceDescriptor, self).__init__(UsbDescriptor.DEVICE, 18)
        self.fields = list(DeviceDescriptor.fields)
        self.vid = vid
        self.pid = pid
        self.desc_array.extend([usb_ver & 0xFF, usb_ver >> 8,
                               dev_class, dev_subclass,
                               dev_proto, max_packet])
        self.desc_array.extend([self.vid & 0xFF, self.vid >> 8])
        self.desc_array.extend([self.pid & 0xFF, self.pid >> 8])
        self.desc_array.extend([dev_ver & 0xFF, dev_ver >> 8])
        self.desc_array.extend([iMfr, iProd, iSer, num_configs])


class ConfigurationDescriptor(UsbDescriptor):

    def decode_power(self, ba, idx):
        power = ba[idx] * 2
        return "%d (%d mA)" % (ba[idx], power)

    def decode_attributes(self, ba, idx):
        attrs = ba[idx]
        decode_str = "0x%02X (" % attrs
        decode_str += "self-powered=%s" % ('yes' if (attrs & 0x40) else 'no')
        decode_str += ", remote-wake=%s" % ('yes' if (attrs & 0x20) else 'no')
        decode_str += ")"
        return decode_str

    fields = UsbDescriptor.fields \
           + [DescriptorField('wTotalLength', UsbDescriptor.decode_w, 2),
              DescriptorField('bNumInterfaces', UsbDescriptor.decode_b, 1),
              DescriptorField('bConfigurationValue', UsbDescriptor.decode_b, 1),
              DescriptorField('iConfiguration', UsbDescriptor.decode_b, 1),
              DescriptorField('bmAttributes', decode_attributes, 1),
              DescriptorField('bMaxPower', decode_power, 1)]

    def __init__(self, num_interfaces=1, config_value=1, iConf=0,
                 self_powered=True, max_power=100):
        super(ConfigurationDescriptor, self).__init__(UsbDescriptor.CONFIGURATION, 9)
        self.fields = list(ConfigurationDescriptor.fields)
        self.desc_array.extend([0, 0])  # wTotalLength, computed later
        self.desc_array.extend([num_interfaces, config_value, iConf])
        attrs = 0xC0 if self_powered else 0x80
        self.desc_array.append(attrs)
        self.desc_array.append(max_power // 2)
        self.compute_total_length()

    def compute_total_length(self):
        total_length = self.get_length()
        self.desc_array[2] = total_length & 0xFF
        self.desc_array[3] = total_length >> 8

    def add_child(self, child_desc):
        super(ConfigurationDescriptor, self).add_child(child_desc)
        self.compute_total_length()


class InterfaceDescriptor(UsbDescriptor):

    CLASS_AUDIO = 1
    CLASS_HID = 3
    SUBCLASS_AUDIOCONTROL = 1
    SUBCLASS_AUDIOSTREAMING = 2

    class_names = ["NONE", "AUDIO", "?", "HID"]
    subclass_names = ["NONE", "AUDIOCONTROL", "AUDIOSTREAMING"]

    def decode_class(self, ba, idx):
        cls_id = ba[idx]
        if cls_id < len(InterfaceDescriptor.class_names):
            return "%d (%s)" % (cls_id, InterfaceDescriptor.class_names[cls_id])
        else:
            return "%d (unknown)" % cls_id

    def decode_subclass(self, ba, idx):
        cls_id = ba[idx]
        if cls_id < len(InterfaceDescriptor.subclass_names):
            return "%d (%s)" % (cls_id, InterfaceDescriptor.subclass_names[cls_id])
        else:
            return "%d (unknown)" % cls_id

    fields = UsbDescriptor.fields \
           + [DescriptorField('bInterfaceNumber', UsbDescriptor.decode_b, 1),
              DescriptorField('bAlternateSetting', UsbDescriptor.decode_b, 1),
              DescriptorField('bNumEndpoints', UsbDescriptor.decode_b, 1),
              DescriptorField('bInterfaceClass', decode_class, 1),
              DescriptorField('bInterfaceSubClass', decode_subclass, 1),
              DescriptorField('bInterfaceProtocol', UsbDescriptor.decode_xb, 1),
              DescriptorField('iInterface', UsbDescriptor.decode_b, 1)]

    def __init__(self, if_num, alt=0, num_eps=0, if_class=0, if_subclass=0,
                 if_protocol=0, iIface=0):
        super(InterfaceDescriptor, self).__init__(UsbDescriptor.INTERFACE, 9)
        self.fields = list(InterfaceDescriptor.fields)
        self.desc_array.extend([if_num, alt, num_eps, if_class, if_subclass,
                                if_protocol, iIface])


class ClassSpecificAudioDescriptor(UsbDescriptor):
    HEADER = 0x01
    INPUT_TERMINAL = 0x02
    OUTPUT_TERMINAL = 0x03
    MIXER_UNIT = 0x04
    SELECTOR_UNIT = 0x05
    FEATURE_UNIT = 0x06
    PROCESSING_UNIT = 0x07
    EXTENSION_UNIT = 0x08
    AS_GENERAL = 0x01  # overloaded with HEADER
    FORMAT_TYPE = 0x02  # overloaded with INPUT_TERMINAL
    # TODO figure out how to separate overloaded subtype definitions

    subtype_names = ['NONE', 'HEADER', 'INPUT_TERMINAL', 'OUTPUT_TERMINAL', 'MIXER_UNIT',
                     'SELECTOR_UNIT', 'FEATURE_UNIT', 'PROCESSING_UNIT',
                     'EXTENSION_UNIT']

    def decode_subtype(self, ba, idx):
        subtype = ba[idx]
        if subtype < len(ClassSpecificAudioDescriptor.subtype_names):
            return "%d (%s)" % (subtype, ClassSpecificAudioDescriptor.subtype_names[subtype])
        else:
            return "%d (unknown)" % subtype

    fields = UsbDescriptor.fields \
           + [DescriptorField('bDescriptorSubtype', decode_subtype, 1)]

    def __init__(self, subtype, length):
        super(ClassSpecificAudioDescriptor, self).__init__(UsbDescriptor.CS_INTERFACE, length)
        self.fields = list(ClassSpecificAudioDescriptor.fields)
        self.desc_array.append(subtype)


class AudioControlHeader(ClassSpecificAudioDescriptor):

    fields = ClassSpecificAudioDescriptor.fields \
           + [DescriptorField('bcdADC', UsbDescriptor.decode_bcd, 2),
              DescriptorField('wTotalLength', UsbDescriptor.decode_w, 2),
              DescriptorField('bInCollection', UsbDescriptor.decode_b, 1)]

    def __init__(self, ver=0x0100, if_collection=[]):
        num_in_collection = len(if_collection)
        bLen = 8 + num_in_collection
        super(AudioControlHeader, self).__init__(ClassSpecificAudioDescriptor.HEADER, bLen)
        self.fields = list(AudioControlHeader.fields)
        self.desc_array.extend([ver & 0xFF, ver >> 8])
        self.desc_array.extend([0, 0])  # dummy wTotalLength
        self.desc_array.append(num_in_collection)
        ifidx = 0
        for iface in if_collection:
            self.fields += [DescriptorField("baInterfaceNr%d" % ifidx, UsbDescriptor.decode_b, 1)]
            self.desc_array.append(iface)
            ifidx += 1

    def compute_total_length(self):
        total_length = self.get_length()
        self.desc_array[5] = total_length & 0xFF
        self.desc_array[6] = total_length >> 8

    def add_child(self, child_desc):
        super(AudioControlHeader, self).add_child(child_desc)
        self.compute_total_length()


class TerminalDescriptor(ClassSpecificAudioDescriptor):

    TYPE_USB_STREAMING = 0x0101
    TYPE_MICROPHONE = 0x0201
    TYPE_SPEAKER = 0x0301
    TYPE_HEADPHONES = 0x0302
    TYPE_LINE = 0x0603

    type_names = {0x0101: 'USB_STREAMING', 0x0201: 'MICROPHONE',
                  0x0301: 'SPEAKER', 0x0302: 'HEADPHONES', 0x0603: 'LINE'}

    def decode_termtype(self, ba, idx):
        termtype = ba[idx] + (ba[idx+1] << 8)
        tt_name = TerminalDescriptor.type_names[termtype]
        return "0x%04X (%s)" % (termtype, tt_name)

    fields = ClassSpecificAudioDescriptor.fields \
           + [DescriptorField('bTerminalID', UsbDescriptor.decode_b, 1),
              DescriptorField('wTerminalType', decode_termtype, 2),
              DescriptorField('bAssocTerminal', UsbDescriptor.decode_b, 1)]

    def __init__(self, term_is_input, term_id, term_type, assoc_term=0):
        length = 12 if term_is_input else 9
        subtype = ClassSpecificAudioDescriptor.INPUT_TERMINAL if term_is_input\
            else ClassSpecificAudioDescriptor.OUTPUT_TERMINAL
        super(TerminalDescriptor, self).__init__(subtype, length)
        self.fields = list(ClassSpecificAudioDescriptor.fields)
        self.desc_array.append(term_id)
        self.desc_array.extend([term_type & 0xFF, term_type >> 8])
        self.desc_array.append(assoc_term)


class InputTerminal(TerminalDescriptor):

    def decode_config(self, ba, idx):
        chan_config = ba[idx] + (ba[idx+1] << 8)
        chan_text = ""
        chan_text += 'left-front, ' if (chan_config & 1) else ''
        chan_text += 'right-front, ' if (chan_config & 2) else ''
        return "0x%04X (%s)" % (chan_config, chan_text)

    fields = TerminalDescriptor.fields \
           + [DescriptorField('bNrChannels', UsbDescriptor.decode_b, 1),
              DescriptorField('wChannelConfig', decode_config, 2),
              DescriptorField('iChannelNames', UsbDescriptor.decode_b, 1),
              DescriptorField('iTerminal', UsbDescriptor.decode_b, 1)]

    def __init__(self, term_id, term_type, assoc_term=0, num_channels=2, chan_config=3, iChan=0, iTerm=0):
        super(InputTerminal, self).__init__(True, term_id, term_type, assoc_term)
        self.fields = list(InputTerminal.fields)
        self.desc_array.append(num_channels)
        self.desc_array.extend([chan_config & 0xFF, chan_config >> 8])
        self.desc_array.extend([iChan, iTerm])


class OutputTerminal(TerminalDescriptor):

    fields = TerminalDescriptor.fields \
           + [DescriptorField('bSourceID', UsbDescriptor.decode_b, 1),
              DescriptorField('iTerminal', UsbDescriptor.decode_b, 1)]

    def __init__(self, term_id, term_type, source_id, assoc_term=0, iTerm=0):
        super(OutputTerminal, self).__init__(False, term_id, term_type, assoc_term)
        self.fields = list(OutputTerminal.fields)
        self.desc_array.extend([source_id, iTerm])


class FeatureUnit(ClassSpecificAudioDescriptor):
    # TODO add bit settings and decoder for controls
    fields = ClassSpecificAudioDescriptor.fields \
           + [DescriptorField('bUnitID', UsbDescriptor.decode_b, 1),
              DescriptorField('bSourceID', UsbDescriptor.decode_b, 1),
              DescriptorField('bControlSize', UsbDescriptor.decode_b, 1)]

    def __init__(self, unit_id, source_id, control_size, controls=[], iFeature=0):
        length = 7 + (len(controls) * control_size)
        super(FeatureUnit, self).__init__(ClassSpecificAudioDescriptor.FEATURE_UNIT, length)
        self.desc_array.extend([unit_id, source_id, control_size])
        # assumes control size is 1 or 2
        ctrl_decoder = UsbDescriptor.decode_xb if (control_size == 1) else UsbDescriptor.decode_xw
        newfields = list(FeatureUnit.fields)
        idx = 0
        for control in controls:
            newfields += [DescriptorField("bmaControls%d" % idx, ctrl_decoder, control_size)]
            if control_size == 1:
                self.desc_array.append(control)
            elif control_size == 2:
                self.desc_array.extend([control & 0xFF, control >> 8])
            idx += 1
        newfields += [DescriptorField('iFeature', UsbDescriptor.decode_b, 1)]
        self.desc_array.append(iFeature)
        self.fields = newfields


class AudioStreamingInterface(ClassSpecificAudioDescriptor):

    FORMAT_PCM = 1

    # override super's subtype decoder since the subtype numeric
    # value is overloaded
    def decode_subtype(self, ba, idx):
        subtype = ba[idx]
        if subtype == ClassSpecificAudioDescriptor.AS_GENERAL:
            return "%d (AS_GENERAL)" % subtype
        else:
            return "%d (unknown)" % subtype

    def decode_format_tag(self, ba, idx):
        fmt = ba[idx] + (ba[idx+1] << 8)
        decode_str = "0x%04X" % fmt
        decode_str += ' (PCM)' if (fmt == AudioStreamingInterface.FORMAT_PCM) else ' (unknown)'
        return decode_str

    fields = ClassSpecificAudioDescriptor.fields \
           + [DescriptorField('bTerminalLink', UsbDescriptor.decode_b, 1),
              DescriptorField('bDelay', UsbDescriptor.decode_b, 1),
              DescriptorField('wFormatTag', decode_format_tag, 2)]

    def __init__(self, terminal_link, format, delay=0):
        super(AudioStreamingInterface, self).__init__(ClassSpecificAudioDescriptor.AS_GENERAL, 7)
        newfields = list(AudioStreamingInterface.fields)
        # replace the subtype decoder
        newfields[2] = DescriptorField('bDescriptorSubtype', AudioStreamingInterface.decode_subtype, 1)
        self.fields = newfields
        self.desc_array.extend([terminal_link, delay])
        self.desc_array.extend([format & 0xFF, format >> 8])


class AudioFormatTypeIDescriptor(ClassSpecificAudioDescriptor):

    FORMAT_TYPE_I = 1

    # override super's subtype decoder since the subtype numeric
    # value is overloaded
    def decode_subtype(self, ba, idx):
        subtype = ba[idx]
        if subtype == ClassSpecificAudioDescriptor.FORMAT_TYPE:
            return "%d (FORMAT_TYPE)" % subtype
        else:
            return "%d (unknown)" % subtype

    def decode_format_type(self, ba, idx):
        fmt = ba[idx]
        decode_str = "0x%02X" % fmt
        decode_str += ' (FORMAT_TYPE_I)' if (fmt == AudioFormatTypeIDescriptor.FORMAT_TYPE_I) else ' (unknown)'
        return decode_str

    def decode_freq(self, ba, idx):
        freq = ba[idx] + (ba[idx+1] << 8) + (ba[idx+2] << 16)
        decode_str = "0x%02X, 0x%02X, 0x%02X" % (ba[idx], ba[idx+1], ba[idx+2])
        decode_str += " (%d)" % freq
        return decode_str

    fields = ClassSpecificAudioDescriptor.fields \
           + [DescriptorField('bFormatType', decode_format_type, 1),
              DescriptorField('bNrChannels', UsbDescriptor.decode_b, 1),
              DescriptorField('bSubframeSize', UsbDescriptor.decode_b, 1),
              DescriptorField('bBitResolution', UsbDescriptor.decode_b, 1),
              DescriptorField('bSamFreqType', UsbDescriptor.decode_b, 1)]

    def __init__(self, channels, subframe_size, bit_resolution, sample_freqs=[]):
        length = 8 + (len(sample_freqs) * 3)
        super(AudioFormatTypeIDescriptor, self).__init__(ClassSpecificAudioDescriptor.FORMAT_TYPE, length)
        self.desc_array.append(AudioFormatTypeIDescriptor.FORMAT_TYPE_I)
        self.desc_array.extend([channels, subframe_size, bit_resolution])
        self.desc_array.append(len(sample_freqs))
        newfields = list(AudioFormatTypeIDescriptor.fields)
        # replace the subtype decoder
        newfields[2] = DescriptorField('bDescriptorSubtype', AudioFormatTypeIDescriptor.decode_subtype, 1)
        idx = 1
        for freq in sample_freqs:
            newfields += [DescriptorField("tSamFreq%d" % idx, AudioFormatTypeIDescriptor.decode_freq, 3)]
            self.desc_array.extend([freq & 0xFF, (freq >> 8) & 0xFF, freq >> 16])
        self.fields = newfields


class EndpointDescriptor(UsbDescriptor):
    DIR_INPUT = 0x80
    DIR_OUTPUT = 0
    XFER_CONTROL = 0
    XFER_ISOC = 1
    XFER_BULK = 2
    XFER_INTERRUPT = 3
    SYNC_NONE = 0
    SYNC_ASYNC = 4
    SYNC_ADAPTIVE = 8
    SYNC_SYNC = 0x0C
    USAGE_DATA = 0
    USAGE_FEEDBACK = 0x10
    USAGE_IMPLICIT = 0x20

    xfer_type = ['control', 'iso', 'bulk', 'interrupt']
    sync_type = ['none', 'async', 'adaptive', 'sync']
    usage_type = ['data', 'feedback', 'implicit', 'reserved']

    def decode_ep(self, ba, idx):
        ep = ba[idx]
        decode_str = "0x%02X" % ep
        decode_str += " (addr=%d, dir=%s)" % (ep & 0x0F, 'in' if (ep & 0x80) else 'out')
        return decode_str

    def decode_attributes(self, ba, idx):
        attrs = ba[idx]
        decode_str = "0x%02X" % attrs
        decode_str += " (xfer=%s, " % EndpointDescriptor.xfer_type[attrs & 0x03]
        decode_str += "sync=%s, " % EndpointDescriptor.sync_type[(attrs >> 2) & 0x03]
        decode_str += "usage=%s)" % EndpointDescriptor.usage_type[(attrs >> 4) & 0x03]
        return decode_str

    fields = UsbDescriptor.fields \
           + [DescriptorField('bEndpointAddress', decode_ep, 1),
              DescriptorField('bmAttributes', decode_attributes, 1),
              DescriptorField('wMaxPacketSize', UsbDescriptor.decode_w, 2),
              DescriptorField('bInterval', UsbDescriptor.decode_b, 1)]

    def __init__(self, ep_address, direction, max_packet,
                 xfer_type=XFER_CONTROL, sync_type=SYNC_NONE,
                 usage_type=USAGE_DATA, interval=0):
        super(EndpointDescriptor, self).__init__(UsbDescriptor.ENDPOINT, 7)
        self.fields = list(EndpointDescriptor.fields)
        self.desc_array.append(ep_address | direction)  # bEndpointAddress
        self.desc_array.append(xfer_type | sync_type | usage_type)  # bmAttributes
        self.desc_array.extend([max_packet & 0xFF, max_packet >> 8])
        self.desc_array.append(interval)


class AudioEndpointDescriptor(EndpointDescriptor):

    fields = EndpointDescriptor.fields \
           + [DescriptorField('bRefresh', UsbDescriptor.decode_b, 1),
              DescriptorField('bSynchAddress', UsbDescriptor.decode_xb, 1)]

    def __init__(self, ep_address, direction, max_packet,
                 xfer_type=EndpointDescriptor.XFER_CONTROL,
                 sync_type=EndpointDescriptor.SYNC_NONE,
                 usage_type=EndpointDescriptor.USAGE_DATA,
                 interval=0, refresh=0, sync_addr=0):
        super(AudioEndpointDescriptor, self).__init__(ep_address, direction,
                                                      max_packet, xfer_type,
                                                      sync_type, usage_type,
                                                      interval)
        self.fields = list(AudioEndpointDescriptor.fields)
        self.desc_array.extend([refresh, sync_addr])
        # super sets length to 7, but this descriptor is length 9
        # need to override
        self.desc_array[0] = 9


class ClassSpecificAudioEndpoint(UsbDescriptor):

    EP_GENERAL = 1

    def decode_subtype(self, ba, idx):
        subtype = ba[idx]
        decode_str = "0x%02X" % subtype
        decode_str += " (%s)" % 'EP_GENERAL' if (subtype == ClassSpecificAudioEndpoint.EP_GENERAL) else 'unknown'
        return decode_str

    def decode_attributes(self, ba, idx):
        attrs = ba[idx]
        decode_str = "0x%02X (" % attrs
        decode_str += 'freq, ' if (attrs & 1) else ''
        decode_str += 'pitch, ' if (attrs & 2) else ''
        decode_str += 'max_packets' if (attrs & 0x80) else ''
        decode_str += ')'
        return decode_str

    def decode_lock_units(self, ba, idx):
        units = ba[idx]
        decode_str = "0x%02X" % units
        decode_str += " (%s)" % ('milliseconds' if (units ==1) else 'unknown')
        return decode_str

    fields = UsbDescriptor.fields \
           + [DescriptorField('bDescriptorSubtype', decode_subtype, 1),
              DescriptorField('bmAttributes', decode_attributes, 1),
              DescriptorField('bLockDelayUnits', decode_lock_units, 1),
              DescriptorField('wLockDelay', UsbDescriptor.decode_w, 1)]

    def __init__(self, attributes=1, lock_units=0, lock_delay=0):
        super(ClassSpecificAudioEndpoint, self).__init__(UsbDescriptor.CS_ENDPOINT, 7)
        self.fields = list(ClassSpecificAudioEndpoint.fields)
        self.desc_array.append(ClassSpecificAudioEndpoint.EP_GENERAL)
        self.desc_array.append(attributes)
        self.desc_array.append(lock_units)
        self.desc_array.extend([lock_delay & 0xFF, lock_delay >> 8])


class HidDescriptor(UsbDescriptor):

    fields = UsbDescriptor.fields \
           + [DescriptorField('bcdHID', UsbDescriptor.decode_bcd, 2),
              DescriptorField('bCountryCode', UsbDescriptor.decode_b, 1),
              DescriptorField('bNumDescriptors', UsbDescriptor.decode_b, 1)]

    def __init__(self, ver=0x0111, country_code=0, desc_list=[]):
        length = 6 + (len(desc_list) * 3)
        super(HidDescriptor, self).__init__(UsbDescriptor.HID, length)
        self.desc_array.extend([ver & 0xFF, ver >> 8])
        self.desc_array.extend([country_code, len(desc_list)])
        newfields = list(HidDescriptor.fields)
        for desc in desc_list:
            newfields += [DescriptorField('bDescriptorType', UsbDescriptor.decode_type, 1)]
            newfields += [DescriptorField('wDescriptorLength', UsbDescriptor.decode_w, 2)]
            self.desc_array.append(desc[0])
            self.desc_array.extend([desc[1] & 0xFF, desc[1] >> 8])
            self.fields = newfields


class AudioStreamingSubtree(InterfaceDescriptor):
    """
    Convenience class that can be used to build an interface descriptor
    subtree containing all the sub-descriptors for an audio
    streaming interface

    Make some assumptions - there are always 2 channels and format is
    PCM.  One isoc endpoint.  None of the descriptors in the tree have
    associated strings.

    Lock delay is assumed to be ms.  If zero then units and value are set
    to 0.  If non-zero, then units is set to ms.
    """
    def __init__(self, if_num, alt, terminal_link, subframe_size, ep_addr, ep_dir,
                 max_packet, sync_type, rates=[], format_delay=0, interval=0,
                 explicit_feedback=0, implicit_feedback=0, lock_delay=0):
        # if explicit feedback is requested, then need to create second endpoint
        num_eps = 1 if (explicit_feedback == 0) else 2

        # create the top level interface descriptor
        super(AudioStreamingSubtree, self).__init__(if_num, alt=alt, num_eps=num_eps,
                                                    if_class=InterfaceDescriptor.CLASS_AUDIO,
                                                    if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
        # audio streaming descriptor
        asif = AudioStreamingInterface(terminal_link,
                                       AudioStreamingInterface.FORMAT_PCM,
                                       delay=format_delay)
        asif.set_comment('Audio streaming descriptor')

        # audio format descriptor
        fmt = AudioFormatTypeIDescriptor(2, subframe_size, subframe_size*8,
                                         sample_freqs=rates)
        fmt.set_comment('Audio streaming format descriptor')

        # feedback logic
        # --------------
        # There are multiple axes: streaming EP can be input or output,
        # and feedback can be explicit, implicit or none.  Caller should not
        # choose both implicit and explicit in the input parameters.
        #
        # OUTPUT
        #
        # implicit feedback - sync address should be set to the implicit
        # feedback address (addr | 0x80)
        # This assumes there is an input stream used for implicit feedback
        #
        # explicit feedback - sync address must be set to the explicit
        # feedback address AND feedback endpoint must be created
        # This assumes there is not also an input stream because this
        # setting would not make any sense
        #
        # none - sync address remains 0
        #
        # INPUT
        #
        # implicit feedback - endpoint attributes need to have implicit feedback
        # bit set IFF there is also an output stream - up to caller.
        # So if this is input and implicit feedback is requested we assume
        # this means implicit bit must be set.
        #
        # explicit feedback - this choice does not make sense for an
        # input stream
        #
        # none - no effect on input stream
        #

        # if output and feedback requested, set up sync ep address
        sync_addr = 0
        if ep_dir == EndpointDescriptor.DIR_OUTPUT:
            if explicit_feedback != 0:
                sync_addr = explicit_feedback | EndpointDescriptor.DIR_INPUT

            # previously I had the following logic, setting the sync_address
            # to be the implicit feedback endpoint if there was one.  However
            # the old RCP app only sets sync address in the case of explicit
            # feedback endpoint, so I changed the logic here to match.
            #
#            elif implicit_feedback != 0:
#                sync_addr = implicit_feedback | EndpointDescriptor.DIR_INPUT

        # if input and implicit feedback, then need to set implicit
        # ep usage
        usage = EndpointDescriptor.USAGE_DATA
        if ep_dir == EndpointDescriptor.DIR_INPUT and implicit_feedback != 0:
            usage = EndpointDescriptor.USAGE_IMPLICIT

        # audio endpoint descriptor
        ep = AudioEndpointDescriptor(ep_addr, ep_dir, max_packet,
                                     xfer_type=EndpointDescriptor.XFER_ISOC,
                                     sync_type=sync_type,
                                     usage_type=usage,
                                     interval=interval,
                                     sync_addr=sync_addr)
        ep.set_comment('Audio streaming endpoint')

        # class specific audio endpoint
        lock_units = 1 if (lock_delay != 0) else 0
        csep = ClassSpecificAudioEndpoint(lock_units=lock_units,
                                          lock_delay=lock_delay)

        # build the subtree
        asif.add_child(fmt)
        self.add_child(asif)
        ep.add_child(csep)
        self.add_child(ep)

        # if non-zero feedback address is provided, it means there is a
        # feedback endpoint
        if explicit_feedback != 0:
            fbep = AudioEndpointDescriptor(explicit_feedback,
                                           EndpointDescriptor.DIR_INPUT, 3,
                                           xfer_type=EndpointDescriptor.XFER_ISOC,
                                           sync_type=EndpointDescriptor.SYNC_NONE,
                                           usage_type=EndpointDescriptor.USAGE_FEEDBACK,
                                           refresh=6, interval=1)
            self.add_child(fbep)


if __name__ == "__main__":


    # test stuff

    # device descriptor
    device = DeviceDescriptor(0x10C4, 0xEAC1, max_packet=64, iMfr=1, iProd=2,
                              iSer=3, num_configs=1)
    device.set_comment('Device Descriptor')

    # configuration descriptor.  child descriptors will be added below
    config = ConfigurationDescriptor(num_interfaces=5, config_value=1,
                                     self_powered=False, max_power=100, iConf=4)
    config.set_comment('Configuration Descriptor')

    # interface descriptor for HID
    hid_if = InterfaceDescriptor(0, alt=0, num_eps=1,
                                 if_class=InterfaceDescriptor.CLASS_HID,
                                 if_subclass=0, if_protocol=0)
    hid_if.set_comment('HID Interface')

    # HID descriptor, to be added to HID interface
    hid = HidDescriptor(desc_list=[(UsbDescriptor.HIDREPORT, 39)])
    hid.set_comment('HID Descriptor Declaration')

    # endpoint for HID interface
    hid_ep = EndpointDescriptor(1, EndpointDescriptor.DIR_INPUT, 2,
                                xfer_type=EndpointDescriptor.XFER_INTERRUPT,
                                interval=20)
    hid_ep.set_comment("HID Endpoint")

    # add the hid descriptor and endpoint to the hid interface,
    # then add the interface to the configuration
    hid_if.add_child(hid)
    hid_if.add_child(hid_ep)
    config.add_child(hid_if)

    # interface for bulk io protocol.  Alts 0, 1 and 2
    iop_if0 = InterfaceDescriptor(1, alt=0, num_eps=0, if_class=0xFF, if_subclass=0x15, if_protocol=1)
    iop_if0.set_comment('IOP Bulk Interface Alt 0')

    # alt 1
    iop_if1 = InterfaceDescriptor(1, alt=1, num_eps=2, if_class=0xFF, if_subclass=0x15, if_protocol=1)
    iop_if1.set_comment('IOP Bulk Interface Alt 1')
    iop1_ep_in = EndpointDescriptor(2, EndpointDescriptor.DIR_INPUT, max_packet=64,
                                    xfer_type=EndpointDescriptor.XFER_BULK)
    iop1_ep_out = EndpointDescriptor(2, EndpointDescriptor.DIR_OUTPUT, max_packet=64,
                                     xfer_type=EndpointDescriptor.XFER_BULK)
    # add the endpoints to the alt1 if
    iop_if1.add_child(iop1_ep_in)
    iop_if1.add_child(iop1_ep_out)

    # alt 2
    iop_if2 = InterfaceDescriptor(1, alt=2, num_eps=2, if_class=0xFF, if_subclass=0x15, if_protocol=1)
    iop_if2.set_comment('IOP Bulk Interface Alt 2')
    iop2_ep_in = EndpointDescriptor(2, EndpointDescriptor.DIR_INPUT, max_packet=64,
                                    xfer_type=EndpointDescriptor.XFER_BULK)
    iop2_ep_out = EndpointDescriptor(2, EndpointDescriptor.DIR_OUTPUT, max_packet=64,
                                     xfer_type=EndpointDescriptor.XFER_BULK)
    # add the endpoints to the alt2 if
    iop_if2.add_child(iop2_ep_in)
    iop_if2.add_child(iop2_ep_out)

    # add the IOP interfaces to the configuration
    config.add_child(iop_if0)
    config.add_child(iop_if1)
    config.add_child(iop_if2)

    # audio control
    ac_if = InterfaceDescriptor(2, alt=0, num_eps=0,
                                if_class=InterfaceDescriptor.CLASS_AUDIO,
                                if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOCONTROL)
    ac_if.set_comment('Audio control interface')

    # audio control header, terminals and feature units
    ac_hdr = AudioControlHeader(if_collection=[3, 4])
    ac_hdr.set_comment('Audio Control Header')

    # headphone audio topology
    hp_it = InputTerminal(1, TerminalDescriptor.TYPE_USB_STREAMING, num_channels=2, chan_config=3)
    hp_it.set_comment('Headphones Input Terminal')
    hp_ot = OutputTerminal(2, TerminalDescriptor.TYPE_HEADPHONES, 3)
    hp_ot.set_comment('Headphones Output Terminal')
    hp_fu = FeatureUnit(3, 1, 2, controls=[1, 2, 2])
    hp_fu.set_comment('Headphones Feature Unit')

    ac_hdr.add_child(hp_it)
    ac_hdr.add_child(hp_ot)
    ac_hdr.add_child(hp_fu)

    # microphone audio topology
    mic_it = InputTerminal(4, TerminalDescriptor.TYPE_LINE, num_channels=2, chan_config=3)
    mic_it.set_comment('Line Input Terminal')
    mic_ot = OutputTerminal(5, TerminalDescriptor.TYPE_USB_STREAMING, 6)
    mic_ot.set_comment('Line Output Terminal')
    mic_fu = FeatureUnit(6, 4, 2, controls=[1, 0, 0])
    mic_fu.set_comment('Line Feature Unit')

    ac_hdr.add_child(mic_it)
    ac_hdr.add_child(mic_ot)
    ac_hdr.add_child(mic_fu)

    # add audio control header to the audio control interface
    ac_if.add_child(ac_hdr)

    # audio OUT streaming interfaces
    out_alt0 = InterfaceDescriptor(3, alt=0, num_eps=0,
                                   if_class=InterfaceDescriptor.CLASS_AUDIO,
                                   if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
    out_alt0.set_comment("Streaming OUT, alt 0")
    out_alt1 = InterfaceDescriptor(3, alt=1, num_eps=1,
                                   if_class=InterfaceDescriptor.CLASS_AUDIO,
                                   if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
    out_alt1.set_comment("Streaming OUT, alt 1")
    out_asif = AudioStreamingInterface(1, AudioStreamingInterface.FORMAT_PCM, 2)
    out_asif.set_comment('Audio streaming interface')
    out_format = AudioFormatTypeIDescriptor(2, 2, 16, [48000])
    out_format.set_comment('Streaming out format')

    out_ep = AudioEndpointDescriptor(3, EndpointDescriptor.DIR_OUTPUT, 200,
                                     xfer_type=EndpointDescriptor.XFER_ISOC,
                                     sync_type=EndpointDescriptor.SYNC_SYNC,
                                     usage_type=EndpointDescriptor.USAGE_DATA,
                                     interval=1, refresh=0, sync_addr=0)
    out_ep.set_comment('Audio OUT endpoint')
    out_audio_ep = ClassSpecificAudioEndpoint()
    out_audio_ep.set_comment('Class specific audio OUT endpoint')

    out_alt1.add_child(out_asif)
    out_alt1.add_child(out_format)
    out_alt1.add_child(out_ep)
    out_alt1.add_child(out_audio_ep)

    ac_if.add_child(out_alt0)
    ac_if.add_child(out_alt1)

    # audio IN streaming interfaces
    in_alt0 = InterfaceDescriptor(4, alt=0, num_eps=0,
                                  if_class=InterfaceDescriptor.CLASS_AUDIO,
                                  if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
    in_alt0.set_comment("Streaming IN, alt 0")
    in_alt1 = InterfaceDescriptor(4, alt=1, num_eps=1,
                                  if_class=InterfaceDescriptor.CLASS_AUDIO,
                                  if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOSTREAMING)
    in_alt1.set_comment("Streaming IN, alt 1")
    in_asif = AudioStreamingInterface(5, AudioStreamingInterface.FORMAT_PCM, 2)
    in_asif.set_comment('Audio streaming interface')
    in_format = AudioFormatTypeIDescriptor(2, 2, 16, [48000])
    in_format.set_comment('Streaming IN format')

    in_ep = AudioEndpointDescriptor(3, EndpointDescriptor.DIR_INPUT, 200,
                                    xfer_type=EndpointDescriptor.XFER_ISOC,
                                    sync_type=EndpointDescriptor.SYNC_SYNC,
                                    usage_type=EndpointDescriptor.USAGE_DATA,
                                    interval=1, refresh=0, sync_addr=0)
    in_ep.set_comment('Audio IN endpoint')
    in_audio_ep = ClassSpecificAudioEndpoint()
    in_audio_ep.set_comment('Class specific audio IN endpoint')

    in_alt1.add_child(in_asif)
    in_alt1.add_child(in_format)
    in_alt1.add_child(in_ep)
    in_alt1.add_child(in_audio_ep)

    ac_if.add_child(in_alt0)
    ac_if.add_child(in_alt1)



    # add the audio control interface to the configuration descriptor
    config.add_child(ac_if)

    print(repr(config))
    print(config)

    print(config.get_c())

    # acif = InterfaceDescriptor(1, alt=0, num_eps=0,
    #                           if_class=InterfaceDescriptor.CLASS_AUDIO,
    #                           if_subclass=InterfaceDescriptor.SUBCLASS_AUDIOCONTROL,
    #                           if_protocol=0, iIface=0)
    #csac = CsAcInterfaceHeader(ver=0x0100, if_collection=[2,3])
    #interm = InputTerminal(1, TerminalDescriptor.TYPE_USB_STREAMING)
    #outterm = OutputTerminal(2, TerminalDescriptor.TYPE_HEADPHONES, 3)
    #fuout = FeatureUnit(3, 1, 2, controls=[0x0001, 0x0002, 0x0002])

    #csac.add_child(interm)
    #csac.add_child(outterm)
    #csac.add_child(fuout)
    #acif.add_child(csac)
    #cd.add_child(acif)





















