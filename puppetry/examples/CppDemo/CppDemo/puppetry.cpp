#include <iostream>
#include <fstream>
#include <string>
#include "llsd.h"
#include "llsdutil.h"
#include "llsdserialize.h"
#include "puppetry.h"

std::ofstream TMPLOGFILE;	//SPATTERS remove me!
std::string TMPLOGFILENAME = "C:\\Users\\aura\\logfile.txt";

void Puppetry::flog(std::string line)
{
	//TODO replace with LL_INFOS.

	TMPLOGFILE << line << std::endl;
	return;
}

LLSD Puppetry::_get()
{
	//Private function for getting data from stdin and parsing it as llsd.

	int count = 0;

	std::vector<char> buff;
	char c = '\0';

	std::cin.seekg(0, std::cin.end);
	int length = std::cin.tellg();
	if (length < 0)
	{
		return LLSD::emptyMap();
	}

	//Get bytes until we hit a : or exceed our count.

	while (!std::cin.eof())
	{
		std::cin >> c;
		buff.push_back(c);
		count++;
		if (c == ':' || count > 20)
		{
			break;
		}
	}
	if (c == ':')
	{
		std::string line(buff.begin(), buff.end());
		U32 num_bytes = std::stol(line);
		buff.clear();
		buff.resize(num_bytes + 2);
		std::cin.read(buff.data(), num_bytes);
		buff.push_back('\0');
		line = std::string(buff.begin(), buff.end());
		flog(line);   //What's our input look like?
		LLPointer<LLSDParser> parser = new LLSDNotationParser();
		LLSD data;
		std::istringstream iss(line);
		if (parser->parse(iss, data, line.length()) == LLSDParser::PARSE_FAILURE)
		{
			LL_WARNS("LEAP") << "Parsing received message failed" << LL_ENDL;
			return LLSD::emptyMap();
		}

		/* TODO switch to this implementation.
		if (!LLSDSerialize::deserialize(data, iss, line.size()))
		{
			return LLSD::emptyMap();
		}
		*/

		return data;
	}
	return LLSD::emptyMap();
}


void Puppetry::sendRequest(std::string pump, LLSD data, bool init = false)
{
	static U32 reqid = 1;

	if (!init)
	{
		if (!data.has("reply"))
		{
			data["reply"] = mReplyPumpID;
		}
	}

	LLSD msg = LLSD::emptyMap();
	msg["pump"] = pump;
	msg["data"] = data;
	
	if (!init)
	{
		msg["reqid"] = LLSD::Integer(mRequestID);
	}

	std::ostringstream oss;
	oss << msg;
	U32 sz = (U32)oss.str().size();

	//std::cout.rdbuf(mSTDOUTstreambuf);
	std::cout << sz << ":" << oss.str();
	//std::cout.rdbuf(mSTDOUTstreamfile);

	std::ostringstream deb;
	deb << sz << ":" << oss.str();
	flog(deb.str());
	std::flush(std::cout);

	mRequestID++;	//Increment request counter
}

void Puppetry::sendSet(std::string pump, LLSD data)
{
	LLSD msg = LLSD::emptyMap();
	msg["command"] = "set";
	msg["data"] = data;
	sendRequest(pump, msg);
}

void Puppetry::sendGet(std::string pump, LLSD data)
{
	std::string verb = "get";
	LLSD msg = LLSD::emptyMap();

	msg["data"] = verb;

	if (data.isArray())
	{
		msg[verb] = data;
	}
	else
	{
		msg[verb] = LLSD::emptyArray();
		msg[verb].append(data);
	}
	sendRequest(pump, msg);
}

void Puppetry::redirectSTDOUT(std::string filename)
{
	mSTDOUTfile.open(filename, std::ios::out);
	std::string line;

	// Backup streambuffers of  cout
	mSTDOUTstreambuf = std::cout.rdbuf();

	// Get the streambuffer of the file
	mSTDOUTstreamfile = mSTDOUTfile.rdbuf();

	// Redirect cout to file
	std::cout.rdbuf(mSTDOUTstreamfile);
}

void Puppetry::waitForHandshake(S32 reqid)
{
	//TODO:  Add some result codes here instead of just pretending everything is fine.
	while(1)
	{
		LLSD msg = _get();

		if (msg != LLSD::emptyMap() && msg.has("data") && msg["data"].has("reqid"))
		{
			if (msg["data"]["reqid"].asInteger() == reqid)
			{
				break;
			}
		}
		else
		{
			LL_DEBUGS("PUPPET") << "Skipping bad response" << LL_ENDL;
		}
	}
}

void Puppetry::poll()
{
	//TODO:  Put this in a thread.

	LLSD msg;

	//For now, just flush the buffer every frame
	//by getting messages until we have an empty map.
	for (msg=_get(); msg != LLSD::emptyMap(); )
	{
		std::string cmd = msg["data"]["command"].asString();
		LLSD args = msg["data"]["args"]; //An array.

		if (cmd == "stop")
		{
			stop();
		}
		//else{}  TODO handle other commands.
	}
}

void Puppetry::stop()
{
	//std::cout.rdbuf(mSTDOUTstreambuf);	//Restore stdout
	//mSTDOUTfile.close();				//Close output file.
	//TODO send Puppetry stop.
	TMPLOGFILE.close();
}

bool Puppetry::start()
{
	TMPLOGFILE.open(TMPLOGFILENAME, std::ios_base::out);

	//redirectSTDOUT("redirected_output.txt");
	mRequestID = -1;		//Reset request ID.

	LLSD msg = _get();

	if (msg == LLSD::emptyArray())
	{
		LL_WARNS("PUPPET") << "Failed to get a line" << LL_ENDL;
		return false;
	}

	flog(ll_pretty_print_sd(msg));
	
	if (!msg.has("pump") || !msg.has("data") || !msg["data"].has("command") || !msg["data"].has("features"))
	{
		LL_WARNS("PUPPET") << "Initial state did not contain correct payload" << LL_ENDL;
		return false;
	}

	mReplyPumpID = msg["pump"].asUUID();
	mCommandPumpID = msg["data"]["command"].asUUID();
	mFeatures = msg["data"]["features"];

	LLSD response;
	response["op"] = "listen";
	response["reqid"] = (LLSD::Integer)mRequestID;
	response["source"] = mSource;
	response["listener"] = mReplyPumpID;

	sendRequest(mCommandPumpID.asString(), response, true);
	//waitForHandshake(response["reqid"].asInteger());

	return true;
}