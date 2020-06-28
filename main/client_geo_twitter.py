import re
import socket
import sys
import json

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import API
from tweepy import Stream

# Tweepy API Credentials
CONSUMER_KEY = "vNQdccsU7qD8qCA5LRjZKxvNN"
CONSUMER_SECRET = "7rmevS3tbpdjMlmvXsSh0IYHW9iVF01vkIx5zi3ytGs0gBWUjg"
ACCESS_TOKEN = "942120259569496066-jUr59FJ1pz1tBOOc9PsOD33X5P9aTrV"
ACCESS_TOKEN_SECRET = "trv7xnaAs5ieWW0X0UlcbjsVQjwXXMu3dgqot8FbJ6dpB"

ON = ["ontario", "on"]
QC = ["quebec", 'qc']
AB = ["alberta", "ab"]
MB = ["manitoba", "mb"]
NS = ["nova",  "scotia", "ns"]
BC = ["british",  "columbia", "bc"]
NB = ["brunswick", "nb"]
NL = ["newfoundland",  "labrador", "nl"]
PE = ["prince",  "edward", "island", "pe"]
SASK = ["saskatchewan", "sask"]

pON = "ON"
pQC = "QC"
pAB = "AB"
pMB = "MB"
pNS = "NS"
pBC = "BC"
pNB = "NB"
pNL = "NL"
pPE = "PE"
pSASK = "SASK"

provinces = ["ontario", "on", "quebec", 'qc',"alberta", "ab", "manitoba", "mb", "nova scotia", "ns",
             "british columbia", "bc","new brunswick", "nb", "newfoundland and labrador", "nl",
             "prince edward island", "pe", "saskatchewan", "sask"]



# Listener for tweet streams
class TweetListener(StreamListener):
    def on_data(self, data):
        try:
            global conn
            full_tweet = json.loads(data)

            # Get tweet text from JSON
            tweet_text = full_tweet['text']
            tweet_location = filterLocation(full_tweet)

            # print tweet
            print("------------------------------------------")

            # Tweet cleaning
            tweet_text = cleanTweet(tweet_text)


            # send tweet to Spark
            if tweet_location:
                print(tweet_text + " [" + tweet_location + "]" + '\n')
                conn.send(str.encode(tweet_text + " [" + tweet_location + "]" +  '\n'))
        except:
            # handle errors
            e = sys.exc_info()[0]
            print("Error: %s" % e)

        return True

    def on_error(self, status):
        print(status)


def isProvince(locationTokens, provinceList):
    for element in provinceList:
        for token in locationTokens:
            if token.strip() == element.strip():
                # print("comparing: " + token + " vs. " + element)
                return True

    return False


def getProvince(location):
    # print("chosen location: " + location)
    location = location.split()
    # print(location)

    if isProvince(location, ON):
        return pON
    elif isProvince(location, ON):
        return pON
    elif isProvince(location, AB):
        return pAB
    elif isProvince(location, MB):
        return pMB
    elif isProvince(location, NS):
        return pNS
    elif isProvince(location, BC):
        return pBC
    elif isProvince(location, NB):
        return pNB
    elif isProvince(location, NL):
        return pNL
    elif isProvince(location, PE):
        return pPE
    elif isProvince(location, SASK):
        return pSASK
    else:
        return None


def filterProvince(location):
    for province in provinces:
        if province in location:
            return getProvince(location)

    return None


def filterLocation(tweet):
    tweet_location = tweet['user']['location']
    if tweet_location:
        tweet_location = re.sub(r'[^[a-zA-Z\s]+|[^[a-zA-Z\s]+$', '', tweet_location)
        tweet_location = re.sub(r'[\s]+', ' ', tweet_location)
        tweet_location = tweet_location.lower()
        # print(tweet_location)
        tweet_location = filterProvince(tweet_location)


    return tweet_location


# remove special symbols and numbers..etc.
def cleanTweet(tweet):
    tweet = re.sub(r'[^[a-zA-Z#\s]+|[^[a-zA-Z#\s]+$', '', tweet)
    tweet = re.sub(r'[\s]+', ' ', tweet)
    return tweet


# IP and port of local machine or Docker
TCP_IP = socket.gethostbyname(socket.gethostname())  # returns local IP
TCP_PORT = 9009

# setup local connection, expose socket, listen for spark app
conn = None
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)
print("Waiting for TCP connection...")

# if the connection is accepted, proceed
conn, addr = s.accept()
print("Connected... Starting getting tweets.")

# ==== setup twitter connection ====
listener = TweetListener()
auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
stream = Stream(auth, listener)

# setup search terms
track = [
        # LIBERALS
         '#liberal', '#liberals', '#lpc', '#trudeau', '#justintrudeau', 'justintrudeau', 'trudeau', 'liberal',
         'liberals', 'Liberal Party of Canada', 'Justin Trudeau'
        # CONSERVATIVES
         '#conservatives', '#conservative', '#cpc', '#scheer', '#andrewscheer', 'conservatives', 'conservative', 'cpc',
        'Andrew Scheer', 'Scheer', 'Conservative Party of Canada',
        # NDP
         '#NDP', '#newdemocraticparty', '#jagmeetsingh', '#jagmeet', 'NDP', 'new democratic party', 'jagmeet singh',
         'jagmeet']
language = ['en']

# get filtered tweets, forward them to spark until interrupted
try:
    stream.filter(track=track, languages=language)
except KeyboardInterrupt:
    s.shutdown(socket.SHUT_RD)

