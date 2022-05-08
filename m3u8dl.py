# -*- coding: utf-8 -*-

import requests
import logging
import os
import re
import subprocess
from utils import clean_filename

def get_m3u8_files(url, headers, args):
    """
    Retrieve the list of files to download.
    """
    logging.debug('[m3u8] reading %s', url)
    filenames = []
    r = requests.get(url, headers=headers)
    m3u8_content = r.text
    for line in m3u8_content.splitlines():
        if line[0:1]!='#':
            filenames.append(line)
    return filenames

def download_m3u8(url, filename, headers, args):
    """
    Retrieve and download the list of files.
    """
    ok = True
    ts_files = []
    
    urls = get_m3u8_files(url, headers, args)
    for ts_url in urls:
        ts_filename = ts_url.split('/').pop()

        if ts_url[0:3]!='http': 
            # add base url if omitted
            url_base = url.rsplit('/',1)[0]
            url = "{}/{}".format(url_base, ts_filename)
        else:
            url = ts_url
        # construct file name
        ts_filename = filename + clean_filename(ts_filename)

        logging.debug('[m3u8] reading %s', url)
        #print('[m3u8] reading ' + url)
        r = requests.get(url, headers=headers)
        if r.status_code == requests.codes.OK:
            with open(ts_filename, "wb") as ts:
                ts.write(r.content)
                ts.close()
                ts_files.append(ts_filename)
        else:
            logging.error('failed to get ts file '+url)
            ok = False

    if not ok:
        return []
    else:
        return ts_files
    
def merge_m3u8_to_mp4(ts_files, mp4filename):
    """
    Downloads the given m3u8 url and merge it as mp4.
    """
    logging.debug('[m3u8] merging files')
    cmd = ['ffmpeg', '-i', "concat:{}".format("|".join(ts_files)), '-c:a', 'copy', '-c:v', 'copy', mp4filename]
    subprocess.call(cmd, shell=False)

def clear_ts_files(ts_files):
    logging.debug('[m3u8] clear ts files')
    for tsfile in ts_files:
        os.remove(tsfile)

def download_mp4(url, filename, headers, args):
    """
    Downloads the given m3u8 url and merge it as mp4.
    """
    filename_prefix = filename.rstrip('.mp4')
    ts_files = download_m3u8(url, filename_prefix, headers, args)
    merge_m3u8_to_mp4(ts_files, filename)
    clear_ts_files(ts_files)
    
def choose_max_resolution(url, headers, args):
    """
    Detect and get max res m3u8 file
    """
    logging.debug('[m3u8] reading %s', url)
    
    r = requests.get(url, headers=headers)
    m3u8_content = r.text
    lines = m3u8_content.splitlines()

    url_base = url.rsplit('/',1)[0]
    default_resolution = 0
    default_url = url

    for l in list(range(len(lines))):
        if lines[l][0:17]=='#EXT-X-STREAM-INF':
            r = re.search('RESOLUTION=(\d+)x(\d+)',lines[l]) #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=348844,RESOLUTION=1664x936
            res = int(r[1])*int(r[2])
            if res>default_resolution:
                default_resolution = res
                default_url = lines[l+1]

    if default_url[0:4]!='http':
        default_url = url_base + '/' + default_url

    return default_url