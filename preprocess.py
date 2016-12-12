#!/usr/bin/python
#
# This example shows how to use the MITIE Python API to perform named entity
# recognition and also how to run a binary relation detector on top of the
# named entity recognition outputs.
#
import sys
import glob
from pprint import pprint
import os
import simplejson
import copy
import re
from nltk.stem import WordNetLemmatizer
from pycorenlp import StanfordCoreNLP
import pysolr

lemmatizer = WordNetLemmatizer()

address = '35.165.231.60:8001'
core_name = 'IRF16P4'
solr = pysolr.Solr('http://%s/solr/%s'%(address,core_name), timeout=10)

nlp = StanfordCoreNLP('http://localhost:9000')

def splitHashtags(tweet):
    hashtag = []
    for hashtags in tweet['entities']['hashtags']:
        # a = re.findall('[A-Z][^A-Z]*', hashtags['text'])
        tweet['processed_text'] = tweet['processed_text'].replace('#'+hashtags['text'],hashtags['text'])
        hashtag.append('#'+hashtags['text'])
    tweet['hashtags'] = hashtag
    return tweet

def removeUrls(tweet):
    url = []
    for urls in tweet['entities']['urls']:
        tweet['processed_text'] = tweet['processed_text'].replace(urls['url'],' ')
        url.append(urls['url'])
    tweet['urls'] = url
    return tweet

def convertMentionToName(tweet):
    mentions = []
    for mention in tweet['entities']['user_mentions']:
        tweet['processed_text'] = tweet['processed_text'].replace("@"+mention['screen_name'],mention['name'])
        mentions.append("@"+mention['screen_name'])
    tweet['mentions'] = mentions
    return tweet

def removeExtraWhiteSpaces(tweet):
    tweet['processed_text'] = ' '.join(tweet['processed_text'].replace("\t"," ").replace("\n"," ").replace("\r"," ").split())
    return tweet

def extraProcessing(tweet):
    temp = {}
    temp['text'] = tweet['text']
    temp['hashtags'] = tweet['hashtags']
    temp['mentions'] = tweet['mentions']
    temp['urls'] = tweet['urls']
    temp['username'] = tweet['user']['screen_name']
    temp['name'] = tweet['user']['name']
    temp['displaypic'] = tweet['user']['profile_image_url']
    temp['processed_text'] = tweet['processed_text']

    temp['processed_text'] = " ".join(tweet['processed_text'].split())
    return temp

def combineNER(tokens):
    ners = []
    last_token = ''
    temp = []
    for token in tokens:
        if 'ner' in token:
            if last_token != token['ner']:
                stri = ' '.join(temp)
                if stri != '':
                    if [stri,last_token] not in ners and last_token != 'O':
                        ners.append(stri+" [["+last_token+"]]")
                last_token = token['ner']
                temp = []
            temp.append(token['originalText'])
    return ners


def getEntities(response):
    # print simplejson.dumps(response)

    ners = []
    relations = []
    sentiment = []
    for sent in response['sentences']:
        result = [sent["openie"] for item in sent]
        # print(result)
        for i in result:
            for rel in i:
                relationSent=rel['subject'] + " " + rel['relation'] + " " + rel['object']
                # print(relationSent)
                relations.append(relationSent)
        ners.extend(combineNER(sent['tokens']))
        sentiment.append(sent['sentiment'])

    return ners,relations,sentiment

def removeUnencodedObjects(text):
    return str(re.sub(r'[\x80-\xff]+', " ", text.encode("utf8")))


def preprocess(tweet):

    tweet['processed_text'] = copy.copy(tweet['text'])
    tweet = convertMentionToName(tweet)
    tweet = removeUrls(tweet)
    tweet = splitHashtags(tweet)
    tweet['processed_text'] = removeUnencodedObjects(tweet['processed_text'])
    tweet = removeExtraWhiteSpaces(tweet)
    tweet = extraProcessing(tweet)

    response = nlp.annotate(tweet['processed_text'], properties={'annotators': 'tokenize,ssplit,pos,depparse,parse,ner,openie,sentiment', 'outputFormat': 'json'})
    tweet['ners'],tweet['relations'],tweet['sentiment'] = getEntities(response)

    tweet['relations'] = list(set(tweet['relations']))

    tweet['relations'] = ' : '.join(tweet['relations'])


    # exit(0)

    return tweet


def main():
    counter = 0
    tweet_list = []
    tweet_file = [simplejson.loads(i) for i in open("../Data/all-tweets-1.txt").read().split("\n")[:-1]]
    # new_tweet_file = open("processed-tweets.json","r+")
    # new_tweet_file.seek(0,2)
    for tweet in tweet_file:
        tweet = preprocess(tweet)
        tweet_list.append(tweet)
        if len(tweet_list) % 100 == 0:
            counter += 1
            solr.add(tweet_list)
            tweet_list = []
            print "Tweets uploaded ", counter*100
        # counter += 1
        # if counter % 1000 == 0:
        #     print counter
        # new_tweet_file.write(simplejson.dumps(tweet)+"\n")

if __name__ == "__main__":
    main()