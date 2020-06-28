import json

from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import Row, SQLContext
import pyspark
import sys
import requests
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA

sia = SIA()

# list of hashtags
searched_keywords = [
        # LIBERALS
         '#liberal', '#liberals', '#lpc', '#trudeau', '#justintrudeau', 'justintrudeau', 'trudeau', 'liberal',
         'liberals', 'liberal party of canada', 'justin trudeau'
        # CONSERVATIVES
         '#conservatives', '#conservative', '#cpc', '#scheer', '#andrewscheer', 'conservatives', 'conservative', 'cpc',
        'andrew scheer', 'scheer', 'conservative party of canada',
        # NDP
         '#ndp', '#newdemocraticparty', '#jagmeetsingh', '#jagmeet', 'ndp', 'new democratic party', 'jagmeet singh',
         'jagmeet']

LIBERALS = "Liberals"
CONSERVATIVES = "Conservatives"
NDP = "NDP"

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

listOfProvinces = [pON,pQC, pAB, pMB, pNS, pBC, pNB, pNL, pPE, pSASK]

# create spark configuration
conf = SparkConf()
conf.setAppName("Political Twitter Sentiment Analysis")

# create spark context with the above configuration
sc = SparkContext(conf=conf)
sc.setLogLevel("ERROR")

# create the Streaming Context from spark context, interval size 2 seconds
ssc = StreamingContext(sc, 2)

# setting a checkpoint for RDD recovery (necessary for updateStateByKey)
ssc.checkpoint("checkpoint_TwitterApp")

# read data from port 9009
dataStream = ssc.socketTextStream("twitter", 9009)

# decide whether tweet will be chosen or not
def chooseTweet(tweet):
    for keyword in searched_keywords:
        if keyword in tweet:
            return True

    return False


def getLocation(tweet):
    # 1st split:  will be split into two. ["tweet", "location]"]. so take element 1
    # 2nd split: will be split into two. [location, ""], so take element 0
    return (((tweet.split("["))[1]).split("]")[0])


def getTopic(goodTweet):
    tweet_location = getLocation(goodTweet)
    goodTweetTokens = goodTweet.lower().split()
    for keyword in searched_keywords:
        if keyword in goodTweetTokens:
            tagIndex = searched_keywords.index(keyword)

            if tagIndex < 11:
                return tweet_location + "_" + LIBERALS
            elif tagIndex < 21:
                return tweet_location + "_" + CONSERVATIVES
            else :
                return tweet_location + "_" + NDP


def sentimentAnalysis(goodTweet):
    scores = sia.polarity_scores(goodTweet)
    compound_score = scores['compound']

    if compound_score > 0.2:
        return (1, 1)
    elif compound_score < - 0.1:
        return (-1, 1)
    else:
        return (0, 1)


# get good tweets that have our keywords
goodTweet = dataStream.filter(lambda tweet: chooseTweet(tweet.lower().split()))

# map as follows: ON_LIBERAL --> (-1, 1)
sentimentCount = goodTweet.map(lambda tweet: (getTopic(tweet), sentimentAnalysis(tweet.lower())))


# adding the (sentiment, count) of each topic to its last (sentiment, count)
def aggregate_tags_count(new_values, prev_values):
    sentimentValue = sum(valueTuple[0] for valueTuple in new_values) + (prev_values[0] if prev_values else 0)
    totalCount     = sum(valueTuple[1] for valueTuple in new_values) + (prev_values[1] if prev_values else 0)

    return (sentimentValue, totalCount)


# do the aggregation, note that now this is a sequence of RDDs
sentiment_totals = sentimentCount.updateStateByKey(aggregate_tags_count)


def get_sql_context_instance(spark_context):
    if ('sqlContextSingletonInstance' not in globals()):
        globals()['sqlContextSingletonInstance'] = SQLContext(spark_context)
    return globals()['sqlContextSingletonInstance']


