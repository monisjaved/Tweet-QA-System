#!/usr/bin/python

__author___ = "Monis Javed"
__version__ = "1.0.0"
__email__ = "monis.javed@gmail.com"

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

address = ''
core_name = ''
solr = pysolr.Solr('http://%s/solr/%s'%(address,core_name), timeout=10)

nlp = StanfordCoreNLP('http://localhost:9000')

def splitHashtags(tweet):
    '''convert hashtags to words for nlp
    params tweet: tweet dict
    output modified tweet dict with hashtags array'''
    hashtag = []
    for hashtags in tweet['entities']['hashtags']:
        # to split hashtags on capital letters
        # a = re.findall('[A-Z][^A-Z]*', hashtags['text'])
        tweet['processed_text'] = tweet['processed_text'].replace('#'+hashtags['text'],hashtags['text'])
        hashtag.append('#'+hashtags['text'])
    tweet['hashtags'] = hashtag
    return tweet

def removeUrls(tweet):
    '''remove urls from tweet text for nlp
    params tweet: tweet dict
    output modified tweet dict with urls array'''
    url = []
    for urls in tweet['entities']['urls']:
        # remove all urls with blank space
        tweet['processed_text'] = tweet['processed_text'].replace(urls['url'],' ')
        url.append(urls['url'])
    tweet['urls'] = url
    return tweet

def convertMentionToName(tweet):
    '''convert user mention to screen name for named entity recognition
    params tweet: tweet dict
    output modified tweet dict with mentions array'''
    mentions = []
    for mention in tweet['entities']['user_mentions']:
        # replace mention with screen name
        tweet['processed_text'] = tweet['processed_text'].replace("@"+mention['screen_name'],mention['name'])
        mentions.append("@"+mention['screen_name'])
    tweet['mentions'] = mentions
    return tweet

def removeExtraWhiteSpaces(tweet):
    '''remove unnecessary whitespaces
    params tweet: tweet dict
    output modified tweet dict'''
    tweet['processed_text'] = ' '.join(tweet['processed_text'].replace("\t"," ").replace("\n"," ").replace("\r"," ").split())
    return tweet

def extraProcessing(tweet):
    '''process tweet for nlp
    params tweet: tweet dict
    output modified tweet dict with various fields'''

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
    '''combine ners consecutive similar named entites recieved from 
        corenlp to create a single named entity
        params tokens: tokens array recieved from corenlp
        output named entites array'''
    ners = []
    last_token = ''
    temp = []
    for token in tokens:
        if 'ner' in token:
            # if different entity then combine last entity and make new entity for combination
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
    '''get entites from corenlp and convert to usable format of 
        subject relation object to be stored in solr
        also retrieve named entites and sentiments
        params response: response array from corenlp [openie]
        output named entites
                relations
                sentiment'''

    ners = []
    relations = []
    sentiment = []
    for sent in response['sentences']:
        result = [sent["openie"] for item in sent]
        for i in result:
            for rel in i:
                # convert relations to usable format
                relationSent=rel['subject'] + " " + rel['relation'] + " " + rel['object']
                relations.append(relationSent)
        # get named entities for the sentence
        ners.extend(combineNER(sent['tokens']))
        # get sentiments for the sentence
        sentiment.append(sent['sentiment'])

    return ners,relations,sentiment

def removeUnencodedObjects(text):
    '''remove hex characters which are unreadable
    params text: text string
    output cleaned text string'''
    return str(re.sub(r'[\x80-\xff]+', " ", text.encode("utf8")))


def preprocess(tweet):
    '''preprocess function to clean tweet and add all fields used for processing
    params tweet: tweet dict
    output modified tweet dict with all fields'''

    # create processed text field for all changes
    tweet['processed_text'] = copy.copy(tweet['text'])
    # convert mentions 
    tweet = convertMentionToName(tweet)
    # remove urls from text
    tweet = removeUrls(tweet)
    # split hashtgas
    tweet = splitHashtags(tweet)
    # remove hex characters
    tweet['processed_text'] = removeUnencodedObjects(tweet['processed_text'])
    # normalize white spaces
    tweet = removeExtraWhiteSpaces(tweet)
    # set tweet for usage
    tweet = extraProcessing(tweet)

    # get named entites, relations and sentiment for the tweet
    response = nlp.annotate(tweet['processed_text'], properties={'annotators': 'tokenize,ssplit,pos,depparse,parse,ner,openie,sentiment', 'outputFormat': 'json'})
    tweet['ners'],tweet['relations'],tweet['sentiment'] = getEntities(response)

    tweet['relations'] = list(set(tweet['relations']))

    # store relations as a single string sepeared by :
    tweet['relations'] = ' : '.join(tweet['relations'])

    return tweet


def main():
    counter = 0
    tweet_list = []
    tweet_file = [simplejson.loads(i) for i in open("../Data/all-tweets-1.txt").read().split("\n")[:-1]]
    for tweet in tweet_file:
        tweet = preprocess(tweet)
        tweet_list.append(tweet)
        if len(tweet_list) % 100 == 0:
            counter += 1
            solr.add(tweet_list)
            tweet_list = []
            print "Tweets uploaded ", counter*100

if __name__ == "__main__":
    main()