from __init__ import ConfigTool
import binascii
tool = ConfigTool("CP2615")
in_dict = tool.encoder.default_dict
binary = tool.to_binary(in_dict)

print("Printing default CP2615 config byte-array as a string:")
print(binary)

print("\n\nPrinting array as hex:")
hexStr = binascii.b2a_hex(binary)
print(hexStr)

print("Printing C# byte array:")
print( "byte[] config = {")
i = 0;

for b in binary:
	print( "0x%.2x"% b, end = ', ')
	i += 1
	if i % 20 == 0:
		print(" ")
print( "};")
print("")
print("")
print("Printing for Xpress config:")
print( "Config {  { ")
i = 0;

for b in binary:
	print( "%.2x"% b, end = ' ')
print( "} }")