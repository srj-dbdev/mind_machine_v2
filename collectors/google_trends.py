from pytrends.request import TrendReq

pytrends = TrendReq()

trending = pytrends.trending_searches()

print(trending.head(20))