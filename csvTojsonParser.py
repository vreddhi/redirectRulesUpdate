'''
Python Script to parse a csv input file containing source and destination URLComponents
and convert them to akamai PAPI specific json data. This script is limited to redirect
behavior. You can find this script in https://github.com/vreddhi/
'''
import csv
import json
import re
import sys
import configparser


class optionSelector(object):
    sourcequeryString = "fromFile"
    sourceProtocol = "fromFile"
    sourcequeryStringNameCase = "no"
    sourcequeryStringValueCase = "no"
    sourcequeryStringNameWilCard = "no"
    sourcequeryStringValueWilCard = "no"
    sourcePathComponent = "yes"
    sourcePathCase = "no"
    sourceHostname = "fromFile"
    destinationProtocol = "fromFile"
    destinationHostname = "fromFile"
    destinationQueryString = "fromFile"
    destinationResponseCode = "301"

    def __int__(self,sourceProtocol ="fromFile",sourcequeryString = "yes",sourcequeryStringNameCase = "yes", \
                sourcequeryStringValueCase = "yes", sourcequeryStringNameWilCard = "yes", sourcequeryStringValueWilCard = "yes", \
                sourcePathComponent = "yes", sourcePathCase = "yes", sourceHostname = "yes", destinationProtocol = "fromFile", \
                destinationHostname = "fromFile", destinationQueryString = "fromFile", destinationResponseCode = "301"):
        self.sourceProtocol = sourceProtocol
        self.sourcequeryString = sourcequeryString
        self.sourcequeryStringNameCase = sourcequeryStringNameCase
        self.sourcequeryStringValueCase = sourcequeryStringValueCase
        self.sourcequeryStringNameWilCard = sourcequeryStringNameWilCard
        self.sourcequeryStringValueWilCard = sourcequeryStringValueWilCard
        self.sourcePathComponent = sourcePathComponent
        self.sourcePathCase = sourcePathCase
        self.sourceHostname = sourceHostname
        self.destinationProtocol = destinationProtocol
        self.destinationHostname = destinationHostname
        self.destinationResponseCode = destinationResponseCode

    #Function to Check for valid URL, this is the Django way to do this
    def is_valid_url(self,url):
        regex = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url is not None and regex.search(url)


    #Function to Check and populate URL componenets
    def fetchURLComponents(self,Url):
        URLComponents = {}
        urlMatch = re.match(r"(^https?)://([a-zA-Z0-9.-]*)/?([a-zA-Z0-9./-]*)\??(.*)",Url)
        if urlMatch:
            URLComponents['Protocol'] = urlMatch.group(1)
            URLComponents['Hostname'] = urlMatch.group(2)
            URLComponents['Path'] = urlMatch.group(3)
            URLComponents['Query_param'] = urlMatch.group(4)
        return(URLComponents)

#Function to Check and populate the match criterias
    def criteriaList(self,srcURLComponents,childRedirectRule):
        criteria_values = []
        criterias_list = [] #Fix to avoid Dictionary over-write of criteria values
        #Match on Request Protocol
        if self.sourceProtocol == "fromFile" or self.sourceProtocol == "HTTP" or self.sourceProtocol == "HTTPS":
            criteria = {}
            criteria['options'] = {}
            criteria['name'] = 'requestProtocol'
            if self.sourceProtocol == "fromFile" and srcURLComponents['Protocol'] and srcURLComponents['Protocol'] != '':
                criteria['options']['value'] = srcURLComponents['Protocol'].upper()
            elif self.sourceProtocol == "HTTP":
                criteria['options']['value'] = "HTTP"
            elif self.sourceProtocol == "HTTPS":
                criteria['options']['value'] = "HTTPS"
        #Match on Request Hostname
        if self.sourceHostname == "fromFile" and srcURLComponents['Hostname'] and srcURLComponents['Hostname'] != '':
            criteria = {}
            criteria['options'] = {}
            criteria['name'] = 'hostname'
            criteria['options']['values'] = srcURLComponents['Hostname'].split()
            criterias_list.append(criteria)
        #Match on Request Query Strings
        if self.sourcequeryString == "fromFile" and srcURLComponents['Query_param'] and srcURLComponents['Query_param'] != '':
            paramString = str(srcURLComponents['Query_param'])
            paramStringPair = paramString.split('&')
            for nameValuePair in paramStringPair:
                criteria = {}
                criteria['options'] = {}
                queryName = nameValuePair.split('=')[0]
                queryValue = nameValuePair.split('=')[1]
                criteria['name'] = 'queryStringParameter'
                criteria['options']['matchOperator'] = "matchOperator"
                criteria['options']['escapeValue'] = bool(False)
                criteria['options']['matchOperator'] = "IS_ONE_OF"
                criteria['options']['parameterName'] = queryName
                criteria['options']['values'] = queryValue.split()
                if self.sourcequeryStringNameCase == "yes":
                    criteria['options']['matchCaseSensitiveName'] = bool(True)
                else:
                    criteria['options']['matchCaseSensitiveName'] = bool(False)
                if self.sourcequeryStringValueCase == "yes":
                    criteria['options']['matchCaseSensitiveValue'] = bool(True)
                else:
                    criteria['options']['matchCaseSensitiveValue'] = bool(False)
                if self.sourcequeryStringNameWilCard == "yes":
                    criteria['options']['matchWildcardName'] = bool(True)
                else:
                    criteria['options']['matchWildcardName'] = bool(False)
                if self.sourcequeryStringValueWilCard == "yes":
                    criteria['options']['matchWildcardValue'] = bool(True)
                else:
                    criteria['options']['matchWildcardValue'] = bool(False)
                criterias_list.append(criteria)
        #Match on Request Path components
        if self.sourcePathComponent == "yes" and srcURLComponents['Path'] and srcURLComponents['Path'] != '':
            criteria = {}
            criteria['options'] = {}
            criteria['name'] = "path"
            criteria['options']['matchOperator'] = "MATCHES_ONE_OF"
            criteria['options']['values'] = "/"+str(srcURLComponents['Path'])
            criteria['options']['values'] = criteria['options']['values'].split()
            if self.sourcePathCase == "yes":
                criteria['options']['matchCaseSensitive'] = bool(True)
            else:
                criteria['options']['matchCaseSensitive'] = bool(False)
            criterias_list.append(criteria)
        #Build a criteria list having protocol, hostname, path and(or) query strings information
        return criterias_list


