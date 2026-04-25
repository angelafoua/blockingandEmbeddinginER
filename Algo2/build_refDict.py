

import re

def tokenizeInput(inputFileName, delimiter=","):
    
    # *********** Inner Function *******************************
    def tokenizerCompress(string):
        string = string.upper()
        string = string.replace(delimiter, ' ')
        tokenList = re.split(r'\s+', string)

        newList = []
        for token in tokenList:
            newToken = re.sub(r'\W+', '', token)
            if newToken:   # cleaner than len(newToken) > 0
                newList.append(newToken)
        return newList

    # *********** Outer Function *******************************
    refDict = {}

    with open(inputFileName, 'r', encoding="utf-8") as inputFile:
        
        # Skip header
        next(inputFile)

        for line in inputFile:
            line = line.strip()
            if not line:
                continue

            firstDelimiter = line.find(delimiter)
            if firstDelimiter == -1:
                continue  # skip malformed line

            refID = line[:firstDelimiter]
            body = line[firstDelimiter + 1:]

            tokenList = tokenizerCompress(body)

            refDict[refID] = tokenList

    return refDict