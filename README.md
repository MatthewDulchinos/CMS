# CMS

System requirements:
Running on: Python 3.11.9 (Other versions of python 3.x probably work as well, but it was tested on 3.11.9)
Required packages: flask, langchain_openai, openpyxl, sqlite3, argparse, os, pandas, pickle, mlxtend  

Background:  
This project is based off medical codes from the below link. These codes are used to be able tag key   
https://www.cms.gov/medicare/regulations-guidance/physician-self-referral/list-cpt/hcpcs-codes  

To run:  
python main.py  
  
optional flags:  
--debug runs in debug mode   
--recreateDb  recreates the database before starting  
--recreateAssociation  recreates the relationships before starting  
  
Features:  
This project demonstrates a basic API that you can use to look up descriptions of codes, search for codes based off key phrases, and ask chatGPT what a code means.  

In the future I would like to expand upon my relationship api so that it uses actual data and the odds that you are interested in a specific other code is easily modified as part of the API call, so you can elect to only get surefire matches, or more unlikely matches  
  
Database:
This program will create a database that contains all of the codes provided from https://www.cms.gov/apps/ama/license.asp?file=/files/zip/list-codes-effective-january-1-2024-published-november-29-2023.zip  
  
You can create a database using a different list code (i.e. a previous or future year) by downloading the file, renaming the excel file code_list.xlsx and placing it in the codes folder (replacing the current codes/code_list.xlsx file) Make sure you run --recreateDb to recreate the database after changing the file.  

You can create a different relationship system by replacing /codes/transactions.csv. Make sure you run --recreateAssociation to recreate the relationships after you change the file.  
  
APIs:  
  
GET /code/{id}:  
	path parameters:  
		id = the identify code  
	example: http://127.0.0.1:5000/code/Q9982  
	example response:  
		[  
			{  
    			"code": "Q9982",  
    			"description": "Flutemetamol f18 diagnostic"  
			}  
		]  
	Functionality: fetches the description for a given code, returns 404 if the code isnt in the database. If you only include part of a code, you will get all the matching codes (try "Q9" to see this)  
  
GET /search:  
	Query parameters:   
		phrase = the keyword or keywords that you want to search for a code with. Seperate keywords with spaces  
	example: http://127.0.0.1:5000/search?phrase=colonography  
	example response:   
		[  
		    {  
		        "code": "74261",  
		        "description": "Ct colonography dx"  
		    },  
		    {  
		        "code": "74262",  
		        "description": "Ct colonography dx w/dye"  
		    }  
		]  
	Functionality: searches the database for keyword(s) and returns any matches or a 404 if nothing is found  
  
GET /info/{id}:  
	path parameters:  
		id = the identify code  
	Query parameters: 
		OPEN_API_KEY = an open api secret key (Get one from here assuming you have a chatGPT account: https://platform.openai.com/account/api-keys)  
	example: http://127.0.0.1:5000/info/Q9982?OPEN_API_KEY=ff-ffffffffffffffff  
	example response:   
		content='The HCPCS code Q9982 and description "Flutemetamol f18 diagnostic" refer to a specific diagnostic radiopharmaceutical used in imaging studies, particularly in PET scans to detect beta-amyloid plaques in the brain. This procedure is commonly used in the diagnosis of Alzheimer\'s disease and other neurodegenerative disorders.'
	Functionality: Asks chatGPT for a defintion of a particular code. This obviously is not perfect, works as an easy search to understand abreviations. (obviously passing a secret key over the internet is not ideal, but it works for local stuff)  
  
GET /relationship/  
	Query parameters:  
		codes = the code or codes that you want to search for a code with. Seperate code(s) with spaces  
	example: http://127.0.0.1:5000/relationship?codes=86950  
	example response:  
		[  
    		"86930",  
    		"86931"  
		]  
	Functionality: This is a demo of how we could use market basket analysis (https://towardsdatascience.com/a-gentle-introduction-on-market-basket-analysis-association-rules-fa4b986a40ce) to recommend potential matches of codes. This current implementation uses fictional data for just the codes: [86930,86931,86950,71046,71100] so if you try to use a differnt code, it will error out. In the future however, this could be replaced with actual data to be able to predict this.