#Function to Check and populate the behavior values for Redirect
    def determineBehaviorList(self,DstURLComponents,childRedirectRule):
        behaviors_list = []
        behavior = {}
        behavior['name'] = 'redirect'
        behavior['options'] = {}
        if self.destinationProtocol == "fromFile" or self.destinationProtocol == "HTTP" or self.destinationProtocol == "HTTPS":
            if self.destinationProtocol == "fromFile" and DstURLComponents['Protocol'] and DstURLComponents['Protocol'] != '':
                behavior['options']['destinationProtocol'] = DstURLComponents['Protocol'].upper()
            elif self.destinationProtocol == "HTTP":
                behavior['options']['destinationProtocol'] = "HTTP"
            elif self.destinationProtocol == "HTTPS":
                behavior['options']['destinationProtocol'] = "HTTPS"
        if self.destinationHostname == "fromFile":
            behavior['options']['destinationHostname'] = "OTHER"
            behavior['options']['destinationHostnameOther'] = DstURLComponents['Hostname']
        elif self.destinationHostname == "SAME_AS_REQUEST":
            behavior['options']['destinationHostname'] = "SAME_AS_REQUEST"
        behavior['options']['destinationPath'] = "OTHER"
        if DstURLComponents['Path'] and DstURLComponents['Path'] != '':
            behavior['options']['destinationPathOther'] = '/'+DstURLComponents['Path']
        else:
            #There is no path component in destination URL. so send it to root
            behavior['options']['destinationPathOther'] = "/"
        behavior['options']['mobileDefaultChoice'] = "DEFAULT"
        #There is no mechanism to include new queryString in queryString endpoint of API
        #So append queryString to path itself in case destination queryString is different
        #And set the queryString API endpoint to IGNORE
        if self.destinationQueryString == "fromFile":
            behavior['options']['destinationPathOther'] = behavior['options']['destinationPathOther'] + "?" + DstURLComponents['Query_param']
            behavior['options']['queryString']= "IGNORE"
        elif self.destinationQueryString == "SAME_AS_REQUEST":
            behavior['options']['queryString']= "APPEND"
        elif self.destinationQueryString == "IGNORE":
            behavior['options']['queryString']= "IGNORE"
        behavior['options']['responseCode'] = int(self.destinationResponseCode)
        #Form a list of behaviors
        behaviors_list.append(behavior)
        return behaviors_list


#Function to parse the input file
    def parseCSVFile(self):
        try:
            config = configparser.ConfigParser()
            config.read('config.txt')
            InputFilename = config['INPUT']['input_csv_file']
        except KeyError:
            print("\nConfig Entry Or the Config file is missing\n")
            exit()

        try:
            fileHandler = open(InputFilename)
            inputFileReader = csv.reader(fileHandler)
        except FileNotFoundError:
            print("Unable to find the input file \n")
            exit()

        childRedirectRulesSet = [] #This will contain the list of redirect rules
        parentRedirectRule = {} #This is the parent rule under which redirect rules will be populated as children
        for line in inputFileReader:
            number = 1
            childRedirectRule = {}
            sourceUrl = str(line[0])
            destinationUrl = str(line[1])
            s = self.is_valid_url(sourceUrl)
            d = self.is_valid_url(destinationUrl)
            if s is not None and d is not None and sourceUrl != destinationUrl:
                SrcURLComponents = self.fetchURLComponents(sourceUrl)
                DstURLComponents = self.fetchURLComponents(destinationUrl)
                redirectName = str(number) + ". Redirect " + SrcURLComponents['Hostname'] + "+" + SrcURLComponents['Path'] + SrcURLComponents['Query_param']
                number += 1
                childRedirectRule['name'] = redirectName
                childRedirectRule['children'] = []
                #Add all the behaviors applicable
                behaviors_list = self.determineBehaviorList(DstURLComponents,childRedirectRule)
                childRedirectRule['behaviors'] = behaviors_list
                criterias_list = self.criteriaList(SrcURLComponents,childRedirectRule)
                childRedirectRule['criteria'] = criterias_list
                childRedirectRule['criteriaMustSatisfy'] = "all"
                childRedirectRulesSet.append(childRedirectRule)
            else:
                print("One or more URL is not valid in :"+ sourceUrl + "    " +destinationUrl)

        parentRedirectRule['name'] = "Automated Redirects"
        parentRedirectRule['behaviors'] = []
        parentRedirectRule['children'] = childRedirectRulesSet
        return parentRedirectRule
