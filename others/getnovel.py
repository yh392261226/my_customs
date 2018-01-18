#--coding:utf-8--
#获取小说内容
from bs4 import BeautifulSoup
from sys import argv
import urllib
import codecs

print ("Type link here: >"),
link = raw_input()
print ("Type filename here: >")
filename = raw_input()
if link == "n" or link == "no":
  print ("Ok, Bye")
else:
  response = urllib.urlopen(link);
  html = response.read()
  # print (html)
  soup = BeautifulSoup(html, "html5lib")
  text = soup.get_text(strip=True)
  if "" != text:
    txt_write = codecs.open("/Users/json/Documents/novels/"+filename, 'w', "utf-8")
    txt_write.write(text);
    txt_write.close()
  else:
    print ("Does not get result")
