# -*- Mode: Python; tab-width: 2; indent-tabs-mode:nil; -*-
# vim: set ts=2 et sw=2 tw=80:
# ***** BEGIN LICENSE BLOCK *****
# Version: Apache License 2.0
#
# Copyright (c) 2011 Design Science, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contributor(s):
#   Frederic Wang <fred.wang@free.fr> (original author)
#
# ***** END LICENSE BLOCK *****

"""
@file runTestsuite.py
The file for the @ref runTestsuite module.

@package runTestsuite
This module is the main script of the test launcher.

@var MATHJAX_TEST_ROOT
Root of the MathJax-test directory.

@var TASK_HANDLER_HOST
Host address of the task handler

@var TASK_HANDLER_PORT
Port of the task handler

@var MAX_FILES_WITH_SAME_NAME
The maximum number of files sharing the same name in the result directory.
"""

MATHJAX_TEST_ROOT = "../"
TASK_HANDLER_HOST = "localhost"
TASK_HANDLER_PORT = 4445
MAX_FILES_WITH_SAME_NAME = 100

from datetime import datetime, timedelta
import ConfigParser
import argparse
import errno
import gzip
import math
import os
import platform
import re
import reftest
import seleniumMathJax
import socket
import string
import subprocess
import sys
import time
import unittest

def getOperatingSystem(aOperatingSystem):

    """
    @fn getOperatingSystem(aOperatingSystem)
    @brief get the operating system

    @param aOperatingSystem the name of an operating system or "auto"
    @return the name of the operating system

    @details The result used is the operating system if it specified or the
    value of Python's platform.system()
    """

    if aOperatingSystem != "auto":
        return aOperatingSystem

    return platform.system()

def getBrowserStartCommand(aBrowserPath, aOS, aBrowser):

    """
    @fn getBrowserStartCommand(aBrowserPath, aOS, aBrowser)
    @brief get the browser start command

    @param aBrowserPath the path to the executable of the browser or "auto"
    @param aOS the name of the operating system
    @param aBrowser the name of the browser
    @return the start command to be used by Selenium 

    @details The return value is "*firefox", "*googlechrome", "*opera",
    "*iexploreproxy", "*konqueror /usr/bin/konqueror" or "unknown" if the
    browser was not recognized.
    """

    if aBrowser == "Firefox":
        startCommand = "*firefox"
    elif (aOS == "Windows" or aOS == "Mac") and aBrowser == "Safari":
        startCommand = "*safariproxy"
    elif aBrowser == "Chrome":
        startCommand = "*googlechrome"
    elif aBrowser == "Opera":
        startCommand = "*opera"
    elif aOS == "Windows" and aBrowser == "MSIE":
        startCommand = "*iexploreproxy"
    elif aOS == "Linux" and aBrowser == "Konqueror":
        startCommand = "*konqueror"
    else:
        startCommand = "*custom"
    
    if aBrowserPath == "auto":
        if startCommand == "*custom":
            print >> sys.stderr, "Unknown browser"
            return "unknown"

        if aOS == "Linux" and aBrowser == "Konqueror":
           startCommand = startCommand + " /usr/bin/konqueror" 
    else:
        startCommand = startCommand + " " + aBrowserPath
    
    return startCommand

def resultsExist(aName):
    """
    @fn resultsExist(aName)
    @brief verify whether there are results with the given name

    @return whether one file with the specified name and extension ".txt",
            ".html", ".txt.gz" or ".html.gz" exists.
    """
    return (os.path.exists(aName + ".txt") or
            os.path.exists(aName + ".html") or
            os.path.exists(aName + ".txt.gz") or
            os.path.exists(aName + ".html.gz"))

def getOutputFileName(aDirectory, aSelenium, aDoNotOverwrite):
    """
    @fn getOutputFileName(aDirectory, aSelenium, aDoNotOverwrite)
    @brief build a file name for the output

    @param aDirectory directory where the test output will be stored
    @param aSelenium @ref seleniumMathJax::seleniumMathJax object
    @param aDoNotOverwrite whether the name should be changed to prevent
           overwriting the result files.

    @return Concatenation of aDirectory, the operating system, the browser,
    the browser mode and the font, separated by underscores. Sometimes followed
    by a "-number" to prevent overwriting files.
    """

    name = aDirectory + \
        aSelenium.mOperatingSystem + "_" + \
        aSelenium.mBrowser + "_" + \
        aSelenium.mBrowserMode + "_" + \
        aSelenium.mFont

    if aDoNotOverwrite and resultsExist(name):
        i = 1
        while (resultsExist(name + "-" + str(i)) and
               i < MAX_FILES_WITH_SAME_NAME):
            i = i + 1
        name += "-" + str(i)

    return name

