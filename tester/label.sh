#!/bin/sh

# Create Dymo label printer using e.g.
#
#    sudo lpadmin -p dymo -E -v 'usb://DYMO/LabelManager%20PnP' -m lmpnp.ppd
#
# Invoke this script as e.g.
#
#    ./label.sh 70b3d5b1e000014a
#
# If Dymo label printer is not the default printer, invoke as e.g.
#
#    PRINTER=dymo ./label.sh 70b3d5b1e000014a

for eui in $* ; do
    echo $eui | \
	fold -w 8 | \
	text2pdf -w 34 -h 17 -m 0 -s 7 -o - | \
	lpr -o landscape \
	    -o MediaType=06mm \
	    -o DymoLabelAlignment=Left \
	    -o DymoContinuousPaper=1
done
