#!flask/bin/python

__author___ = "Monis Javed"
__version__ = "1.0.0"
__email__ = "monis.javed@gmail.com"

from flask import Flask
from flask import request
from flask import jsonify
import requests
import simplejson
import json
from functools import wraps
from flask import redirect, request, current_app
from nltk.corpus import stopwords
from nltk import pos_tag
from nltk import word_tokenize
from simpleQueryAnswering import *

def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f().data) + ')'
            return current_app.response_class(content, mimetype='application/json')
        else:
            return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)

# create autocomplete array 
autocomplete_file = []
for i in open("autocomplete.txt").read().split("\n"):
	try:
		i = i.encode("utf8")
		autocomplete_file.append(i)
	except:
		pass

# use logging to log queries
logger = open("logger.txt","r+")
logger.seek(0,2)

@app.route('/')
def index():
	'''test endpoint'''
    return "Hello, World!"

@app.route('/getAutoComplete',methods=['GET'])
@support_jsonp
def getAutoComplete():
	'''function to provide autocomplete output to frontend'''
	global autocomplete_file

	return jsonify({'matches':autocomplete_file})

@app.route('/getResults',methods=['GET','POST'])
@support_jsonp
def getResults():
	'''get results for query recieved from frontend
	params query: user query
	output json with answer, tweets, sentiments, hashtags and words frequency'''

	# get query
	query = request.args.get("query")[1:-1]

	# log query
	logger.write("%s %s\n"%(query,request.remote_addr))
	logger.flush()
	
	# get question as word tokens
	qwords = word_tokenize(query)

	# get pos tags for query
	postags = pos_tag(qwords)
	postags = {i[0].lower():i[1] for i in postags}

	postagsAns = {}
	hashtags = {}
	senti = {}
	words = {}
	answer = ''

	# get repsonse for the question
	resp_dict = getResponse(query)

	# if not success then return error message
	if resp_dict['status'] != 'success':
		return jsonify(resp_dict)

	# if answer then bold answer text in tweets
	if 'answer' in resp_dict:
		answer = resp_dict['answer']
		awords = word_tokenize(answer)
		postagsAns = pos_tag(awords)
		postagsAns = {i[0].lower():i[1] for i in postagsAns}

	for tweet in resp_dict['tweets']:
		# create sentiment dict for sentiment pie chart
		for sent in tweet['sentiment']:
			if sent not in senti:
				senti[sent] = 0
			senti[sent] += 1

		# create hashtags array for hashtag line chart
		if 'hashtags' in tweet:
			for hasht in tweet['hashtags']:
				if hasht not in hashtags:
					hashtags[hasht] = 0
				hashtags[hasht] += 1
		# get words with frequencies for word cloud
		for word in tweet['text'].replace("\n"," ").replace("\t"," ").replace("\r"," ").split():
			word1 = word.lower().replace("#","")
			if word1 not in hashtags.keys():
				if word1 not in words:
					words[word1] = 0
				words[word1] += 1
			# bold text
			if word1 in postags and ('JJ' in postags[word1] or 'NN' in postags[word1]):
				tweet['text'] = tweet['text'].replace(" " + word + " "," <b>%s</b> "%word)
			if word1 in postagsAns and ('JJ' in postagsAns[word1] or 'NN' in postagsAns[word1]):
				tweet['text'] = tweet['text'].replace(" " + word + " "," <b>%s</b> "%word)

	labels_hashtags = []
	count_hashtags = []

	for hasht in hashtags:
		labels_hashtags.append(hasht)
		count_hashtags.append(hashtags[hasht])

	labels_sentiment = []
	count_sentiment = []

	for sent in senti:
		labels_sentiment.append(sent)
		count_sentiment.append(senti[sent])

	word = [{'text':i, 'weight':j} for i,j in words.iteritems()]
	
	return jsonify({'answer':answer, 'tweets':resp_dict['tweets'],'tweet_count':len(resp_dict['tweets']),
					'hashtags':{'labels':labels_hashtags, 'count':count_hashtags},
					'sentiment':{'labels':labels_sentiment, 'count':count_sentiment},
					'wordcloud':word, 'status':resp_dict['status']})



if __name__ == '__main__':
    while True:
        try:
            app.run(port=8888, host='0.0.0.0', threaded=True)
        except:
            pass
