#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
forum thread fetcher
input: a list of single page
output: epub version of stripped html
"""
import subprocess
import smtplib
import urlparse
from urllib2 import urlopen, HTTPError
from urllib import urlretrieve
import os
import sys
import re
import random
from bs4 import *
from bs4.element import NavigableString
from epub import *
import argparse
from time import sleep

## for sending email
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
import base64
class vbbfetcher:
    """
    Vbb fetcher
    """
    def __init__(self, url_list, **options):
        self.index_url_orig = url_list
        self.fetched_url = []
        self.fetched_file = []
        self.fetched_css = []
        self.fetched_img = []
        self.index_pid_lst = []
        self.html_file = []
        self.index_lst = options.get('index', [])
        self.toc_map = options.get('toc_map', {})
        self.toc_full_map = {}
        self.html_basepath = ""
        self.url_path = ""
        self.url_loc = ""
        self.exclude = []        
        self.regex = []
        self.title_length = 255
        self.new_update = False
        tmp = options.get('regex', [])
        if tmp:
            self.regex = tmp

        tmp = options.get('exclude',[])
        if tmp:
            for i in tmp:
                pid = self.extract_thread_post_id(i)
                if pid:
                    self.exclude.append(pid)
            
        tmp = options.get('title_length', 0)
        if tmp:
            self.title_length = tmp

        if self.index_lst:
            p = urlparse.urlsplit(self.index_lst[0])
            self.url_path = p.scheme + '://' + p.netloc
            self.url_loc = p.netloc
        elif self.index_url_orig:
            p = urlparse.urlsplit(self.index_url_orig[0])
            self.url_path = p.scheme + '://' + p.netloc
            self.url_loc = p.netloc

        self.html_path = self.url_loc + '/' + options.get('html_path', 'Html')
        self.img_path = self.url_loc + '/' + options.get('img_path', 'Images')
        self.css_path = self.url_loc + '/' + options.get('css_path', 'Styles')

        if not os.path.exists(self.html_path):
            os.makedirs(self.html_path)
        if not os.path.exists(self.img_path):
            os.makedirs(self.img_path)
        if not os.path.exists(self.css_path):
            os.makedirs(self.css_path)
        ## build the url list
        for i in self.index_url_orig:
            pid = self.extract_thread_post_id(i)
            if pid:
                self.index_pid_lst.append(i)


    def extract_thread_post_id(self, url):
        ## FIXME: should check if urlsplit is successfull or not
        p = urlparse.urlsplit(url)
        if p.netloc <> self.url_loc:
            return None
        m = re.match(r'p\=(\d+).*', p.query)
        if m:
            return m.group(1)
        else:
            print "Error: can't find post or thread id: %s" % url
            return None

    def download_file(self, url, path="."):
        filename = url.split('/')[-1]
        outpath = os.path.join(path, filename)
        urlretrieve(url,outpath)

    def save_html(self, soup, filename, path="."):
        outpath = os.path.join(path, filename)
        f = open(outpath, 'wb')
        f.write(str(soup))
        f.close()

    def fetch_html(self, pid, filename="", path="."):
        if pid == None: return
        if pid in self.exclude: return
        page = None
        url = self.url_path + '/showpost.php?p=' +pid
        if os.path.exists(self.html_path + '/' + pid + '.html'):
            print "File downloaded: %s" % (self.html_path + '/' + pid + '.html')
            page = open(self.html_path + '/' + pid + '.html', 'r')
        else:
            self.new_update = True
            try:
                print "Downloading %s" % url
                page = urlopen(url)
            except HTTPError:
                print "HTTP Error: redownloading 1 %s" % url
                sleep(5)
                try:
                    page = urlopen(url)
                except HTTPError:
                    sleep(5)
                    print "HTTP Error: redownloading 2 %s" % url
                    try:
                        page = urlopen(url)
                    except:
                        sleep(5)
                        print "HTTP Error: redownloading 3 %s" % url
                        page = urlopen(url)
            except:
                print "Unexpected error:", sys.exc_info()[0]
                raise
        soup = BeautifulSoup(page.read())
        if pid not in self.fetched_url:
            self.fetched_url.append(pid)
        download_list = []

	for i in soup('script'):
		i.extract()
	for i in soup('style'):
		i.extract()
	for i in soup('link'):
		i.extract()
        div = soup.findAll(True, attrs={'id': ['post_message_'+pid]})
        if len(div) == 1:
            tag = soup.body
            tag.clear()
            tag.insert(0, div[0])
            a_list = soup.findAll('a', href=True)
            a_pid = ""
            for a in a_list:
                if a['href']:
                    a_pid = self.extract_thread_post_id(a['href'])
                    if a_pid:
                        a['href'] = '../Texts/' + a_pid + '.html'

            toc = []
            cnt = 0
            text = ""
            heading_id = ""
            for sec_regex in self.regex:
                for i in soup(text=re.compile(sec_regex.decode('utf-8'), re.I)):
                    t1 = i.parent
                    if t1.name != 'div':
                        t2 = t1.parent
                        while( t2.name != 'div' and t2 != None):
                            t1=t1.parent
                            t2=t1.parent
                    else:
                        t1 = i
                    print repr(t1)
                    if isinstance(t1,NavigableString):
                        print "I: " + repr(t1)
                        text= t1.strip()
                        if len(text) <= self.title_length:
                            s = BeautifulSoup('<h2>'+text+'</h2>')
                            t = s.h2
                            heading_id = 'hd_' + pid + '_' + str(cnt)
                            t['id'] = heading_id
                            cnt +=1
                            t1.insert_before(t)
                            t1.replace_with('')
                            toc.append((text,heading_id))
                    else:
                        print "T: " + repr(t1)
                        for stp in t1.stripped_strings:
                            text=stp
                        if len(text) > self.title_length:
                            break
                        if t1.name == 'a':
                            break
                        if t1.find_all('a'):
                            break
                        if re.match(r'h[0-9]',t1.name):
                            print 'H: ' + repr(t1),
                            if 'id' not in t1:
                                heading_id = 'hd_' + pid +'_'+ str(cnt)
                                t1['id'] = heading_id
                                cnt+=1
                            else:
                                heading_id = t1['id']
                            toc.append((text,heading_id))
                            # print text,
                            # print heading_id,
                            # print toc
                        else:
                            print 'N: ' + repr(t1)
                            t1.name = 'h2'
                            heading_id = 'hd_' + pid +'_'+ str(cnt)
                            cnt+=1
                            t1['id'] = heading_id
                            t1.clear()
                            t1.insert(0,text)
                            toc.append((text,heading_id))
            print toc
            if len(toc) == 0:
                if pid in self.toc_map:
                    text = self.toc_map[pid].strip()
                    tx = soup(text=re.compile('^\s*' + text +'\s*$', re.I))
                    if len(tx) == 0:
                        if not text.startswith('http://'):
                            heading_id = 'hd_' + pid +'_'+ str(cnt)
                            cnt+=1
                            s = BeautifulSoup('<h2>' + text + '</h2>')
                            t = s.h2
                            t['id'] = heading_id
                            tag.insert(0, t)
                            toc.append((text, heading_id))
                    else:
                        for i in tx:
                            t1 = i.parent
                            if t1.name != 'div':
                                t2 = t1.parent
                                while( t2.name != 'div' and t2 != None):
                                    t1=t1.parent
                                    t2=t1.parent
                                # for stp in t1.stripped_strings:
                                #         print stp,
                            else:
                                t1 = i
                            # print i,
                            print repr(t1)
                            if isinstance(t1,NavigableString):
                                print "IP: " + repr(t1)
                                text= t1.strip()
                                if len(text) <= self.title_length:
                                    s = BeautifulSoup('<h2>'+text+'</h2>')
                                    t = s.h2
                                    heading_id = 'hd_' + pid + '_' + str(cnt)
                                    t['id'] = heading_id
                                    cnt +=1
                                    t1.insert_before(t)
                                    t1.replace_with('')
                                    toc.append((text,heading_id))
                            else:
                                print "T: " + repr(t1)
                                for stp in t1.stripped_strings:
                                    text=stp
                                if len(text) > self.title_length:
                                    break
                                if t1.name == 'a':
                                    break
                                if t1.find_all('a'):
                                    break
                                if re.match(r'h[0-9]',t1.name):
                                    print 'H: ' + repr(t1),
                                    if 'id' not in t1:
                                        heading_id = 'hd_' + pid +'_'+ str(cnt)
                                        t1['id'] = heading_id
                                        cnt+=1
                                    else:
                                        heading_id = t1['id']
                                    toc.append((text,heading_id))
                                else:
                                    print 'N: ' + repr(t1)
                                    t1.name = 'h2'
                                    heading_id = 'hd_' + pid +'_'+ str(cnt)
                                    cnt+=1
                                    t1['id'] = heading_id
                                    t1.clear()
                                    t1.insert(0,text)
                                    toc.append((text,heading_id))
                        
            self.toc_full_map[pid] = toc
        else:
            print "Error: too many divs"
        # save all images
        for image in soup.findAll("img"):
            if image['src'] is not None:
                image_url = urlparse.urljoin(url, image['src'])
                if image_url in self.fetched_img:
                    pass
                elif os.path.exists(self.img_path + '/' + image['src'].split('/')[-1]):
                    print "Image downloaded: %s" %(self.img_path + '/' + image['src'].split('/')[-1])
                    self.fetched_img.append(image_url)                
                else:
                    print "Downloading image: %s" % image_url
                    self.download_file(image_url,self.img_path)
                    self.fetched_img.append(image_url)
                image['src'] = '../Images/' + image['src'].split('/')[-1]
        filename = pid+".html"
        self.save_html(soup, filename, self.html_path)
        return soup
        

    def download(self):
        for i in self.index_url_orig:
            url = urlparse.urljoin(self.url_path,i)
            pid = self.extract_thread_post_id(url)
            self.fetch_html(pid)
def send_mail(send_from, send_to, subject, text, files=[]):
    assert type(send_to)==list
    assert type(files)==list
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach( MIMEText(text) )
    fp = open('p.txt','r')
    pstr = fp.read()
    password = base64.b64decode(pstr.strip()).decode('hex')
    for f in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(f,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"'
                        % os.path.basename(f))
        msg.attach(part)

    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(send_from,password)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()
def create_book(args):
    url_lst = []
    url_title = {}
    index_lst = []
    if args.Index:
        url_lst += args.Index
        index_lst = args.Index
    if args.appendToBegin:
        url_lst += args.list
    if args.file:
        f = open(args.file, 'r')
        for i in f:
            url_lst.append(i)
    if args.index:
        index_lst = args.index
    for i in index_lst:
        print "Parsing index url: %s" % i
        vbb = vbbfetcher([i])
        pid = vbb.extract_thread_post_id(i)
        page = urlopen(i)
        test = urlopen(i).read()
        # print test
        soup = BeautifulSoup(page.read())
        for i in soup('script'):
                i.extract()
        for i in soup('style'):
                i.extract()
        for i in soup('link'):
                i.extract()
        # print soup
        div = soup.findAll(True, attrs={'id': ['post_message_'+pid]})
        if len(div) == 1:
            tag = soup.body
            tag.clear()
            tag.insert(0, div[0])
            for link in BeautifulSoup(str(div[0])).findAll('a', href=True):
                if link['href'] in url_lst: continue
                url_lst.append(link['href'])
                p = vbb.extract_thread_post_id(link['href'])
                if p:
                    for i in link.stripped_strings:
                        url_title[p] = i
        else:
            print "Error: too many divs"

    if args.appendToEnd:
        url_lst += args.list
    f = open(args.title + '.log', 'w')
    f.write('\n'.join(url_lst))
    f.close()
    print "Fetching html..."
    v = vbbfetcher(url_lst, toc_map=url_title,
                   regex=args.regex,exclude=args.nofetch,
                   title_length=args.title_length)
    v.download()
    print "Creating ebook..."
    if args.title :
        book_title=args.title
    else:
        book_title="Default"
    book_path = book_title + '.epub'
    book_converted = book_title + '.mobi'
    if v.new_update:
        if os.path.exists(book_converted):
            os.remove(book_converted)
    else:
        print "No update found"
        # return
    book = EpubBook()
    book.setTitle(book_title)
    if args.author:
        book.addCreator(args.author)
    else:
        book.addCreator('Default')
    book.addMeta('date', '2012', event = 'publication')
    for css_url in v.fetched_css:
        css_path =  v.css_path + '/' + css_url.split('/')[-1]
        css_dest =  "Styles/" + css_url.split('/')[-1]
        book.addCss(css_path, css_dest)
    cnt = 0
    rm_f = open(book_title+'.rm.txt','w')
    for html_url in v.fetched_url:
        filename = ""
        if html_url.endswith('/'):
            filename = "index.html"
        else:
            filename = html_url.split('/')[-1]

        html_path = v.html_path + '/' + filename + ".html"
        rm_f.write(html_path+'\n')
        dest_path = "Texts/" + filename + ".html"
        f = open(html_path, 'r')
        print html_path,
        print dest_path
        n1 = book.addHtml(html_path, dest_path, f.read())
        book.addSpineItem(n1)

        if html_url in v.toc_full_map:
            for t in v.toc_full_map[html_url]:
                print t
                book.addTocMapNode(n1.destPath+'#'+t[1], t[0])
        f.close()
    for img_url in v.fetched_img:

        if img_url is not None:
            filename = img_url.split('/')[-1]
            img_path = v.img_path + '/' + filename
            img_dest = "Images/" + filename
            book.addImage(img_path,img_dest)
    rootDir = r"output"
    book.createBook(rootDir)
    EpubBook.createArchive(rootDir, book_title + '.epub')
    if not os.path.exists(book_converted):
        cmd = ['ebook-convert']
        cmd.append(book_path)
        cmd.append(book_converted)
        cmd.append('--output-profile')
        cmd.append('kindle')
        subprocess.call(cmd)
    if os.path.exists(book_converted):
        send_from = file('u.txt').read().strip()
        send_to = file('t.txt').read().split()
        flst = []
        flst.append(book_converted)
        subject = "[vbbfetcher] e-book"
        text = "Have a nice reading!\n"
        print '='*20 + " Sending email " +'='*20
        send_mail(send_from, send_to, subject, text, flst)
        print '='*20 + ' Sending email done ' + '='*15
    else:
        print '='*20 + " No book to send " + '='*20

if __name__ == "__main__":

    print sys.getdefaultencoding()
    reload(sys)
    sys.setdefaultencoding('utf-8')    
    print sys.getdefaultencoding()
    parser = argparse.ArgumentParser()
    parser.add_argument("list", metavar="url-list", type=str, nargs='*')
    parser.add_argument("-f", "--file", help="index file", type=str)
    parser.add_argument("-i", "--index", help="index url list",
                        type=str, nargs='*')
    parser.add_argument("-I", "--Index", help="index url list and this will be append to the fetching list",
                        type=str, nargs='*')
    parser.add_argument("title", help="Book's name",
                        type=str)
    parser.add_argument("-a", "--author", help="Book's author", type=str)
    parser.add_argument("-b", "--appendToBegin",
                        help="Append url list to download list", action="store_true")
    parser.add_argument("-e", "--appendToEnd",
                        help="Append url list to the end of download list",
                        action="store_true")
    parser.add_argument('-r', '--regex',
                        help="Document structure regular expression",
                        type=str, nargs='*')
    parser.add_argument('-k', '--nofetch',
                        help="do not fetch the following url",
                        type=str, nargs='*')
    parser.add_argument('-l', '--title_length',
                        help="all title greater than this length will not be added to the index",
                        type=int)
    args = parser.parse_args()

    create_book(args)
    # main(args)