def boolToString(aBoolean):
    """
    @fn boolToString(aBoolean)
    @brief A simple function to convert a boolean to a string

    @return the string "true" or "false"
    """
    if aBoolean:
        return "true"
    return "false"

def gzipFile(aFile):
    """
    @fn gzipFile(aFile)
    @brief Compress a file using the gzip format.

    @param aFile the file to compress

    @details The action is the same as the gzip command: aFile is compressed
    into an archive aFile.gz and the original file is removed.
    """
    f_in = open(aFile, "rb")
    f_out = gzip.open(aFile + ".gz", "wb")
    f_out.writelines(f_in)
    f_out.close()
    f_in.close()
    os.remove(aFile)

def printReftestList():
    """
    @fn printReftestList()
    @brief generate the file web/reftestList.js
    """
    print "Generating reftestList.js...",

    suite = reftest.reftestSuite()
    fp = file(MATHJAX_TEST_ROOT + "web/reftestList.js", "w")
    stdout = sys.stdout
    sys.stdout = fp
    print "// This file is automatically generated. Do not edit."
    print "/**"
    print " * @file reftestList.js"
    print " * @brief array representing the test suite."
    print " *"
    print " * This file is generated by runTestsuite.py -p"
    print " *" 
    print " * @var Array gTestSuite"
    print " * An array representing the file hierarchy of the test suite"
    print " */"
    print "var gTestSuite = [\"testsuite/\"",
    suite.addReftests(None, MATHJAX_TEST_ROOT + "testsuite/",
                      "reftest.list", -1)
    print "]"
    sys.stdout = stdout
    fp.close()

    print "done"

def removeTemporaryData(aSelenium):
    """
    @fn removeTemporaryData(aSelenium)
    @brief Execute a Selenium instance and call the
           @ref seleniumMathJax::seleniumMathJax::clearBrowserData function.

    @param aSelenium @ref seleniumMathJax::seleniumMathJax object
    """
    aSelenium.start()
    aSelenium.clearBrowserData()
    aSelenium.stop()

