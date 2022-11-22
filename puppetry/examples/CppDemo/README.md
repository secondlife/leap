An example of using the LEAP puppetry functionality from a C++ base.

PREREQUISITES:
    Must have locally built a copy of the viewer in another directory.

BUILDING:
    Specify the path to the viewer build as a cmake variable.
    EX:
        cmake -DVIEWER_PATH:STRING="C:/Users/YOU/viewer-release"

ALTERNATIVE BUILD:
    Open the CMake project in Visual Studio and set the VIEWER_PATH either in the cmake parameter
or directly in ./CppDemo/CMakeLists.txt
    Switch to Release 64 config if not already.
    Press F5
