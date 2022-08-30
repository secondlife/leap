# helloworld.py = minimal example LEAP plug-in written in python

* Modify the SecondLifeViewer to listen for `helloworld` events:
* Add this code to the application initialization logic (e.g. in `LLAppViewer::init()` method):
```
    // get the pump by name
    // Note: if pump doesn't yet exist this will create it
    std::string pump_name = "helloworld";
    LLEventPump& pump = LLEventPumps::instance().obtain(pump_name);

    // add a named listener to the pump and bind a method to handle events
    std::string listener_name = "helloworld-listener";
    pump.listen(listener_name, boost::bind(&processHelloWorld, _1));
```
* Add a `processHelloWorld()` method near the top of the same file:
```
bool processHelloWorld(const LLSD& data)
{
    LL_INFOS("helloworld") << "data=" << LLSDOStreamer<LLSDNotationFormatter>(data) << LL_ENDL;
    return true;
}
```
* Build the viewer.
* Run the custom **SecondLifeViewer** application with the following option `--leap "python path/to/helloworld.py"`
* Stop the viewer to make it save its log file to the default location, and examine the logs and verify `helloworld` events were recorded there.
* * For example in a cygwin terminal:
```grep helloworld /cygdrive/c/Users/$USER/AppData/Roaming/SecondLife/logs/SecondLife.log```