def runTestingInstance(aDirectory, aSelenium, aSuite,
                       aFormatOutput, aCompressOutput):
    """
    @fn runTestingInstance(aDirectory, aSelenium, aSuite,
                           aFormatOutput, aCompressOutput)
    @brief Execute a testing instance
    
    @param aDirectory  directory where the test output will be stored
    @param aSelenium @ref seleniumMathJax::seleniumMathJax object
    @param aSuite    @ref reftest::reftestSuite object
    @param aFormatOutput whether output should be formatted
    @param aCompressOutput whether output should be compressed

    @note This function may send the status "Running", "Complete" and
    "Interrupted" to the task handler.
    """

    # Build the testsuite
    aSuite.sendRequest("Running", "Init")
    if aSuite.mListOfTests == "all":
        index = -1 # all tests
    else:
        index = 0 # tests indicated in listOfTests
        
    aSuite.addReftests(aSelenium, MATHJAX_TEST_ROOT + "testsuite/",
                       "reftest.list", index)

    # Create the output file. Do not overwrite the file name if we are not
    # recovering a previous testing instance
    output = getOutputFileName(aDirectory, aSelenium,
                               aSuite.mRunningTestID == "")
    outputTxt = output + ".txt"
    outputHTML= output + ".html"

    if aSuite.mRunningTestID == "":
        # Create a new text file
        fp = file(outputTxt, "w")
    else:
        # A startID is used to recover a test interrupted. Open in "appening"
        # mode to concatenate the outputs.
        fp = file(outputTxt, "a")

    stdout = sys.stdout
    sys.stdout = fp

    # Run the test suite
    startTime = datetime.utcnow()
    aSuite.printInfo("Starting Testing Instance ; " + startTime.isoformat())
    interrupted = False
    try:
        aSuite.printInfo("host =" + str(aSelenium.host))
        aSuite.printInfo("port =" + str(aSelenium.port))
        aSuite.printInfo("mathJaxPath = " + aSelenium.mMathJaxPath)
        aSuite.printInfo("mathJaxTestPath = " + aSelenium.mMathJaxTestPath)
        aSuite.printInfo("operatingSystem = " + aSelenium.mOperatingSystem)
        aSuite.printInfo("browser = " + aSelenium.mBrowser)
        aSuite.printInfo("browserMode = " + aSelenium.mBrowserMode)
        aSuite.printInfo("font = " + aSelenium.mFont)
        aSuite.printInfo("nativeMathML = " +
                         boolToString(aSelenium.mNativeMathML))
        aSuite.printInfo("runSlowTests = " +
                         boolToString(aSuite.mRunSlowTests))
        sys.stdout.flush()
        aSelenium.start()
        aSelenium.pre()
        aSuite.sendRequest("Running")
        unittest.TextTestRunner(sys.stderr, verbosity = 2).run(aSuite)
        aSelenium.post()
        aSelenium.stop()
        time.sleep(4)
    except KeyboardInterrupt:
        aSelenium.post()
        aSelenium.stop()
        interrupted = True

    endTime = datetime.utcnow()
    deltaTime = endTime - startTime

    if not interrupted:
        aSuite.printInfo("Testing Instance Finished ; " +
                         endTime.isoformat())
    else:
        aSuite.printInfo("Testing Instance Interrupted ; " +
                         endTime.isoformat())
        aSuite.printInfo("To recover use parameter")
        aSuite.printInfo("startID = " + aSuite.mRunningTestID)

    aSuite.printInfo("Testing Instance took " +
                     str(math.trunc((deltaTime.days
                                     * 24 * 60 + deltaTime.seconds) / 60))
                     + " minute(s) and " +
                     str(deltaTime.seconds % 60) + " second(s)")
    print

    sys.stdout = stdout
    fp.close()

    if not interrupted:
        if aFormatOutput:
            # Execute the Perl script to format the output
            print "Formatting the text ouput...",
            pipe = subprocess.Popen(["perl", "clean-reftest-output.pl",
                                     outputTxt],
                                    stdout=subprocess.PIPE)
            fp = file(outputHTML, "w")
            print >> fp, pipe.stdout.read()
            fp.close()
            print "done"

        if aCompressOutput:
            # gzip the outputs
            print "Compressing the output files...",
            gzipFile(outputTxt)
            if aFormatOutput:
                gzipFile(outputHTML)
            print "done"

        aSuite.sendRequest("Complete")
    else:
        print
        print "Test Launcher received SIGINT!"
        print "Testing Instance Interrupted."
        aSuite.sendRequest("Interrupted", aSuite.mRunningTestID)
    
