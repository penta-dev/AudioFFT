# Import public API into package namespace
from decoder_2614 import ConfigDecoderCP2614
from decoder_2615 import ConfigDecoderCP2615
from encoder_2614 import ConfigEncoderCP2614, cp2614_fields
from encoder_2615 import ConfigEncoderCP2615, cp2615_fields
from packer import ConfigStructCP2614, ConfigStructCP2615

class ConfigTool(object):
    """
    Top-level class provides an interface for converting between a 
    dictionary of high-level device configuration properties and a 
    binary image of the low-level configuration data structured for 
    use by the device firmware.
    
    :param device: Part name as a string (i.e. CP2614).
    """
    def __init__(self, device):
        if '2614' in device:
            self.decoder = ConfigDecoderCP2614()
            self.encoder = ConfigEncoderCP2614()
            self.struct = ConfigStructCP2614()
        elif '2615' in device:
            self.decoder = ConfigDecoderCP2615()
            self.encoder = ConfigEncoderCP2615(device)
            self.struct = ConfigStructCP2615()
        else:
            raise ValueError('Unknown device: %s' % device)

    def to_binary(self, in_dict):
        """
        Converts device configuration properties into a binary image for 
        use by the device firmware.
        
        :param in_dict: Dictionary of high-level configuration properties.
        :return: Binary image of the device configuration.
        """
        cfg_encode = self.encoder.encode(in_dict)
        return self.struct.pack(cfg_encode)

    def from_binary(self, in_bytes):
        """
        Converts binary configuration image into a dictionary of configuration 
        properties.
        
        :param in_bytes: Binary image of the device configuration.
        :return: Dictionary of high-level configuration properties.
        """
        cfg_unpack = dict(self.struct.unpack(in_bytes))
        return self.decoder.decode(cfg_unpack)
