
def buildTokenFreqDict(refDict):
    
    tokenCnt = 0
    refCnt = 0
    numTokenCnt = 0
    tokenFreqDict = {}
    tokenLenDict = {}
    for key in refDict:
        refCnt +=1
        tokenList = refDict[key]
        tokenCnt = tokenCnt + len(tokenList)
        for j in range(0, len(tokenList)):
            token = tokenList[j]
            if token.isdigit():
                numTokenCnt += 1
            if token in tokenFreqDict:
                tokenFreqDict[token] += 1
            else:
                tokenFreqDict[token] = 1
            tokenLen = len(token)
            if tokenLen in tokenLenDict:
                tokenLenDict[tokenLen] += 1
            else:
                tokenLenDict[tokenLen] = 1
    
    return tokenFreqDict


