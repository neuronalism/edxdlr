# -*- coding: utf-8 -*-

import requests
import logging
import os
import re
import subprocess
import shutil
from utils import clean_filename

def get_m3u8_files(url, filename_prefix, headers, args):
    """
    Retrieve the list of files to download.
    """
    logging.debug('[m3u8dl] reading %s', url)
    filenames = []
    r = requests.get(url, headers=headers)
    m3u8_content = r.text
    for line in m3u8_content.splitlines():
        if line[0:1]!='#':
            filenames.append(line)

    # construct file name
    with open(filename_prefix+'.m3u8', "w") as m3u8file:
        m3u8file.write(r.text)
        m3u8file.close()
    
    return filenames

def download_m3u8(url, filename, headers, args):
    """
    Retrieve and download the list of files.
    """
    ok = True
    ts_files = []
    
    urls = get_m3u8_files(url, filename, headers, args)
    for ts_url in urls:
        ts_filename = ts_url.split('/').pop()

        if ts_url[0:3]!='http': 
            # add base url if omitted
            url_base = url.rsplit('/',1)[0]
            url = "{}/{}".format(url_base, ts_filename)
        else:
            url = ts_url
        # construct file name
        ts_filename = filename + '-' + clean_filename(ts_filename)

        logging.debug('[m3u8dl] reading %s', url)
        #print('[m3u8dl] reading ' + url)
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
    logging.debug('[m3u8dl] merge ts segments')
    mp4filename = mp4filename.replace('.m3u8', '.mp4')
    
    # merge ts files and then convert, in case the cmd gets too long
    merged_filename = mp4filename.replace('.mp4', '.ts')
    with open(merged_filename, 'wb') as merged:
        for ts_file in ts_files:
            with open(ts_file, 'rb') as tsfile:
                shutil.copyfileobj(tsfile, merged)
    # convert
    try:
        devnull = open(os.devnull, 'w')
        cmd = ['ffmpeg', '-i', merged_filename, '-c:a', 'copy', '-c:v', 'copy', mp4filename]
        subprocess.run(cmd, shell=False, stdout=devnull, stderr=devnull) 
        ts_files.append(merged_filename)
    except:
        logging.warn('[m3u8dl] ffmpeg not found, segments kept as-is')

    return ts_files
    

def clear_ts_files(ts_files):
    logging.debug('[m3u8dl] clear ts files')
    for tsfile in ts_files:
        os.remove(tsfile)

def download_mp4(url, filename, headers, args):
    """
    Downloads the given m3u8 url and merge it as mp4.
    """
    filename_prefix = filename.rstrip('.m3u8')
    ts_files = download_m3u8(url, filename_prefix, headers, args)
    ts_files = merge_m3u8_to_mp4(ts_files, filename)
    clear_ts_files(ts_files)
    
def choose_max_resolution(url, headers, args):
    """
    Detect and get max res m3u8 file
    """
    logging.debug('[m3u8dl] reading %s', url)
    
    r = requests.get(url, headers=headers)
    m3u8_content = r.text
    lines = m3u8_content.splitlines()

    url_base = url.rsplit('/',1)[0]
    default_resolution = 0
    default_url = url

    for l in list(range(len(lines))):
        if lines[l][0:17]=='#EXT-X-STREAM-INF':  
            # #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=348844,RESOLUTION=1664x936
            r = re.search('RESOLUTION=(\d+)x(\d+)',lines[l]) 
            res = int(r[1])*int(r[2])
            if res>default_resolution:
                default_resolution = res
                default_url = lines[l+1]

    if default_url[0:4]!='http':
        default_url = url_base + '/' + default_url

    return default_url