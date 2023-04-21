// PuppetryTest.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#ifndef WIN32
#define WIN32  //Everything in llapr.h breaks without this defined.
#endif

#include <iostream>
#include <fstream>
#include <string>
#include "llsd.h"
#include "llsdutil.h"
#include "llsdserialize.h"
#include "puppetry.h"

void crudeLoop(Puppetry& p)
{
	S32 step = 0;
	bool reverse = false;

	LLSD test = LLSD::emptyMap();

	test["inverse_kinematics"] = LLSD::emptyMap();
	test["inverse_kinematics"]["mElbowRight"] = LLSD::emptyMap();
	test["inverse_kinematics"]["mElbowRight"]["position"] = LLSD::emptyArray();
	test["inverse_kinematics"]["mElbowRight"]["position"].append(0.3f);
	test["inverse_kinematics"]["mElbowRight"]["position"].append(-0.2f);
	test["inverse_kinematics"]["mElbowRight"]["position"].append(0.211f);

	while (1)
	{
		//p.poll(); //FHandle incoming messages; flush stdin.  TODO put into a thread.

		//world's crudest arm wave.
		test["inverse_kinematics"]["mElbowRight"]["position"][2] = (float)(step) * 0.05 + 0.1;
		p.sendSet("puppetry", test);

		if (reverse)
		{
			step--;
			if (step < 0)
			{
				reverse = false;
			}
		}
		else
		{
			step++;
			if (step > 19)
			{
				reverse = true;
			}
		}
		_sleep(100);	//TODO:  A timer-based approach.
	}
}


int main()
{
	Puppetry p;

	p.start();

	crudeLoop(p);
}