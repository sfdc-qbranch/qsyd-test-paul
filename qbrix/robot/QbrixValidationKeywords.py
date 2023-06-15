import json
import sys
import os
from xml import etree

import pandas as pd
import pandasql as ps
import subprocess
from time import sleep
from datetime import datetime
from typing import Optional
from Browser import ElementState, SelectAttribute
from cumulusci.robotframework.base_library import BaseLibrary
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI
from qbrix.robot.QbrixSharedKeywords import QbrixSharedKeywords


# pip install pandas
# pip install pandasql3

class QbrixValidationKeywords(BaseLibrary):

    def __init__(self):
        super().__init__()
        self._browser = None
        self._salesforceapi = None
        self.shared = QbrixSharedKeywords()
        self._validationresults = None

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    @property
    def salesforceapi(self):
        if self._salesforceapi is None:
            self._salesforceapi = SalesforceAPI()
        return self._salesforceapi

    @property
    def validationresults(self):
        if self._validationresults is None:
            self._validationresults = []

        if "results" not in self._validationresults:
            self._validationresults = {"results": []}

        return self._validationresults

    def __recordFailureResultException(self, resulttype: str, name: str, exceptionMessage: str, datatag=None):
        """
        Records Record Failure Result Exception in results file and raises exception
        :param resulttype:
        :param name:
        :param exceptionMessage:
        :param datatag:
        """
        self.__recordFailureResult(resulttype, name, exceptionMessage, datatag=datatag)
        # res not resolving to any references here
        # self.validationresults["results"].append(res)
        # self.__writeresultstofile()
        raise Exception(exceptionMessage)

    def __recordIgnoredResult(self, resulttype: str, name: str, details: str = None, datatag=None):
        """
        Writes Record Ignored Result to Results File
        :param resulttype:
        :param name:
        :param details:
        :param datatag:
        """
        if details is None:
            details = ""

        if datatag is None:
            datatag = ""

        res = {'type': resulttype, 'name': name, 'status': "Ignored", 'details': details, 'datatag': datatag}

        self.validationresults["results"].append(res)
        self.__writeresultstofile()

    def __recordFailureResult(self, resulttype: str, name: str, details: str = None, datatag=None):
        """
        Write Record Failure Result to results file
        :param resulttype:
        :param name:
        :param details:
        :param datatag:
        """
        if details is None:
            details = ""

        if datatag is None:
            datatag = ""

        res = {'type': resulttype, 'name': name, 'status': "Failing", 'details': details, 'datatag': datatag}

        self.validationresults["results"].append(res)
        self.__writeresultstofile()

    def __recordPassingResult(self, resulttype: str, name: str, details: str = None, datatag=None):
        """
        Add Record Passing Result to Results File
        :param resulttype:
        :param name:
        :param details:
        :param datatag:
        """
        if details is None:
            details = ""

        if datatag is None:
            datatag = ""

        res = {'type': resulttype, 'name': name, 'status': "Passing", 'details': details, 'datatag': datatag}

        self.validationresults["results"].append(res)
        self.__writeresultstofile()

    def __writeresultstofile(self):
        """
        Check for and update the results file
        """
        if os.path.isfile("validationresult.json"):
            os.remove("validationresult.json")

        with open(f"validationresult.json", "w+") as tmpFile:
            jsondata = json.dumps(self.validationresults)
            tmpFile.write(jsondata)
            tmpFile.close()

    def validate_minimal_rowcount(self, targetobject, count, filter=None, tooling=False, continueonfail=True,
                                  datatag=None, targetruntime: str = "ALL"):
        """
        Validate that the rows for the target object and filter do not go below the minimal count
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :param targetobject: The target object you want to lookup
        :param count: The expected minimal count for the object
        :param filter: (Optional) SOQL Filter for the target object (e.g. MyCustomField__c = 'Example')
        :param tooling: (Optional) Set to True if the target object requires the Tooling API
        :param continueonfail: (Optional) Boolean flag to continue testing or abort
        """

        resulttype = "Data"
        resultname = f'Validate Minimal Count of {targetobject} for {count} rows'

        # Check the runtime to see if this validation should be run on the org type
        if self.__isapplicableruntime(targetruntime) is False:
            self.__recordIgnoredResult(resulttype, resultname,
                                       f"IGNORED::targetruntime {targetruntime} does not apply to this org",
                                       datatag=datatag)
            return

        if targetobject is None:
            self.__recordFailureResultException(resulttype, resultname, "A target object must be specified",
                                                datatag=datatag)

        if count is None:
            self.__recordFailureResultException(resulttype, resultname,
                                                "'count' must be specified. This should be the minimum number of object records you expect in the org.",
                                                datatag=datatag)

        foundcnt = self.find_record_count(targetobject, filter, tooling)

        if not (int(foundcnt) >= int(count)):
            if continueonfail:
                self.__recordFailureResult(resulttype, resultname,
                                           f"A minimal count not met. The expected minimal number of records was: {count} and the total found was: {foundcnt}",
                                           datatag=datatag)
                return
            else:
                self.__recordFailureResultException(resulttype, resultname,
                                                    f"A minimal count not met. The expected minimal number of records was: {count} and the total found was: {foundcnt}",
                                                    datatag=datatag)

        self.__recordPassingResult(resulttype, resultname, f"Minimal count met. Found: {foundcnt}", datatag=datatag)

        pass

    def validate_exact_rowcount(self, targetobject, count, filter=None, tooling=False, continueonfail=True,
                                datatag=None, targetruntime: str = "ALL"):
        """
        Validate that the rows for the target object and filter match the expected count
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :param targetobject: Target Object you want to lookup
        :param count: Expected count for the object.
        :param filter: (Optional) SOQL Filter for the target object (e.g. MyCustomField__c = 'Example')
        :param tooling: (Optional) Set to True if the target object requires the Tooling API
        :param continueonfail: (Optional) Boolean flag to continue testing or abort
        """

        resulttype = "Data"
        resultname = f'Validate Exact Count of {targetobject} for {count} rows'

        # Check the runtime to see if this validation should be run on the org type
        if not self.__isapplicableruntime(targetruntime):
            self.__recordIgnoredResult(resulttype, resultname,
                                       f"IGNORED::targetruntime {targetruntime} does not apply to this org",
                                       datatag=datatag)
            return

        if targetobject is None:
            self.__recordFailureResultException(resulttype, resultname, "A target object must be specified",
                                                datatag=datatag)

        if count is None:
            self.__recordFailureResultException(resulttype, resultname,
                                                "'count' must be specified. This should be the exact number of object records you expect in the org.",
                                                datatag=datatag)

        foundcnt = self.find_record_count(targetobject, filter, tooling)

        if not foundcnt == int(count):
            if continueonfail:
                self.__recordFailureResult(resulttype, resultname,
                                           f"An exact count not met. Expected was: {count} and found count was {foundcnt}",
                                           datatag=datatag)
                return
            else:
                self.__recordFailureResultException(resulttype, resultname,
                                                    f"An exact count not met. Expected was: {count} and found count was {foundcnt}",
                                                    datatag=datatag)

        self.__recordPassingResult(resulttype, resultname, f"Exact count met. Found: {foundcnt}", datatag=datatag)
        pass

    def validate_maximum_rowcount(self, targetobject, count, filter=None, tooling=False, continueonfail=True,
                                  datatag=None, targetruntime: str = "ALL"):
        """
        Validate that the rows for the target object and filter do not exceed the expected count
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :param targetobject: Object to lookup
        :param count: Expected maximum count
        :param filter: (Optional) SOQL Filter for the target object (e.g. MyCustomField__c = 'Example')
        :param tooling: (Optional) Set to True if the target object requires the Tooling API
        :param continueonfail: (Optional) Boolean flag to continue testing or abort
        """

        resulttype = "Data"
        resultname = f'Validate Maximum Count of {targetobject} for {count} rows'

        # Check the runtime to see if this validation should be run on the org type
        if not self.__isapplicableruntime(targetruntime):
            self.__recordIgnoredResult(resulttype, resultname,
                                       f"IGNORED::targetruntime {targetruntime} does not apply to this org",
                                       datatag=datatag)
            return

        if targetobject is None:
            self.__recordFailureResultException(resulttype, resultname, "A target object must be specified",
                                                datatag=datatag)

        if count is None:
            self.__recordFailureResultException(resulttype, resultname,
                                                "'count' must be specified. This should be the maximum number of object records you expect in the org.",
                                                datatag=datatag)

        foundcnt = self.find_record_count(targetobject, filter, tooling)

        if foundcnt > int(count):
            if continueonfail:
                self.__recordFailureResult(resulttype, resultname,
                                           f"A max count not met. Expected was: {count} and found count was {foundcnt}",
                                           datatag=datatag)
                return
            else:
                self.__recordFailureResultException(resulttype, resultname,
                                                    f"A max count not met. Expected was: {count} and found count was {foundcnt}",
                                                    datatag=datatag)

        self.__recordPassingResult(resulttype, resultname, f"Max count met. Found: {foundcnt}", datatag=datatag)
        pass

    def validate_range_rowcount(self, targetobject, lowercount, uppercount, filter=None, tooling=False,
                                continueonfail=True, datatag=None, targetruntime: str = "ALL"):
        """Validate the count of the rows for the specified object and filter is >= lower value and <= upper value
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :param targetobject: Target object you are going to lookup
        :param lowercount: Minimum number for the range you want to specify. e.g. 0 if the range is 0-10
        :param uppercount: Maximum number for the range you want to specify. e.g. 10 if the range is 0-10
        :param filter: (Optional) SOQL Filter for the target object (e.g. MyCustomField__c = 'Example')
        :param tooling: (Optional) Set to True if the target object requires the Tooling API
        :param continueonfail: (Optional) Boolean flag to continue testing or abort
        """
        resulttype = "Data"
        resultname = f'Validate Range Count of {targetobject} between {lowercount} and {uppercount} rows'

        # Check the runtime to see if this validation should be run on the org type
        if not self.__isapplicableruntime(targetruntime):
            self.__recordIgnoredResult(resulttype, resultname,
                                       f"IGNORED::targetruntime {targetruntime} does not apply to this org",
                                       datatag=datatag)
            return

        if targetobject is None:
            self.__recordFailureResultException("A target object must be specified", datatag=datatag)

        if lowercount is None:
            self.__recordFailureResultException("A lower count must be specified", datatag=datatag)

        if uppercount is None:
            self.__recordFailureResultException("As upper count must be specified", datatag=datatag)

        foundcnt = self.find_record_count(targetobject, filter, tooling)

        if not foundcnt >= int(lowercount) or not foundcnt <= int(uppercount):

            message = f"A range count not met. Expected Range was between {lowercount} and {uppercount} and the found count was {foundcnt}"

            if continueonfail:
                self.__recordFailureResult(resulttype, resultname, message, datatag=datatag)
                return
            else:
                self.__recordFailureResultException(resulttype, resultname, message, datatag=datatag)

        self.__recordPassingResult(resulttype, resultname, f"Range count met. Found: {foundcnt}", datatag=datatag)
        pass

    def find_record_count(self, targetobject, filter=None, tooling=False, targetruntime: str = "ALL", datatag=None):
        """Locate the record count for the target object and given filter
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :param targetobject: Target Object
        :param filter: (Optional) SOQL Filter for the target object (e.g. MyCustomField__c = 'Example')
        :param tooling: (Optional) Set to True if the target object requires the Tooling API
        :return: Returns record count, if records are found, otherwise returns None.
        """

        # Check the runtime to see if this validation should be run on the org type
        if not self.__isapplicableruntime(targetruntime):
            resulttype = "Data"
            resultname = f"Find record count for {targetobject}"
            self.__recordIgnoredResult(resulttype, resultname,
                                       f"IGNORED::targetruntime {targetruntime} does not apply to this org",
                                       datatag=datatag)
            return

        if targetobject is None or targetobject == "":
            raise Exception("A target object must be specified")

        # default:
        soql = f"select count(Id) DataCount from {targetobject}"

        if self.does_not_support_count(targetobject):
            soql = f"select Id from {targetobject}"

        if filter is not None:
            soql = f"{soql} where ({filter})"

        self.shared.log_to_file(f"Running::tooling::{tooling}::{soql}")

        if not tooling:
            results = self.cumulusci.sf.query_all(f"{soql}")
        else:
            toolingendpoint = 'query?q='
            results = self.cumulusci.sf.toolingexecute(f"{toolingendpoint}{soql.replace(' ', '+')}")

        # so this gets translated to a dict with 3 keys: 
        # records
        # totalSize
        # done

        # we use the totalsize instead of aggregate count
        if self.does_not_support_count(targetobject):
            return int(results["totalSize"])
        else:
            if results["totalSize"] == 1:
                return int(results["records"][0]["DataCount"])

        return None

    def does_not_support_count(self, objectname: str):

        if objectname.lower() == "standardvalueset":
            return True

        return False

    def validate_entity_contains(self, targetobjectlabel: str, layer: str, findfilter: str, continueonfail=True,
                                 datatag=None, targetruntime: str = "ALL"):

        """Allows a validation to treat metadata for the specified object as a queryable object via SQL and DataFrames
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :param targetobjectlabel: The object that metadata will be extracted via the REST api.
        :param layer: The array of data within the metadata to search against
        :param findfilter: The filter where clause to search the dataframe against.
        :param continueonfail(Optional): Boolean flag to continue testing or abort
        """

        # self.shared.log_to_file(f"Target SObject::{targetobjectlabel}")
        # self.shared.log_to_file(f"Taget Layer::{layer}")
        # self.shared.log_to_file(f"Find Filter::{findfilter}")

        resulttype = "Metadata"
        resultname = f'Validate that {targetobjectlabel} has {layer}'

        # Check the runtime to see if this validation should be run on the org type
        if not self.__isapplicableruntime(targetruntime):
            self.__recordIgnoredResult(resulttype, resultname,
                                       f"IGNORED::targetruntime {targetruntime} does not apply to this org",
                                       datatag=datatag)
            return

        sobjectset = self.cumulusci.sf.describe()["sobjects"]
        #self.shared.log_to_file(f"SOjectKeys::{sobjectset}")
        
         #default message: we did not locate the object to traverse the metadata
        message = f'Unable to locate the metadata object to locate the layer'
        
        for x in sobjectset:

            foundlabel = x["label"]
            foundname = x["name"]

            if foundlabel.lower() == targetobjectlabel.lower() or foundname.lower() == targetobjectlabel.lower():

                self.shared.log_to_file(f"Found SObject::{foundlabel}")

                targetdescribe = self.cumulusci.sf.__getattr__(targetobjectlabel).describe()

                self.shared.log_to_file(f"DescKey::{targetdescribe.keys()}")
                layerfound = False
                truelayername = None
                for key in targetdescribe.keys():
                    if key.lower() == layer.lower():
                        truelayername = key
                        layerfound = True

                if not layerfound:
                    # self.shared.log_to_file(f"Layer Not Found::{layer}")
                    break

                if truelayername is not None:

                    fields = targetdescribe[truelayername]

                    # self.shared.log_to_file(f"DataType::{type(fields)}")
                    df = pd.DataFrame(fields)

                    # convert to string- all values
                    for col in df.columns:
                        try:
                            df[col] = df[col].apply(str)
                        except Exception as e:
                            # self.shared.log_to_file(f"Dropping Col::{col}")
                            df.drop(columns=[col])

                    self.shared.log_to_file(f"DataFrame::{df.head()}")

                    try:
                        if findfilter is not None:
                            filter = f"SELECT count(*) datacount from df where {findfilter}"
                        else:
                            filter = f"SELECT count(*) datacount"

                        self.shared.log_to_file(f"SQL Filter::{filter}")
                        dfqueryres = ps.sqldf(filter)
                        self.shared.log_to_file(f"Query Result::{dfqueryres}")

                        # the dataframe will have a single row and column 
                        if dfqueryres is not None and (len(dfqueryres) == 1 and int(dfqueryres.loc[0]['datacount']) > 0):
                            self.__recordPassingResult(resulttype, resultname, f"Metadata contains the specified",
                                                       datatag=datatag)
                            return
                        else:
                            message = f'Unable to locate the metadata data for the specified object and layer and filter'
                    except Exception as exception:
                        message = f'Filter on Metadata did not locate any matching rows of data.'
                        self.shared.log_to_file(f"Data Frame Check Exception::{exception}")
                        self.shared.log_to_file("Exception: {}".format(type(exception).__name__))
                        self.shared.log_to_file("Exception message: {}".format(exception))
                        # we hit an exception - fail closed

        if continueonfail:
            self.__recordFailureResult(resulttype, resultname, message, datatag=datatag)
            return
        else:
            self.__recordFailureResultException(resulttype, resultname, message, datatag=datatag)

    def validate_with_testim(self, testimscriptname: str, continueonfail=True, datatag=None,
                             targetruntime: str = "ALL"):

        """Runs the specified Testim Script and determines if the script ran or failed.
        :param datatag:
        :param continueonfail: Defaults to True
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :param testimscriptname: Testim Script to run
        :param continueonfail(Optional): Boolean flag to continue testing or abort
        """

        resulttype = "UI-Testim"
        resultname = f'Validate via Testim Script {testimscriptname}'

        # Check the runtime to see if this validation should be run on the org type
        if not self.__isapplicableruntime(targetruntime):
            self.__recordIgnoredResult(resulttype, resultname,
                                       f"IGNORED::targetruntime {targetruntime} does not apply to this org",
                                       datatag=datatag)
            return

        # No script name no start
        if testimscriptname is None or testimscriptname == "":
            raise Exception("No Testim Script name provided.")

        # get env variables:

        testimproject = os.environ.get('TESTIM_PROJECT')
        testimgrid = "Testim-Grid"
        testimtoken = os.environ.get('TESTIM_KEY')
        self.shared.log_to_file(f"RUN_CMD Result::{json.dumps(self.cumulusci.sf.session_id)}")
        baseurl = f"{self.cumulusci.org.instance_url}/secur/frontdoor.jsp?sid={self.cumulusci.sf.session_id}"

        RUN_CMD = f"testim --token '{testimtoken}' --project '{testimproject}' --grid '{testimgrid}' --name '{testimscriptname}' --base-url '{baseurl}' --report-file {testimscriptname}_results.xml"
        self.shared.log_to_file(f"RUN_CMD Result::{RUN_CMD}")

        process = subprocess.call([f"{RUN_CMD}"], shell=True)

        # if the result file is there - peek and see if failures exist
        if os.path.isfile(f"{testimscriptname}_results.xml"):

            # Occam's razor
            resultfile = open(f"{testimscriptname}_results.xml", "r")
            resultdata = resultfile.read()
            if resultdata.__contains__("failure=\"0\" "):
                self.__recordPassingResult(resulttype, resultname,
                                           f"Testim script {testimscriptname} reported no failures.", datatag=datatag)
                return
            else:
                message = f"Testim script {testimscriptname} reported failures."

        else:
            message = f"Expected test results file {testimscriptname}_results.xml not found."

        if continueonfail:
            self.__recordFailureResult(resulttype, resultname, message, datatag=datatag)
            return
        else:
            self.__recordFailureResultException(resulttype, resultname, message, datatag=datatag)

    def find_xpath_in_xmlfile(self, sourcefile, xpathfilter):
        """
        Locates the xpath within the xml
        :param sourcefile: Source XML File
        :param xpathfilter: XPath to traverse the XML and locate nodes
        """

        if xpathfilter is None or xpathfilter == "":
            raise Exception("A xpath must be specified")

        if sourcefile is None or sourcefile == "":
            raise Exception("A source file must be specified")

        if not os.path.isfile(sourcefile):
            raise Exception("The source file does not exist")

        else:
            datafile = open(sourcefile, "r")
            xmldata = datafile.read()
            tree = etree.fromstring(bytes(xmldata, 'utf-8'))
            foundata = tree.xpath(xpathfilter)
            return foundata

        return None

    def __isapplicableruntime(self, targetruntime: str = "ALL"):
        """
        Checks Runtime is applicable for the target org
        :param targetruntime: ALL, SCRATCHONLY or PRODONLY. Defaults to ALL
        :return: True if applicable runtime
        """
        if targetruntime == "ALL":
            return True

        results = self.cumulusci.sf.query_all(f"SELECT IsSandbox FROM Organization ")

        if results["totalSize"] == 1:

            if targetruntime == "SCRATCHONLY" and bool(results["records"][0]["IsSandbox"]):
                return True

            if targetruntime == "PRODONLY" and not bool(results["records"][0]["IsSandbox"]):
                return True

        return False
