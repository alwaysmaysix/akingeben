import requests
import os
import re
import time
from sys import stdout, argv
from hashlib import md5
from scraping_utils.scraping_utils import compute_file_hashes, DownloadThread, multithread_download_urls_special, IMG_EXTS, VID_EXTS, TOO_MANY_REQUESTS, NOT_FOUND, THROTTLE_TIME

POSTS_PER_FETCH = 50

class CoomerThread(DownloadThread):
    C_SERVER_COUNT = 6
    F_TOKEN = 'A-Coom@github'
    
    def __init__(self, url, dst, algo=md5, hashes={}):
        DownloadThread.__init__(self, url, dst, algo, hashes)
        self.base = url
        self.server = 1
        self.coomit()
        
    def coomit(self):
        ext = self.base.split('.')[-1]
        name = self.base.split('/')[-1].split('.')[0]
        t1 = name[0:2]
        t2 = name[2:4]
        self.url = f'https://c{self.server}.coomer.su/data/{t1}/{t2}/{name}.{ext}?f={self.F_TOKEN}.{ext}'
        self.server = self.server + 1
        if self.server > self.C_SERVER_COUNT: 
            self.server = 1
        
    def run(self):
        ext = self.base.split('.')[-1]
        name = self.base.split('/')[-1].split('.')[0]
        media = None
        
        try:
            while self.status == self.STANDBY:
                self.status = self.DOWNLOADING
                res = requests.get(self.url, allow_redirects=True)
                if res.status_code == TOO_MANY_REQUESTS:
                    self.status = self.STANDBY
                    self.coomit()
                    if self.server == 1:
                        time.sleep(THROTTLE_TIME)
                elif res.status_code != NOT_FOUND:
                    media = res.content
                    
        except requests.exceptions.Timeout:
            self.status = self.STANDBY
            self.coomit()
            if self.server == 1:
                time.sleep(THROTTLE_TIME)
            
        except Exception as e:
            self.status = self.ERROR
            return
        
        if media is None:
            self.status = self.ERROR
            return
        
        self.status = self.HASHING
        hash = self.algo(media).hexdigest()
        if hash in self.hashes:
            self.status = self.FINISHED
            return

        self.status = self.WRITING
        self.hashes[hash] = name
        with open(os.path.join(self.dst, hash + '.' + ext), 'wb') as file_out:
            file_out.write(media)
        self.status = self.FINISHED

def download_media(urls, include_vids, dst):
    stdout.write('[download_media] INFO: Computing hashes of existing files.\n')
    hashes = {}
    pics_dst = os.path.join(dst, 'Pics')
    vids_dst = os.path.join(dst, 'Vids')
    
    if os.path.isdir(pics_dst):
        hashes = compute_file_hashes(pics_dst, IMG_EXTS, md5, hashes)
    else:
        os.mkdir(pics_dst)

    if include_vids:
        if os.path.isdir(vids_dst):
            hashes = compute_file_hashes(vids_dst, VID_EXTS, md5, hashes)
        else:
            os.mkdir(vids_dst)
    stdout.write('\n')
        
    hashes = multithread_download_urls_special(CoomerThread, urls, pics_dst, vids_dst, algo=md5, hashes=hashes)
    return len(hashes)

def fetch_posts(service, creator, offset=None):
    try:
        api_url = f'https://coomer.su/api/v1/{service}/user/{creator}'
        if offset is not None:
            api_url = f'{api_url}?o={offset}'
        res = requests.get(api_url, headers={'accept': 'application/json'})
        assert(res.status_code == 200)
        return res.json()
    except:
        stdout.write(f'[fetch_posts] ERROR: Failed to fetch using API ({api_url})\n')
        stdout.write(f'[fetch_posts] ERROR: Status code: {res.status_code}\n')
        return []

def main(url, dst, vids):
    url = 'https://www.' + re.sub('(www\.)|(https?://)', '', url)
    if url[-1] == '/': 
        url = url[:-1]
    url_sections = url.split('/')
    if url_sections[-2] == 'post':
        stdout.write('[main] INFO: The URL must be for a creator, not a specific post.\n')
        return
    elif url_sections[-4] == 'data':
        stdout.write('[main] INFO: The URL must be for a creator, not a specific media.\n')
        return
        
    all_posts = []
    offset = 0
    stdout.write(f'[main] INFO: Fetching posts {offset + 1} - ')
    while True:
        stdout.write(f'{offset + POSTS_PER_FETCH}...')
        stdout.flush()
        curr_posts = fetch_posts(url_sections[-3], url_sections[-1], offset=offset)
        all_posts = all_posts + curr_posts
        offset += POSTS_PER_FETCH
        stdout.write(f'\033[{len(str(offset)) + 3}D')
        if len(curr_posts) % POSTS_PER_FETCH != 0:
            break
        elif len(curr_posts) == 0:
            stdout.write(f'{offset - POSTS_PER_FETCH}...')
            break
        
    stdout.write(f'\n[main] INFO: Parsing media from the {len(all_posts)} posts.\n')
    urls = []
    base = 'http://www.coomer.su'
    for post in all_posts:
        if 'path' in post['file']:
            ext = post['file']['path'].split('.')[-1]
            if not vids and ext in VID_EXTS: 
                continue
            urls.append(f'{base}{post["file"]["path"]}')
        for attachment in post['attachments']:
            ext = attachment['path'].split('.')[-1]
            if not vids and ext in VID_EXTS: 
                continue
            urls.append(f'{base}{attachment["path"]}')
    stdout.write(f'[main] INFO: Found {len(urls)} media files to download.\n\n')
    
    cnt = download_media(urls, vids, dst)
    stdout.write(f'\n[main] INFO: Successfully downloaded ({cnt}) unique media.\n\n')

if __name__ == '__main__':
    stdout.write('\n')
    if len(argv) != 4:
        url = input('Enter Coomer URL: ')
        dst = input('Enter download dir (./out/): ')
        vid = input('Include videos (Y/N): ')
    else:
        url = argv[1]
        dst = argv[2]
        vid = argv[3]
        
    vid = vid.lower()[0]
    
    if len(dst) == 0:
        dst = './out'
    if not os.path.isdir(dst):
        os.mkdir(dst)
        
    main(url, dst, (vid == 't' or vid == 'y'))
    stdout.write('\n')
