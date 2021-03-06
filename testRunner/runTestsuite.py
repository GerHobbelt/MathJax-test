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

@var MAX_TEST_RESULTS_WITH_SAME_NAME
The maximum number of output files sharing the same name in the result/
directory.
"""

from __future__ import print_function

MAX_TEST_RESULTS_WITH_SAME_NAME = 100
MATHJAX_WEB_PATH = "../web/"
MATHJAX_TESTSUITE_PATH = "../testsuite/"

from config import PERL, SED
from config import TASK_HANDLER_HOST, TASK_HANDLER_PORT
from config import WARNING_GENERATED_FILE

from config import MATHJAX_TEST_PUBLIC_URI, MATHJAX_TEST_LOCAL_URI
from config import DEFAULT_MATHJAX_PATH

from config import HOST_LIST, OS_LIST, HOST_LIST_OS, SELENIUM_SERVER_PORT
from config import BROWSER_LIST, FONT_LIST
from config import DEFAULT_TIMEOUT, OUTPUT_JAX_LIST

from datetime import datetime, timedelta
import ConfigParser
import argparse
import errno
import gzip
import math
import os
import re
import reftest
import seleniumMathJax
import socket
import string
import subprocess
import sys
import time

from selenium.common.exceptions import WebDriverException

def boolToString(aBoolean):
    """
    @fn boolToString(aBoolean)
    @brief A simple function to convert a boolean to a string

    @return the string "true" or "false"
    """
    if aBoolean:
        return "true"
    return "false"

def getBooleanOption(aConfig, aSection, aOption):
    """
    @fn getBooleanOption(aConfig, aSection, aOption)
    @brief Retrieve a boolean option from a config file
    @param aConfig config object
    @param aSection section in the config object
    @param aOption boolean option in this section

    @return the boolean option or a default value.
    """
    if aConfig.has_option(aSection, aOption):
        return aConfig.getboolean(aSection, aOption)
    else:
        # Default value. This should match the initialization done in
        # __init__ of class task in taskHandler.py
        if (aOption == "fullScreenMode" or
            aOption == "formatOutput" or
            aOption == "compressOutput"):
            return True
        else:
            # "useWebDriver"
            # "runSlowTests"
            # "runSkipTests"
            # "useGrid"
            return False

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

def getOutputFileName(aDirectory, aSelenium, aSuite):
    """
    @fn getOutputFileName(aDirectory, aSelenium, aSuite)
    @brief build a file name for the output

    @param aDirectory directory where the test output will be stored
    @param aSelenium @ref seleniumMathJax::seleniumMathJax object
    @param aSuite @ref reftest::reftestSuite object

    @return Concatenation of aDirectory, the operating system, the browser,
    the browser mode, the font and the output Jax, separated by underscores.
    Sometimes followed by a "-number" to prevent overwriting files.
    """

    name = \
        aSelenium.mOperatingSystem + "_" + \
        aSelenium.mBrowser + "_" + \
        aSelenium.mBrowserMode + "_" + \
        aSelenium.mFont + "_" + \
        aSelenium.mOutputJax

    if resultsExist(aDirectory + name):
        i = 1
        while (resultsExist(aDirectory + name + "-" + str(i)) and
               i < MAX_TEST_RESULTS_WITH_SAME_NAME):
            i = i + 1
        name += "-" + str(i)

    if (aSuite.mTaskHandler != None):
        sendOutputFileName(name);

    return name

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
    print("Generating reftestList.js...", end="")

    suite = reftest.reftestSuite()
    fp = file(MATHJAX_WEB_PATH + "reftestList.js", "w")
    stdout = sys.stdout
    sys.stdout = fp
    print("// " + WARNING_GENERATED_FILE)
    print("/**")
    print(" * @file reftestList.js")
    print(" * @brief array representing the test suite.")
    print(" *")
    print(" * This file is generated by runTestsuite.py -p")
    print(" *")
    print(" * @var Array gTestSuite")
    print(" * An array representing the file hierarchy of the test suite")
    print(" */")
    print("var gTestSuite = [\"testsuite/\"", end="")
    suite.addReftests("printList",
                      MATHJAX_TESTSUITE_PATH, "reftest.list", -1)
    print("]")
    sys.stdout = stdout
    fp.close()

    print("done")

def printNotes():
    """
    @fn printNotes()
    @brief generate the file web/reftestList.js
    """
    print("Generating testsuiteNodes.js...", end="")

    suite = reftest.reftestSuite()
    fp = file(MATHJAX_WEB_PATH + "testsuiteNotes.html", "w")
    stdout = sys.stdout
    sys.stdout = fp
    print('<!doctype>')
    print('<!-- ' + WARNING_GENERATED_FILE + '-->')
    print('<html>')
    print('<head>')
    print(' <meta http-equiv="Content-type" content="text/html;charset=UTF-8">')
    print(' <title>Testsuite Notes</title>')
    print(' <link rel="stylesheet" type="text/css" href="default.css"/>')
    print('</head>')
    print('<body>')
    print('<div class="related">')
    print('  <h3>Navigation</h3>')
    print('  <ul>')
    print('    <li><a href="./">Back to home</a></li> ')
    print('  </ul>')
    print('</div>')

    print('<div class="body testsuiteNotes">')
    print('  <h1>Testsuite Notes</h1>')

    suite.addReftests("printNotes",
                      MATHJAX_TESTSUITE_PATH, "reftest.list", -1)
    print('</div>')
    print('</body>')
    print('</html>')
    sys.stdout = stdout
    fp.close()

    print("done")

def printListOfTests(aFile):
    """
    @fn printListOfTests(aFile)
    @brief generate a listOftests from a file
    """
    lines = []
    for line in open(aFile, "r"):
        line = line.rstrip('\n')
        lines.append(line)
    suite = reftest.reftestSuite()
    suite.addReftests(["printListOfTests", lines],
                      MATHJAX_TESTSUITE_PATH, "reftest.list", -1)
    print

def runTestingInstance(aDirectory, aSelenium, aSuite,
                       aFormatOutput, aCompressOutput, aFileName):
    """
    @fn runTestingInstance(aDirectory, aSelenium, aSuite,
                           aFormatOutput, aCompressOutput, aFileName)
    @brief Execute a testing instance
    
    @param aDirectory  directory where the test output will be stored
    @param aSelenium @ref seleniumMathJax::seleniumMathJax object
    @param aSuite    @ref reftest::reftestSuite object
    @param aFormatOutput whether output should be formatted
    @param aCompressOutput whether output should be compressed
    @param aFileName Name of the output file

    @note This function may send the status "Running", "Complete" and
    "Interrupted" to the task handler.
    """

    # Build the testsuite
    aSuite.sendRequest("Running", "Init")
    if aSuite.mListOfTests == "default":
        index = -1 # all tests
    else:
        index = 0 # tests indicated in listOfTests
        
    aSuite.addReftests(aSelenium, MATHJAX_TESTSUITE_PATH,
                       "reftest.list", index)

    outputTxt  = aDirectory + aFileName + ".txt"
    outputHTML = aDirectory + aFileName + ".html"

    if aSuite.mRunningTestID == "":
        # Create a new text file
        fp = file(outputTxt, "w")
    else:
        # A startID is used to recover a test interrupted.

        # First delete all the lines from the line containing
        # "| startID |" to the one containing " ==Interruption== ".
        # This will clear outputs for tests after the startID and keep
        # the info about the fact that the instance was interrupted.
        regExp = aSuite.mRunningTestID
        regExp = regExp.replace("/", "\\/")
        regExp = "/| " + regExp + " |/,"
        regExp += "/==Interruption==/d"
        subprocess.call([SED, "-i", regExp, outputTxt])

        # Now open in "appening" mode to concatenate the outputs.
        fp = file(outputTxt, "a")

    stdout = sys.stdout
    sys.stdout = fp

    # Run the test suite
    startTime = datetime.utcnow()
    aSuite.printInfo("Starting Testing Instance ; " + startTime.isoformat())
    interrupted = False
    try:
        aSuite.printInfo("host = " + str(aSelenium.mHost))
        aSuite.printInfo("port = " + str(aSelenium.mPort))
        
        aSuite.printInfo("mathJaxPath = " + 
                         string.replace(aSelenium.mMathJaxPath,
                                        MATHJAX_TEST_LOCAL_URI,
                                        MATHJAX_TEST_PUBLIC_URI, 1))
        aSuite.printInfo("mathJaxTestPath = " +
                         string.replace(aSelenium.mMathJaxTestPath,
                                        MATHJAX_TEST_LOCAL_URI,
                                        MATHJAX_TEST_PUBLIC_URI, 1))

        aSuite.printInfo("useWebDriver = " +
                         boolToString(aSelenium.mWebDriver != None))
        aSuite.printInfo("operatingSystem = " + aSelenium.mOperatingSystem)
        aSuite.printInfo("browser = " + aSelenium.mBrowser)
        aSuite.printInfo("browserVersion = " + aSelenium.mBrowserVersion)
        aSuite.printInfo("browserMode = " + aSelenium.mBrowserMode)
        aSuite.printInfo("font = " + aSelenium.mFont)
        aSuite.printInfo("outputJax = " + aSelenium.mOutputJax)
        aSuite.printInfo("runSlowTests = " +
                         boolToString(aSuite.mRunSlowTests))
        aSuite.printInfo("runSkipTests = " +
                         boolToString(aSuite.mRunSkipTests))
        aSuite.printInfo("listOfTests = " + aSuite.mListOfTests)
        sys.stdout.flush()
        aSelenium.start()
        aSelenium.pre()
        aSuite.run()
        aSelenium.post()
        aSelenium.stop()
        time.sleep(4)
    except KeyboardInterrupt:
        aSelenium.post()
        aSelenium.stop()
        interrupted = True
    except WebDriverException:
        interrupted = True
    except Exception:
        if (not aSuite.mTaskHandler):
            # If we don't have a task handler, report this expection normally.
            # Indeed, that can be a possible syntax error in the Python script
            raise
        else:
            interrupted = True

    endTime = datetime.utcnow()
    deltaTime = endTime - startTime

    if not interrupted:
        aSuite.printInfo("Testing Instance Finished ; " +
                         endTime.isoformat())
    else:
        # these markers are used to clean output when the test is recovered
        print("==| " + aSuite.mRunningTestID + " |==")
        print("==Interruption==")

        aSuite.printInfo("Testing Instance Interrupted ; " +
                         endTime.isoformat())
        aSuite.printInfo("To recover use parameter")
        aSuite.printInfo("startID = " + aSuite.mRunningTestID)

    aSuite.printInfo("Testing Instance took " +
                     str(math.trunc((deltaTime.days
                                     * 24 * 60 + deltaTime.seconds) / 60))
                     + " minute(s) and " +
                     str(deltaTime.seconds % 60) + " second(s)")
    aSuite.printInfo("")

    sys.stdout = stdout
    fp.close()

    if not interrupted:
        if aFormatOutput:
            # Execute the Perl script to format the output
            print("Formatting the text ouput...", end="")
            pipe = subprocess.Popen([PERL, "clean-reftest-output.pl",
                                     outputTxt, MATHJAX_TEST_PUBLIC_URI],
                                    stdout=subprocess.PIPE)
            fp = file(outputHTML, "w")
            print(pipe.stdout.read(), file = fp)
            fp.close()
            print("done")

        if aCompressOutput:
            # gzip the outputs
            print("Compressing the output files...", end="")
            gzipFile(outputTxt)
            if aFormatOutput:
                gzipFile(outputHTML)
            print("done")

        aSuite.sendRequest("Complete")
    else:
        print
        print("Testing Instance Interrupted.")
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

    # if the option --printNotes is passed, only generate the
    # testsuiteNotes html page.
    if hasattr(aArgs, "printNotes"):
        printNotes()
        exit(0)

    # if the option --printListOfTests is passed, only generate a ListOfTests
    # from a file containing test URIs
    if hasattr(aArgs, "printListOfTests"):
        if not aArgs.printListOfTests:
            print("No input file!", file=sys.stderr)
            exit(0)
        printListOfTests(aArgs.printListOfTests)
        exit(0)

    # create the date directory
    now = datetime.utcnow();
    directory = MATHJAX_WEB_PATH + "results/"
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
            print("Warning: config file " + configFile + " not found!",
                  file=sys.stderr)
            continue

        # Load configuration file
        config = ConfigParser.ConfigParser()
        config.readfp(open(configFile))

        # framework section
        section = "framework"
        useGrid = getBooleanOption(config, section, "useGrid")
        host = config.get(section, "host")
        # host == "default" is handled below
        port = config.getint(section, "port")
        if (port == -1):
            port = SELENIUM_SERVER_PORT
        mathJaxPath = config.get(section, "mathJaxPath")
        if (mathJaxPath == "default"):
            mathJaxPath = DEFAULT_MATHJAX_PATH
        mathJaxTestPath = config.get(section, "mathJaxTestPath")
        if (mathJaxTestPath == "default"):
            mathJaxTestPath = MATHJAX_TEST_LOCAL_URI + "testsuite/"
        timeOut = config.getint(section, "timeOut")
        if (timeOut == -1):
            timeOut = DEFAULT_TIMEOUT
        timeOut = timeOut * 1000 # convert in ms
        useWebDriver = getBooleanOption(config, section, "useWebDriver")
        fullScreenMode = getBooleanOption(config, section, "fullScreenMode")
        formatOutput = getBooleanOption(config, section, "formatOutput")
        compressOutput = getBooleanOption(config, section, "compressOutput")

        # platform section
        section = "platform"
        operatingSystem = config.get(section, "operatingSystem")
        if (operatingSystem == "default"):
            operatingSystem = OS_LIST[0]
        if (host == "default"):
            host = HOST_LIST[HOST_LIST_OS.index(OS_LIST.index(operatingSystem))]
        browserList = config.get(section, "browser").split()
        browserVersionList = config.get(section, "browserVersion").split()
        browserModeList = config.get(section, "browserMode").split()
        browserPath = config.get(section, "browserPath")
        fontList = config.get(section, "font").split()
        outputJaxList = config.get(section, "outputJax").split()
    
        # testsuite section
        section = "testsuite"
        runSlowTests = getBooleanOption(config, section, "runSlowTests")
        runSkipTests = getBooleanOption(config, section, "runSkipTests")
        listOfTests = config.get(section, "listOfTests")
        startID = config.get(section, "startID")
        if (startID == "default"):
            startID = ""
       
        # When more than one browser is specified, browserPath is ignored.
        if (len(browserList) > 1 and browserPath != "default"):
            print("Warning: browserPath ignored", file=sys.stderr)
            browserPath = "default"

        for browser in browserList:

            if (browser == "default"):
                browser = BROWSER_LIST[0]

            for font in fontList:

                if (font == "default"):
                    font = FONT_LIST[0]

                for outputJax in outputJaxList:

                    if (outputJax == "default"):
                        outputJax = OUTPUT_JAX_LIST[0]

                    for browserVersion in browserVersionList:

                        # browserModeList is only relevant for MSIE
                        if not(browser == "MSIE"):
                            browserModeList2 = ["default"]
                        else:
                            browserModeList2 = browserModeList
               
                        for browserMode in browserModeList2:
                           
                            # Create a Selenium instance
                            selenium = \
                                seleniumMathJax.seleniumMathJax(useWebDriver,
                                                                useGrid,
                                                                host,
                                                                port,
                                                                mathJaxPath,
                                                                mathJaxTestPath,
                                                                operatingSystem,
                                                                browser,
                                                                browserVersion,
                                                                browserMode,
                                                                browserPath,
                                                                font,
                                                                outputJax,
                                                                timeOut,
                                                                fullScreenMode)
                            
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
                            # use the specified file name
                            if hasattr(aArgs, "filename"):
                                filename = aArgs.filename
                            else:
                                filename = getOutputFileName(directory,
                                                             selenium,
                                                             suite)
                            runTestingInstance(directory, selenium, suite,
                                               formatOutput, compressOutput,
                                               filename)
                        # end browserMode
                    # end browserVersion
                #end outputJax
            # end for font
        # end browser

def sendOutputFileName(aName):
    """
    @fn sendOutputFileName(aName)
    @brief send the output file name to the task handler
    """

    global TASK_HANDLER_HOST
    global TASK_HANDLER_PORT

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TASK_HANDLER_HOST, TASK_HANDLER_PORT))
        s = "TASK OUTPUTFILENAME " + str(os.getpid()) + " " + aName + "\n"
        sock.send(s)
    except socket.error:
        print("Could not send output file name to the task handler",
              file=sys.stderr)

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
        print("Could not announce death to the task handler", file=sys.stderr)

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
    parser.add_argument("-f", "--filename", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="Specify a file name to use. Warning: should only \
be used by the task handler during test recovery.")
    parser.add_argument("-p", "--printList", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="If this option is used, the script will print \
generate the file reftestList.txt instead of running tests.")
    parser.add_argument("-n", "--printNotes", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="If this option is used, the script will print \
generate the file testsuiteNotes.html instead of running tests.")
    parser.add_argument("-l", "--printListOfTests", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="Specify a file containting a list of test URIs. \
If this option is used, the script will print a listOfTests parameter instead \
of running tests.")
    parser.add_argument("-t", "--transmitToTaskHandler", nargs = "?",
                        default = argparse.SUPPRESS,
                        help="If this option is used, the script will transmit \
the its status to the task handler.")

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
