# Leap = LLSD Event API Plug-in
LEAP is a framework for launching child processes which can exchange data with the Second Life Viewer.
Originally it was used to record and playback user interface events (mouse clicks, keystrokes, etc),
it has been exposed for other purposes.

## Overview:
1. Pass an option to the SecondLifeViewer like this: `--leap "command to run custom_script"`.
2. Implement `custom_script` which reads inbound data from **stdin** and writes outbound data to **stdout**.
3. Modify SecondLifeViewer C++ to handle the events produced from the output of `custom_script`.

The language of custom_script doesn't matter: the only requirements are that
it must parse valid data from **stdin** and write valid data to **stdout**.
That said, to date only Python LEAP utilities have been written.

Note: Viewer menu options to start/stop a single Python LEAP plug-in have been added
for the Puppetry feature: `Advanced-->Puppetry-->Launch/Close plug-in`.
Although this is intended for Puppetry it could be used to start any Python LEAP plug-in.

## Details:
When the viewer launches a side process the first thing it does is send
an intro message to that process's **stdin** which looks something like this:
```
119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}
```
`199` = length of LLSD string after the colon

The message is always in LLSD notation and has `data` and `pump` keys.

`data` = contents of the message

`pump` = UUID of event pump on which this message was sent.  In this context it is the UUID of the "reply pump" dedicated to this LEAP process.
Messages sent back to this LEAP process should be aimed at the reply pump.

`data.command` = name of pump dedicated to handling commands specific to LEAP protocol.
For example: it is possible to: list available pumps, listen (or stop listening) to some existing pump, and more.

`data.features` = future-proof list of features that affect the LEAP protocol.  Currently empty.

When the LEAP process wants to send a message to the viewer it must be in a similar format and is sent by writing it out to **stdout**:
```
123:{'data': message_data, 'pump': 'name-of-destination-pump'}
```
`123:` = string length of entire LLSD notation after the colon.

`data` = LLSD formatted data

`pump` = destination pump to which the intended recipient logic is listening.

## More details:

TODO: describe LEAP's `command` API

## Frameworks:
[Python](python/README.md)

## Examples:
[helloworld.py](python/helloworld)
