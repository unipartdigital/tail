#!/bin/sh

uploadcmd=u
filename=
device=/dev/ttyUSB0

usage()
{
    echo "Usage: $0 [-h] [--destructive] [--tty device] filename"
    echo
    echo "Connect the tag up and then run this command to flash"
    echo "new firmware. Make sure to use a binary file - this"
    echo "command will not translate .hex files for you."
    echo
    echo "If the firmware is working and this is a normal upgrade,"
    echo "the transfer will start within a few seconds. If the"
    echo "transfer does not start within a few seconds, switch the"
    echo "tag off and on again."
    echo
    echo "If the transfer still doesn't start, switch the tag off"
    echo "for a day or two and try again, this time only switching"
    echo "it on after starting this script."
}

while [ "$1" != "" ]
do
    case "$1" in
        -h | --help)
            usage
            exit
            ;;
        --destructive)
            uploadcmd=d
            ;;
        --tty)
            shift
            device="$1"
            if [ "X$device" = "X" ]
            then
                usage
                exit 1
            fi
            ;;
        *)
            if [ "X$filename" != "X" ]
            then
                usage
                exit 1
            fi
            filename="$1"
            ;;
    esac
    shift
done

if [ "X$filename" = "X" ]
then
    usage
    exit 1
fi

if [ ! -f "$filename" ]
then
    echo "File $filename does not exist"
fi

(
  stty 9600 cs8 -cstopb -parenb -echo clocal raw
  # If we're in the firmware, this should speed things along a bit
  printf '\3\3'
  sleep 1
  printf 'reset\r\n'
  (
    while :
    do
      printf '\3'
      sleep 0.5
    done
  ) &
  
  child=$!
  
  trap 'kill -TERM $child; exit' TERM INT
  
  echo "Waiting for connection to upload $filename" >&2
  
  while read line
  do
      case "$line" in
          *ChipID:*)
              kill $!
              trap - TERM INT
              echo "$line" >&2
              break
              ;;
          *)
              ;;
      esac
  done
  
  echo "Starting upload" >&2
  
  # Start upload
  printf "$uploadcmd"
  
  while read line
  do
      case "$line" in
          Ready*)
              break
              ;;
          *)
              ;;
      esac
  done

  echo "Invoking sx" >&2

  # Perform upload
  sx -b "$filename"
  
  # Reboot
  echo -n "r"
) <"$device" >"$device"

