import cv2
import datetime
import os
import pymongo
import requests
import tempfile
import tweepy

from dotenv import load_dotenv
from pymongo import MongoClient, uri_parser

load_dotenv()

CONSUMER_KEY = os.environ["CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

uri = os.environ["MONGODB_URI"]
client = MongoClient(uri)
db = client[uri_parser.parse_uri(uri)["database"]]
collection = db["tweets"]

TARGET_FILE = "./images/001.jpg"
IMG_SIZE = (1280, 720)
target_img = cv2.imread(TARGET_FILE)
target_img = cv2.resize(target_img, IMG_SIZE)
target_hist = cv2.calcHist([target_img], [0], None, [256], [0, 256])

def imread_web(url):
  try:
    res = requests.get(url, timeout=3)
    img = None
    with tempfile.NamedTemporaryFile(dir='./') as fp:
      fp.write(res.content)
      fp.file.seek(0)
      img = cv2.imread(fp.name)
    return img
  except Exception as e:
    print(e.args)

time_file = "./time.txt"
utc_now = datetime.datetime.now(datetime.timezone.utc)
utc_time = utc_now
with open(time_file) as f:
  s = f.read()
  utc_ago = datetime.datetime.strptime(s, "%Y/%m/%d %H:%M:%S")

search_word = "#マイデザイン filter:images exclude:retweets"
for tweet in tweepy.Cursor(api.search, q=search_word, include_entities = True, tweet_mode = "extended", since=utc_ago.strftime("%Y-%m-%d_%H:%M:%S_UTC")).items():
  try:
    insert_flg = False
    for i in range(len(tweet.extended_entities["media"])):
      print(tweet.extended_entities["media"][i]["media_url"])
      url = tweet.extended_entities["media"][i]["media_url"]
      comparing_img = imread_web(url)
      comparing_img = cv2.resize(comparing_img, IMG_SIZE)
      comparing_hist = cv2.calcHist([comparing_img], [0], None, [256], [0, 256])
      ret = cv2.compareHist(target_hist, comparing_hist, 0)
      print(ret)
      if ret >= 0.7:
        insert_flg = True

    if insert_flg == True:
      utc_now = datetime.datetime.now(datetime.timezone.utc)
      post = {"tweet_id": tweet.id,
              "tweet_created_at": tweet.created_at,
              "created_at": utc_now,
              "updated_at": utc_now}

      result = collection.insert_one(post)
      print(result)
      print("登録しました。")

  except AttributeError as e:
    print(e)
  except cv2.error as e:
    print(e)
  except pymongo.errors.DuplicateKeyError as e:
    print(e)
  except Exception as e:
    print(e)
    print("エラー発生")
    utc_time = utc_ago

with open(time_file, mode="w") as f:
    f.write(utc_time.strftime("%Y/%m/%d %H:%M:%S"))
