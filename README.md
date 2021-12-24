# Tail
Tail - an indoor position system using UWB radio

# Description

Tail consists of tags, anchors and a server.

A tag is a battery-powered device which occasionally transmits a packet on UWB radio.

An anchor is an externally-powered device in a fixed location which acts as a bridge between UWB radio and the network on which the server resides.

The server sends and receives packets via the anchors, and is able to compute the location of each tag using multilateration.

A simpler mode of operation has also been developed whereby an anchor and a tag perform two-way communications to establish a distance between a tag and a single anchor.

# Status

Tail has been developed to a functional demo in a constrained test environment. It requires further development before it can be used in a production environment.

Unipart Digital is not currently developing this project past this stage.

# Repositories

## tail
This repository is the monorepo that was used for the duration of the development project, so contains everything related to the tags - firmware, hardware, CAD etc,
various works on the anchor software as well as a number of scripts, utilities and other bits and pieces.


## dw1000
https://github.com/unipartdigital/dw1000

This contains hardware and drivers for a DW1000 interface card for a Raspberry Pi


## utrack-tail
https://github.com/unipartdigital/utrack-tail

This repository contains the standalone anchor code required for the two-way communications mode.


## tail-server
https://github.com/unipartdigital/tail-server

This repository contains the latest attempt at developing a multilaterating server for the one way ranging mode.


## tail-anchor-hardware
https://github.com/unipartdigital/tail-anchor-hardware

This repository contains the hardware for a standalone anchor

## tail-anchor-firmware
https://github.com/unipartdigital/tail-anchor-firmware

This repository contains the (as yet barely started) firmware for a standalone anchor
