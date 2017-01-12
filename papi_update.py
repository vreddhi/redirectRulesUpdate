import requests, logging, json, sys
from akamai.edgegrid import EdgeGridAuth
import urllib
import json
import configparser
import csvTojsonParser

config = configparser.ConfigParser()
config.read('config.txt')
client_token = config['CREDENTIALS']['client_token']
client_secret = config['CREDENTIALS']['client_secret']
access_token = config['CREDENTIALS']['access_token']
access_url = config['CREDENTIALS']['access_url']
digitalProperty = config['PROPERTY']['property_name']

output_file = open('ConfigOutput_file.json','w')

if digitalProperty == "":
    print("You need to specify the exact property in configuration file\n\n")
    exit()

#Invoke csv to Json parser to convert redirect input URLs to JSON format
csvTojsonParser.parseCSVFile()

class PapiObjects(object):
    session = requests.Session()
    baseUrl = access_url+'/papi/v0'
    propertyFound = "NOT_FOUND"
    propertyDetails = {}

    session.auth = EdgeGridAuth(
				client_token = client_token,
				client_secret = client_secret,
				access_token = access_token
                )

    def getContracts(self):
        contractUrl = self.baseUrl + '/contracts'
        contractResponse = self.session.get(contractUrl)

    def getGroup(self):
        groupUrl = self.baseUrl + '/groups/'
        groupResponse = self.session.get(groupUrl)
        #print("groupResponse: " + groupResponse.text)
        return groupResponse

    def getProperties(self,groupsInfo):
        dummy = {}
        groupsInfoJson = groupsInfo.json()
        groupItems = groupsInfoJson['groups']['items']
        print("Finding the property " + digitalProperty+ " under contracts and groups\n")
        for item in groupItems:
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
                    if propertyName == digitalProperty :
                        print("Found the DP under contract: "+propertyContractId+"\n")
                        print("Fetching the existing version's JSON body\n")
                        self.propertyFound = "FOUND"
                        rulesUrl = self.baseUrl + '/properties/'+propertyId+'/versions/1/rules/?contractId='+propertyContractId+'&groupId='+propertyGroupId
                        rulesUrlResponse = self.session.get(rulesUrl)
                        rulesUrlJsonResponse = rulesUrlResponse.json()
                        print("Updating the JSON body with new Redirect Rules\n")
                        for eachRule in csvTojsonParser.jsonList:
                            rulesUrlJsonResponse['rules']['children'].append(eachRule)
                        jsonOutputFormat = json.dumps(rulesUrlJsonResponse)
                        output_file.write(jsonOutputFormat)
        if self.propertyFound == "NOT_FOUND":
            #This is executed when given property name is not found in any groups
            print("\nProperty Name entered is not found. Following are the list of property Names in this contract:\n")
            serial_number=1
            for name in self.propertyDetails:
                print(str(serial_number) + ". "+name)
                serial_number+=1
        else:
            #This is executed when propertyName matches one of the properties in contract
            print("\nComplete JSON data with redirect rules updated is saved in ConfigOutput_file.json. \n")


papiObj = PapiObjects()
papiObj.getContracts()
print("Fetching all the contracts and groups\n")
groupsInfo = papiObj.getGroup()
papiObj.getProperties(groupsInfo)