def process_rdd(time, rdd):
    print("----------- %s -----------" % str(time))
    try:
        # if rdd is empty, then exit. The main reason behind exiting is
        # to avoid getting ValueError Exception, which will be printed since we are
        # catching all exception and printing them
        if rdd.isEmpty():
            return

        print("processing")
        # Get spark sql singleton context from the current context
        sql_context = get_sql_context_instance(rdd.context)

        # convert the RDD to Row RDD
        row_rdd = rdd.map(lambda w: Row(topic=w[0], sentiment=w[1][0] / w[1][1]))

        # create a DF from the Row RDD
        sentiment_df = sql_context.createDataFrame(row_rdd)

        # Register the dataframe as table
        sentiment_df.registerTempTable("topics")

        # get the country sentiments from the table using SQL and print them
        sentiment_counts_df = sql_context.sql("select topic, sentiment from topics order by topic asc")
        # ON_df = sql_context.sql("SELECT topic, sentiment from topics WHERE (sentiment = (SELECT MAX(sentiment) from topics)) AND (topic LIKE \'ON_%\')")
        # ON_df = sql_context.sql("SELECT topic, sentiment from topics WHERE topic = \'" +
        #                                    pON + "_" + CONSERVATIVES + "\'")
        sentiment_counts_df.show()
        # ON_df.show()

        # call this method to prepare top 10 hashtags DF and send them
        send_df_to_dashboard(sentiment_counts_df, sql_context)
    except:
        e = sys.exc_info()[0]
    # print("Error: %s" % e)


def send_df_to_dashboard(df, sql_context):
    print("sending to dashboard")
    provinceDict = {}

    for province in listOfProvinces:
        pconservatives_df = sql_context.sql("SELECT topic, sentiment from topics WHERE topic = \'" +
                                           province + "_" + CONSERVATIVES + "\'")

        pliberals_df = sql_context.sql("SELECT topic, sentiment from topics WHERE topic = \'" +
                                           province + "_" + LIBERALS + "\'")

        pNDP_df = sql_context.sql("SELECT topic, sentiment from topics WHERE topic = \'" +
                                       province + "_" + NDP + "\'")

        sentimentConservatives = [str(s.sentiment) for s in pconservatives_df.select("sentiment").collect()]
        sentimentLiberals      = [str(s.sentiment) for s in pliberals_df.select("sentiment").collect()]
        sentimentNDP           = [str(s.sentiment) for s in pNDP_df.select("sentiment").collect()]

        conservativeData = sentimentConservatives[0] if len(sentimentConservatives) > 0 else "0.0"
        liberalData = sentimentLiberals[0] if len(sentimentLiberals) > 0 else "0.0"
        ndpData = sentimentNDP[0] if len(sentimentNDP) > 0 else "0.0"

        partyProvinceDict = {CONSERVATIVES: conservativeData, LIBERALS: liberalData, NDP: ndpData}

        provinceDict[province] = partyProvinceDict



    # conservative_df = sql_context.sql("SELECT topic, sentiment FROM topics WHERE topic = \"Conservatives\"")
    # liberal_df      = sql_context.sql("SELECT topic, sentiment FROM topics WHERE topic = \"Liberals\"")
    # ndp_df          = sql_context.sql("SELECT topic, sentiment FROM topics WHERE topic = \"NDP\"")
    #
    # sconservative = [str(s.sentiment) for s in conservative_df.select("sentiment").collect()]
    # sliberal      = [str(s.sentiment) for s in liberal_df.select("sentiment").collect()]
    # sndp          = [str(s.sentiment) for s in ndp_df.select("sentiment").collect()]

    # allParties_df       = sql_context.sql("SELECT topic, sentiment FROM topics ORDER BY topic asc")
    # allPartiesSentiment = [str(s.sentiment) for s in allParties_df.select("sentiment").collect()]




    # extract the counts from dataframe and convert them into array
    # tags_count = [p.sentiment for p in df.select("sentiment").collect()]
    #
    # conservativeData = sconservative[0] if len(sconservative) > 0 else "0.0"
    # liberalData      = sliberal[0] if len(sliberal) > 0 else "0.0"
    # ndpData          = sndp[0] if len(sndp) > 0 else "0.0"

    print("sentiments:")
    # print(conservativeData) #conservative
    # print(liberalData) #liberal
    # print(ndpData) #NDP
    print(provinceDict)


    # initialize and send the data through REST API
    url = 'http://10.24.235.161:5001/updateData'
    # request_data = {'label': str(top_tags), 'data': str(tags_count)}
    request_data = json.dumps(provinceDict)
    headers = {'content-type': 'application/json'}
    # request_data = {'liberal': str(liberalData), 'conservative': str(conservativeData), 'ndp': str(ndpData)}

    response = requests.post(url, data=request_data, headers=headers)


# do this for every single interval
sentiment_totals.foreachRDD(process_rdd)

# start the streaming computation
ssc.start()
# wait for the streaming to finish
ssc.awaitTermination()


