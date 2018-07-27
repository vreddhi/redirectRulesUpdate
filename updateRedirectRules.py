'''
Python Script to parse a csv input file containing source and destination URLComponents
and convert them to akamai PAPI specific json data. This script is limited to redirect
behavior. You can find this script in https://github.com/vreddhi/
'''

import requests, logging, json, sys
from akamai.edgegrid import EdgeGridAuth
import urllib
import json
import configparser
import csvTojsonParser
import argparse
import logging

#Program start here
parser = argparse.ArgumentParser()
parser.add_argument("-i","--interactive", help="Enter yes to pass the below arguments OR no to read it from file specified in -cf option")
parser.add_argument("-ct","--client_token", help="Enter the client_token")
parser.add_argument("-cs","--client_secret", help="Enter the client_token")
parser.add_argument("-at","--access_token", help="Enter the client_token")
parser.add_argument("-au","--access_url", help="Enter the client_token")
parser.add_argument("-pn","--property_name", help="Enter the client_token")
parser.add_argument("-v","--version", help="Enter the version")
parser.add_argument("-cf","--Config_file", help="Enter the configuration file")
args = parser.parse_args()

if args.interactive is None:
    print("\n Use --help to know the options to run this program\n")
    exit()

if args.interactive == "no":
    config = configparser.ConfigParser()
    config.read('config.txt')
    try:
        client_token = config['CREDENTIALS']['client_token']
        client_secret = config['CREDENTIALS']['client_secret']
        access_token = config['CREDENTIALS']['access_token']
        access_url = config['CREDENTIALS']['access_url']
        digitalProperty = config['PROPERTY']['property_name']
        version = config['PROPERTY']['version']
    except KeyError:
        print("\nYou have chosen interactive mode. Config Entry Or the Config file is missing\n")

elif args.interactive == "yes":
    try:
        if args.client_token is not  None:
            client_token = args.client_token
        else:
            print("Client Token is missing")
            exit()
        if args.client_secret is not None:
            client_secret = args.client_secret
        else:
            print("Client Secret is missing")
            exit()
        if args.access_token is not None:
            access_token = args.access_token
        else:
            print("Access Token is missing")
            exit()
        if args.access_url is not None:
            access_url = args.access_url
        else:
            print("Access Url is missing")
            exit()
        if args.property_name is not None:
            digitalProperty = args.property_name
        else:
            print("Digital Property Name is missing")
            exit()
        if args.version is not None:
            version = int(args.version)
        else:
            print("Version number is missing")
            exit()
    except NameError as Err:
        print("\n"+str(Err)+"\n")
        exit()

loggingFileName = digitalProperty +"_log.log"
logging.basicConfig(format='%(asctime)s %(message)s',filename=loggingFileName,filemode='w',level=logging.INFO)


class PapiObjects(object):
    session = requests.Session()
    baseUrl = 'https://' + access_url+'/papi/v0'
    propertyFound = "NOT_FOUND"
    propertyDetails = {}

    session.auth = EdgeGridAuth(
				client_token = client_token,
				client_secret = client_secret,
				access_token = access_token
                )

    header = {
        "Content-Type": "application/json"
    }

    def customPrintorLog(self,data):
        if args.interactive == "yes":
            print(str(data))
            logging.info(str(data))
        else:
            logging.info(str(data))


    def getGroup(self):
        groupUrl = self.baseUrl + '/groups/'
        groupResponse = self.session.get(groupUrl)
        return groupResponse

    def updateProperty(self,propertyId,version,propertyContractId,propertyGroupId,jsonOutputRulesData):
        updateurl = self.baseUrl + '/properties/'+ propertyId + "/versions/" + str(version) + '/rules/' + '?contractId=' + propertyContractId +'&groupId=' + propertyGroupId
        updateResponse = self.session.put(updateurl,data=jsonOutputRulesData,headers=self.header)
        self.customPrintorLog("\nupdateResponse " + updateResponse.text + "\n")
        self.customPrintorLog("\nupdateResponse " + str(updateResponse.status_code) + "\n")

    def getProperty(self,groupsInfo,version):
        dummy = {}
        groupsInfoJson = groupsInfo.json()
        groupItems = groupsInfoJson['groups']['items']
        self.customPrintorLog("Finding the property " + digitalProperty+ " under contracts and groups\n")
        for item in groupItems:
            try:
                contractId = [item['contractIds'][0]]
                groupId = [item['groupId']]
                url = self.baseUrl + '/properties/' + '?contractId=' + contractId[0] +'&groupId=' + groupId[0]
                propertiesResponse = self.session.get(url)
                if propertiesResponse.status_code == 200:
                    propertiesResponseJson = propertiesResponse.json()
                    propertiesList = propertiesResponseJson['properties']['items']
                    for propertyInfo in propertiesList:
                        propertyName = propertyInfo['propertyName']
                        propertyId = propertyInfo['propertyId']
                        propertyContractId = propertyInfo['contractId']
                        propertyGroupId = propertyInfo['groupId']
                        self.propertyDetails[propertyName] = propertyName
                        if propertyName == digitalProperty or propertyName == digitalProperty + ".xml" :
                            self.customPrintorLog("Found the DP " + digitalProperty +" under contract: "+propertyContractId[4:]+"\n")
                            self.customPrintorLog("Fetching the existing version's JSON body\n")
                            self.propertyFound = "FOUND"
                            rulesUrl = self.baseUrl + '/properties/'+propertyId+'/versions/'+str(version)+'/rules/?contractId='+propertyContractId+'&groupId='+propertyGroupId
                            rulesUrlResponse = self.session.get(rulesUrl)
                            return (rulesUrlResponse,propertyId,propertyContractId,propertyGroupId)
            except KeyError:
                pass
        if self.propertyFound == "NOT_FOUND":
            #This is executed when given property name is not found in any groups
            self.customPrintorLog("\nProperty Name entered is not found.\n")




#Invoke csv to Json parser to convert redirect input URLs to JSON format
csvObject = csvTojsonParser.optionSelector()
parentRedirectRule = csvObject.parseCSVFile()
papiObj = PapiObjects()
papiObj.customPrintorLog("Fetching all the contracts and groups\n")
groupsInfo = papiObj.getGroup()
(rulesUrlResponse,propertyId,propertyContractId,propertyGroupId) = papiObj.getProperty(groupsInfo,version)
papiObj.customPrintorLog("Updating the JSON body with new Redirect Rules\n")
rulesUrlJsonResponse = rulesUrlResponse.json()
rulesUrlJsonResponse['rules']['children'].append(parentRedirectRule)
jsonOutputRulesData = json.dumps(rulesUrlJsonResponse)
version = int(version) + 1
papiObj.updateProperty(propertyId,version,propertyContractId,propertyGroupId,jsonOutputRulesData)
