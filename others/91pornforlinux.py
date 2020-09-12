import requests,os,re,time
from bs4 import BeautifulSoup as Bf

def getHTMLText(url, header):
    try:
        r = requests.get(url, headers = header, timeout = 300)
        r.raise_for_status()
        r.encoding = 'utf-8'
        return r.text
    except:
        return "crwal_error"

def FormList(html, hrefsls, namesls):
    soup = Bf(html, 'html.parser')
    a = soup('a')
    for i in range(27,51):
        hrefsls.append(a[i].get('href'))
        span = a[i]('span')
        namesls.append(span[-1].text)

def FindRealUrl(hrefsls,realurl):
    header = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36', 'referer': 'not blank'}

    for url in hrefsls:
        rr = requests.get(url, headers = header)
        realurl.append(re.findall(r'source src=".*?"', rr.text)[0].split('"')[-2])
def Save_as_files(hrefsls, namesls, p):
    header = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36', 'referer': 'not blank'}
    
    for i in range(len(namesls)):
        for one in range(len(namesls[i])):
            temp = []
            for j in range(len(namesls[i])):
                if namesls[i][j] == '/':
                    temp.append(' ')
                else:
                    temp.append(namesls[i][j])
            temp1 = ''.join(temp)    
        video_src = '/Users/json/data/Vedioes/' + str(p) + '/' + temp1 #输入你要存储的地址
        rr = requests.get(hrefsls[i], headers = header)
        with open(video_src + '.mp4', 'wb') as f:
            f.write(rr.content)
            f.close()
            time.sleep(3)

def main():
    
    page = input("从第几页开始爬？")
    topage = input("爬到哪一页?")
    for p in range(int(page), int(topage)):
        url = 'http://91porn.com/video.php?category=rf&page=' + str(p)
        header = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36', 'referer': 'not blank'}
        os.mkdir('/Users/json/data/Vedioes/' + str(p)) #存储地址(ps:注意最后要有'/')
        html = getHTMLText(url, header)
        hrefsls = []
        namesls = []
        realurl = []
        FormList(html, hrefsls, namesls)
        FindRealUrl(hrefsls,realurl)
        Save_as_files(realurl, namesls, p = p)

main()