# CMakeList.txt : CMake project for CppDemo, include source and define
# project specific logic here.
#
cmake_minimum_required (VERSION 3.8)

#set(VIEWER_PATH "<MYPATH>")

link_directories("${VIEWER_PATH}/build-vc150-64/packages/lib/release" "${VIEWER_PATH}/build-vc150-64/llcommon/Release" "${VIEWER_PATH}/build-vc150-64/llmessage/Release" "${VIEWER_PATH}/build-vc150-64/llcorehttp/Release" )

add_executable (${PROJECT_NAME} "CppDemo.cpp" "CppDemo.h" "puppetry.cpp" "puppetry.h")

include_directories ("${VIEWER_PATH}/indra/llcommon" "${VIEWER_PATH}/build-vc150-64/packages/include" "${VIEWER_PATH}/build-vc150-64/packages/include/apr-1") 

target_link_libraries (${PROJECT_NAME} llcommon apr-1 apriconv-1 aprutil-1 dullahan fmodL_vc fmod_vc freetype gmock gmock_main jpeglib json_libmd kdu libapr-1 libapriconv-1 libaprutil-1 libboost_chrono-mt-x64 libboost_context-mt-x64 libboost_date_time-mt-x64 libboost_fiber-mt-x64 libboost_filesystem-mt-x64 libboost_iostreams-mt-x64 libboost_program_options-mt-x64 libboost_regex-mt-x64 libboost_stacktrace_noop-mt-x64 libboost_stacktrace_windbg-mt-x64 libboost_stacktrace_windbg_cached-mt-x64 libboost_system-mt-x64 libboost_thread-mt-x64 libboost_wave-mt-x64 libcef libcef_dll_wrapper libcollada14dom23-s libcrypto libcrypto_static libcurl libexpatMT libhunspell libminizip libndofdev libpng16 libssl libssl_static libvlc libvlccore libxml2_a meshoptimizer nghttp2 nvapi ogg_static openjpeg pcre pcrecpp pcreposix uriparser vivoxsdk_x64 vorbis_static vorbisenc_static vorbisfile_static xmlrpc-epi zlib ws2_32 Wldap32 Crypt32 netapi32)