def main(aArgs, aTransmitToTaskHandler):
    """
    @fn main(aArgs, aTransmitToTaskHandler)
    @brief main routine of the runTestsuite.py script.

    @param aArgs               command line arguments given by Python's argparse
    @param aTransmitToTaskHandler whether the testing instance should transmit
    information to the task handler.
    """

    global TASK_HANDLER_HOST
    global TASK_HANDLER_PORT

    # if the option --printList is passed, only generate the file
    # reftestList.txt
    if hasattr(aArgs, "printList"):
        printReftestList()
        exit(0)
    
    clearBrowsersData = hasattr(aArgs, "removeTemporaryData")

    if (not clearBrowsersData):
        # create the date directory
        now = datetime.utcnow();
        directory = MATHJAX_TEST_ROOT + "web/results/"
        if not os.path.exists(directory):
            os.makedirs(directory)

        # create the subdirectory
        if aArgs.output and re.match("^([0-9]|[a-z]|[A-Z]|-|/){1,50}/$",
                                    aArgs.output):
            directory += aArgs.output
        else:
            directory += now.strftime("%Y-%m-%d/%H-%M-%S/")

        if not os.path.exists(directory):
            os.makedirs(directory)

    # execute testing instances for all the config files
    configFileList = aArgs.config.split(",")

    for configFile in configFileList:

        configFile = configFile

        if (not os.path.isfile(configFile)):
            print >> sys.stderr,\
                "Warning: config file " + configFile + " not found!"
            continue

        # Load configuration file
        config = ConfigParser.ConfigParser()
        config.readfp(open(configFile))

        # framework section
        section = "framework"
        host = config.get(section, "host")
        port = config.getint(section, "port")
        mathJaxPath = config.get(section, "mathJaxPath")
        mathJaxTestPath = config.get(section, "mathJaxTestPath")
        timeOut = config.getint(section, "timeOut")
        fullScreenMode = config.getboolean(section, "fullScreenMode")
        formatOutput = config.getboolean(section, "formatOutput")
        compressOutput = config.getboolean(section, "compressOutput")

        # platform section
        section = "platform"
        operatingSystem = getOperatingSystem(config.get(section,
                                                        "operatingSystem"))
        browserList = config.get(section, "browser").split()
        browserModeList = config.get(section, "browserMode").split()
        browserPath = config.get(section, "browserPath")
        fontList = config.get(section, "font").split()
        nativeMathML = config.getboolean(section, "nativeMathML")
    
        # testsuite section
        section = "testsuite"
        runSlowTests = config.getboolean(section, "runSlowTests")
        runSkipTests = config.getboolean(section, "runSkipTests")
        listOfTests = config.get(section, "listOfTests")
        startID = config.get(section, "startID")
       
        # When more than one browser is specified, browserPath is ignored.
        if (len(browserList) > 1 and browserPath != "auto"):
            print >> sys.stderr, "Warning: browserPath ignored"
            browserPath = "auto"

        # If we just want to clear browsers data, we ignore the list of fonts
        # and browser modes.
        if clearBrowsersData:
            fontList = ["STIX"]
            browserModeList = ["StandardMode"]

        i = 0

        for browser in browserList:

            for font in fontList:

                # browserModeList is only relevant for MSIE
                if not(browser == "MSIE"):
                    browserModeList2 = ["StandardMode"]
                else:
                    browserModeList2 = browserModeList
               
                for browserMode in browserModeList2:

                    browserStartCommand = \
                        getBrowserStartCommand(browserPath,
                                               operatingSystem,
                                               browser)

                    if browserStartCommand != "unknown":

                        # Create a Selenium instance
                        selenium = \
                            seleniumMathJax.seleniumMathJax(host,
                                                            port,
                                                            mathJaxPath,
                                                            mathJaxTestPath,
                                                            operatingSystem,
                                                            browser,
                                                            browserMode,
                                                            browserStartCommand,
                                                            font,
                                                            nativeMathML,
                                                            timeOut,
                                                            fullScreenMode)
                        
                        if (clearBrowsersData):
                            removeTemporaryData(selenium)
                        else:
                            if aTransmitToTaskHandler:
                                taskHandler = [TASK_HANDLER_HOST,
                                               TASK_HANDLER_PORT,
                                               str(os.getpid())]
                            else:
                                taskHandler = None
                            # Create the test suite
                            suite = reftest.reftestSuite(taskHandler,
                                                         runSlowTests,
                                                         runSkipTests,
                                                         listOfTests,
                                                         startID)
                            runTestingInstance(directory, selenium, suite,
                                               formatOutput, compressOutput)

                    # end if browserStartCommand

                    i = i + 1

                # end browserMode
            # end for font
        # end browser

def announceDeath(aDeath, aExceptionMessage = None):
    """
    @fn announceDeath(aDeath, aExceptionMessage = None)
    @brief announce the death of the runTestsuite script to the task handler

    @param aDeath the kind of death that happened: EXPECTED or UNEXPECTED.
    @param aExceptionMessage exception message raised or None if the death
    was expected.
    """

    global TASK_HANDLER_HOST
    global TASK_HANDLER_PORT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TASK_HANDLER_HOST, TASK_HANDLER_PORT))
        s = "TASK " + aDeath + "_DEATH " + str(os.getpid()) + "\n"

        if aExceptionMessage != None:
            s += aExceptionMessage
            s += "\nTASK DEATH END\n"

        sock.send(s)
    except socket.error:
        print >> sys.stderr, "Could not announce death to the task handler"
        return

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="A Python script to run MathJax automated tests.")
    parser.add_argument("-c", "--config", nargs = "?",
                        default = "config/default.cfg",
                        help="A comma separated list of files describing the \
parameters of the automated test instance to run. The default configuration \
file is config/default.cfg.")
    parser.add_argument("-o", "--output", nargs = "?", default = None,
                        help="By default, the output files are stored in \
default web/results/YEAR-MONTH-DAY/TIME/. This option allows to specify a \
custom sub directory instead of the date.")
    parser.add_argument("-p", "--printList", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="If this option is used, the script will print \
generate the file reftestList.txt instead of running tests.")
    parser.add_argument("-t", "--transmitToTaskHandler", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="If this option is used, the script will transmit \
the its status to the task handler.")
    parser.add_argument("-r", "--removeTemporaryData", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="Remove temporary data from the browsers \
(not implemented)")

    args = parser.parse_args()

    if hasattr(args, "transmitToTaskHandler"):
        try:
            main(args, True)
            announceDeath("EXPECTED")
            exit(0)
        except Exception as e:
            announceDeath("UNEXPECTED", str(e))
            exit(1)
    else:
        main(args, False)
        exit(0)
