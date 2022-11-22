
#ifndef PUPPETRY_H
#define PUPPETRY_H

#ifndef WIN32
#define WIN32  //Everything in llapr.h breaks without this defined.
#endif

#include <iostream>
#include <fstream>
#include <string>
#include "llsd.h"
#include "llsdutil.h"
#include "llsdserialize.h"

class Puppetry
{
public:
	Puppetry() : mRequestID(-1), mSource("puppetry.controller") {};
	void flog(std::string line);	//SPATTERS delete me!
	void sendRequest(std::string pump, LLSD data, bool init);
	void sendSet(std::string pump, LLSD data);
	void sendGet(std::string pump, LLSD data);
	void waitForHandshake(S32 reqid);
	void poll();
	bool start();
	void stop();

private:
	LLSD _get();
	void redirectSTDOUT(std::string filename);
	void restoreSTDOUT();

	U32 mRequestID;
	LLUUID mReplyPumpID;
	LLUUID mCommandPumpID;
	LLSD mFeatures;
	std::string mSource;

	std::fstream mSTDOUTfile;
	std::streambuf* mSTDOUTstreambuf;
	std::streambuf* mSTDOUTstreamfile;
};

#endif //PUPPETRY_H