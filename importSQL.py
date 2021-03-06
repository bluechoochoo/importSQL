#!/usr/bin/env python

import MySQLdb as mdb
from optparse import OptionParser
import json
import urllib2
import urllib
import sys


def getRequiredConfigData(options,configData, configName):
	if options.__dict__[configName] is None:
		if configData[configName] is None:
			print "Missing required option: " + configName
			print "This option needs to be in a config file, or supplied on the commandline"
			sys.exit(1)
	else:
		configData[configName] = options.__dict__[configName]

def getOptionalConfigData(options, configData, configName, default):
	if options.__dict__[configName] is None:
		configData[configName] = default
	else:
		configData[configName] = options.__dict__[configName]


def getConfigOptions(options, configData): 

	# Get required config data
	getRequiredConfigData(options, configData, "sourceUUID")
	getRequiredConfigData(options, configData, "table")
	getRequiredConfigData(options, configData, "database")

	getRequiredConfigData(options, configData, "ioUserID")
	getRequiredConfigData(options, configData, "ioAPIKey")
	getRequiredConfigData(options, configData, "inputUrl")

	# Grab optional configuration parameters, use defaults if they don't exist
	getOptionalConfigData(options, configData, "host", "localhost")
	getOptionalConfigData(options, configData, "port", 3306)
	getOptionalConfigData(options, configData, "username", "root")
	getOptionalConfigData(options, configData, "password", "root")

	return configData

# Grab the data from import.io
def importRESTQuery(sourceUUID, inputUrl, ioUserID, ioAPIKey):
	urlParams = urllib.urlencode({"input/webpage/url": inputUrl, "_user": ioUserID, "_apikey": ioAPIKey})
	url = 'http://api.import.io/store/data/' + sourceUUID + '/_query?' + urlParams

	response = urllib2.urlopen(url).read()
	return json.loads(response)["results"];

# Convert the data to a reasonable format and stick it in SQL
def pushToSQL(configData, results):

	fieldMappings = configData["mapping"]

	if fieldMappings is None:
		print "Using default mapping from import.io data, assuming the field names are identical to the SQL field names"
	else:
		sqlFieldMapping = [];

		for mapping in fieldMappings:
			sqlFieldMapping.append(fieldMappings[mapping])

		sqlFieldMappingString = ", ".join(sqlFieldMapping)
		print sqlFieldMappingString

		print "Mappings: %s" % fieldMappings

	

	try:
		con = mdb.connect(configData["host"], configData["username"], configData["password"], configData["database"]);
		cur = con.cursor()

		for result in results:

			values = []

			if(fieldMappings is not None):
				# Get the values for each row based on the mapping that we supplied in config.json
				for mapping in fieldMappings:
					if result[mapping] is not None:
						values.append("'"+result[mapping]+"'")
			else:
				# Get the values from the import.io source (assume the field names are identical)
				sqlFieldMapping = [];
				for key in result:
					sqlFieldMapping.append(key)
					values.append("'"+result[key]+"'")
				sqlFieldMappingString = ", ".join(sqlFieldMapping)


			sqlFieldValuesString = ", ".join(values)
			print "row data: %s" % sqlFieldValuesString

		   	queryString = "INSERT INTO " + configData["table"] + " (" + sqlFieldMappingString + ") VALUES("+sqlFieldValuesString+");"

			cur.execute(queryString)
			con.commit()

		cur.close()

	except mdb.Error, e:
	  	con.rollback()
		print "Error %d: %s" % (e.args[0],e.args[1])
		con.close()
		sys.exit(1)

def doImport(configData):
	results = importRESTQuery(configData["sourceUUID"], configData["inputUrl"], configData["ioUserID"], configData["ioAPIKey"]);
	print "Recieved %d rows of data" % (len(results))
	pushToSQL(configData, results)

parser = OptionParser()

# Get the config options from the commandline

# Import.io setup info
parser.add_option("-u", "--iouserid", dest="ioUserID", help="Your import.io user ID")
parser.add_option("-p", "--ioapikey", dest="ioAPIKey", help="Your import.io API key")
parser.add_option("-i", "--input", dest="inputUrl", help="The input url for the extractor")
parser.add_option("-s", "--sourceUUID", dest="sourceUUID", help="The data source you wish to grab data from and put it in a table")

# MySQL setup info
parser.add_option("-U", "--username", dest="username", help="Your mysql username")
parser.add_option("-P", "--password", dest="password", help="Your mysql password")
parser.add_option("-t", "--table", dest="table", help="The name of the table you wish to import the data into")
parser.add_option("-d", "--database", dest="database", help="The name fo the mysql database that you wish to import your data into")
parser.add_option("-H", "--host", dest="host", help="The mysql host")
parser.add_option("-E", "--port", dest="port", help="The mysql port")

(options, args) = parser.parse_args()

configData = {}
configData["username"] = options.username;
configData["password"] = options.password;
configData["ioUserID"] = options.ioUserID;
configData["ioAPIKey"] = options.ioAPIKey;

# Check if we have a config file: If we do, USE IT
try:
	configDataFile=open('config.json')
	configData = json.load(configDataFile)
	configDataFile.close()
	print "CONFIG FOUND, YAY!"
except IOError:
	print 'NO CONFIG FILE FOUND, going to use defaults', 'config.json'
	

#Do the call to import and push it out to the sql database in the configuration file
configData = getConfigOptions(options, configData)
doImport(configData)



