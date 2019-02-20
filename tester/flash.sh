#!/bin/sh

file="$1"

if [ ! -f "${file}" ]
then
    echo "Usage: $0 filename"
    exit 1
fi

openocd -f flash.cfg -c "init; reset halt; sleep 100; flash write_image erase \"${file}\"; sleep 100; reset run; shutdown"
