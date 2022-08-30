# Leap = LLSD Event API Plug-in
LEAP is a framework for launching child processes which can exchange data with the Second Life Viewer.
Originally it was used to automate viewer testing, for instance logging in and passing user interface events (mouse clicks, keystrokes, etc). It can also be used for, e.g., puppetry.

## Overview:
1. Pass an option to the SecondLifeViewer like this: `--leap "command to run custom_script"`.
2. Implement `custom_script` which reads inbound LLSD events from **stdin** and writes outbound LLSD events to **stdout**.
3. Modify SecondLifeViewer C++ to handle the events produced from the output of `custom_script`.

Any output on the LEAP script's **stderr** is reported in the viewer's
SecondLife.log file. This is useful, for instance, if a script crashes with an
error.

The implementation language of custom_script doesn't matter: the only
requirements are that it must parse LLSD events from **stdin** and write LLSD
events to **stdout**. That said, only Python LEAP utilities have yet been
written, and we've built some reusable Python support code.

Note: Viewer menu options to start/stop a single Python LEAP plug-in have been added
for the Puppetry feature: `Advanced→Puppetry→Launch/Close plug-in`.
Although this is intended for Puppetry it could be used to start any Python LEAP plug-in.

## Details:
When the viewer launches a LEAP plugin as a child process the first thing it does is send
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

`data.features` = future-proof list of features affecting the LEAP protocol that have been added since baseline. Currently empty: we're still using the original `length:notation-LLSD` protocol.

When the LEAP process wants to send a message to the viewer it must be in a similar format and is sent by writing it out to **stdout**:
```
123:{'data': message_data, 'pump': 'name-of-destination-pump'}
```
`123:` = string length of entire LLSD notation after the colon.

`pump` = destination pump to which the intended recipient logic is listening.

`data` = LLSD formatted data

`data` is usually an LLSD map. It usually contains a key (e.g. `op`, which is
conventional) used to dispatch to a particular operation on the `LLEventAPI`
identified by `pump`.

Moreover, for an operation expected to return a reply, conventionally you
include in the `data` map a `reply` key specifying your own `pump`: the `pump`
received in the initial message. This directs the selected operation to send
response data to the LEAP script's **stdin**.

It is the script's responsibility to associate an incoming response event with
an outstanding request event. If multiple requests are sent in quick
succession, the corresponding responses are not guaranteed to arrive in the
same order in which the requests were sent. If your `data` map includes a
`reqid` key, that `reqid` value will be echoed into the reply map.

A running viewer contains many `LLEventPump` instances. A subset of these are
actually `LLEventAPI` instances, explicitly intended to support LEAP scripts.
Sending a properly-formatted LLSD event on the script's **stdout** posts the
LLSD `data` blob to the `LLEventPump` named by the `pump` key.

## More details:

The operations supported on the LEAP `command` pump can be queried by sending
a request to that pump with `op='getAPI', api=<command>` as described below.
As noted above, setting `reply=<pump>` is also important, and it's
conventional to add `reqid=<unique>`.

With a recent viewer, the response to `'getAPI'` (formatted for readability):

    Operations relating to the LLSD Event API Plugin (LEAP) protocol:
    op == 'getAPI' (requires api):
        Get name, description, dispatch key and operations for LLEventAPI ["api"].
    op == 'getAPIs':
        Enumerate all LLEventAPI instances by name and description.
    op == 'getFeature' (requires feature):
        Return the feature value with key ["feature"]
    op == 'getFeatures':
        Return an LLSD map of feature strings (deltas from baseline LEAP protocol)
    op == 'listen' (requires listener, source):
        Listen to an existing LLEventPump named ["source"], with listener name
        ["listener"].
        By default, send events on ["source"] to the plugin, decorated
        with ["pump"]=["source"].
        If ["dest"] specified, send undecorated events on ["source"] to the
        LLEventPump named ["dest"].
        Returns ["status"] boolean indicating whether the connection was made.
    op == 'newpump' (requires name):
        Instantiate a new LLEventPump named like ["name"] and listen to it.
        ["type"] == "LLEventStream", "LLEventMailDrop" et al.
        Events sent through new LLEventPump will be decorated with ["pump"]=name.
        Returns actual name in ["name"] (may be different if collision).
    op == 'ping':
        No arguments, just a round-trip sanity check.
    op == 'stoplistening' (requires listener, source):
        Disconnect a connection previously established by "listen".
        Pass same ["source"] and ["listener"] arguments.
        Returns ["status"] boolean indicating whether such a listener existed.

## Plugins:
[puppetry](puppetry/README.md)

## Examples:
[helloworld.py](leap/examples/)
[puppetry](puppetry/examples/)
