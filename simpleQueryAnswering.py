import sys
import numpy
from corenlp import *
import nltk
import nltk.data
import collections
import json
from bs4 import BeautifulSoup
import requests


link = "http://localhost:8001/solr/IRF16P4/select?defType=dismax&q=%s&qf=relations^2.5 processed_text&wt=json&rows=10"


return_dict = {}

sent_detector = nltk.data.load("tokenizers/punkt/english.pickle")

# Hardcoded word lists
yesnowords = ["can", "could", "would", "is", "does", "has", "was", "were", "had", "have", "did", "are", "will"]
commonwords = ["the", "a", "an", "is", "are", "were", "."]
questionwords = ["who", "what", "where", "when", "why", "how", "whose", "which", "whom"]

# Take in a tokenized question and return the question type and body
def processquestion(qwords):
    
    # Find "question word" (what, who, where, etc.)
    questionword = ""
    qidx = -1

    for (idx, word) in enumerate(qwords):
        if word.lower() in questionwords:
            questionword = word.lower()
            qidx = idx
            break
        elif word.lower() in yesnowords:
            return ("YESNO", qwords)

    if qidx < 0:
        return ("MISC", qwords)

    if qidx > len(qwords) - 3:
        target = qwords[:qidx]
    else:
        target = qwords[qidx+1:]
    type = "MISC"

    # Determine question type
    if questionword in ["who", "whose", "whom"]:
        type = "PERSON"
    elif questionword == "where":
        type = "PLACE"
    elif questionword == "when":
        type = "TIME"
    elif questionword == "how":
        if target[0] in ["few", "little", "much", "many"]:
            type = "NUMBER"
            target = target[1:]
        elif target[0] in ["young", "old", "long"]:
            type = "TIME"
            target = target[1:]

    # Trim possible extra helper verb
    if questionword == "which":
        target = target[1:]
    if target[0] in yesnowords:
        target = target[1:]
    
    # Return question data
    return (type, target)


def getResponse(question):
    # Iterate through all questions
    for question in [question]:

        # Answer not yet found
        done = False

        # Tokenize question
        print question
        qwords = nltk.word_tokenize(question.replace('?', ''))
        questionPOS = nltk.pos_tag(qwords)

        # Process question
        (type, target) = processquestion(qwords)


        # Get sentence keywords
        searchwords = set(target).difference(commonwords)
        print searchwords,type,target
        dict = collections.Counter()

        req = requests.get(link % " ".join(searchwords))

        if req.status_code != 200:
            return {'status':'fail', 'error':'Couldnt establish connection to db'}

        if type == "YESNO":
            return {'status':'success', 'tweets':data['response']['docs']}

        data = req.json()

        counter = 0 
        pos = {}

        for result in data['response']['docs']:
            if 'relations' in result:
                for rels in result['relations'].lower().split(" : "):
                    words = nltk.word_tokenize(rels)
                    wordmatches = set(filter(set(searchwords).__contains__, words))
                    dict[rels] = len(wordmatches)
                    pos[rels] = counter
            counter += 1
         
        # Focus on 10 most relevant sentences
        for (sentence, matches) in dict.most_common(10):
            # print sentence
            # print matches
            # parse = json.loads(corenlp.parse(sentence))
            sentencePOS = nltk.pos_tag(nltk.word_tokenize(sentence))

            # Attempt to find matching substrings
            searchstring = ' '.join(target)
            if searchstring in sentence:
                startidx = sentence.index(target[0])
                endidx = sentence.index(target[-1])
                answer = sentence[:startidx]
                print answer
                return {'status':'success', 'tweets':data['response']['docs'], 'answer':answer}
        
        #     # Check if solution is found

            # Check by question type
            answer = ""
            for sent,index in pos.iteritems():
                if 'ners' in data['response']['docs'][index]:
                    for ner in data['response']['docs'][index]['ners']:
                        NamedEntityTag = ner.split("[[")[1].split("]]")[0]
                        if type == NamedEntityTag:
                            answer = ner.split(" [[")[0]
                            done = True
                        elif done:
                            break
                
        if done:
            return {'status':'success', 'tweets':data['response']['docs'], 'answer':answer}
        else:
            return {'status':'success', 'tweets':data['response']['docs']}

if __name__ == "__main__":
    print getResponse('who was worst affected by demonetisation ?')