#!/usr/bin/python3

import argparse
import json
import sys
import fdt
from pihat.eeprom import EepromDevice, EepromFile


def apply(node, data):
    """Apply JSON data to devicetree node"""
    for name, value in data.items():
        if value is None:
            pass
        elif isinstance(value, dict):
            subnode = fdt.Node(name)
            node.append(subnode)
            apply(subnode, value)
        else:
            node.set_property(name, value)


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Modify Tail EEPROM")
parser.add_argument('--file', '-f', help="EEPROM file")
parser.add_argument('json', nargs='?', help="JSON file")
args = parser.parse_args()

# Read JSON data
if args.json:
    with open(args.json, 'r') as f:
        data = json.load(f)
else:
    data = json.load(sys.stdin)

# Update EEPROM
with (EepromFile(file=args.file, autosave=True) if args.file else
      EepromDevice(autosave=True)) as eeprom:

    # Locate dw1000 node
    path = eeprom.fdt.get_property('dw1000', '__symbols__').value
    node = eeprom.fdt.get_node(path)

    # Delete existing nodes or properties
    for name in data.keys():
        node.remove_subnode(name)
        node.remove_property(name)

    # Apply new properties
    apply(node, data)
