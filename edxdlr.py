#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main module for the edx-dl downloader.
It corresponds to the cli interface
"""
import argparse
import getpass
import json
import logging
from logger import *
import signal
import os
import re
import sys
import m3u8dl
from multiprocessing import Pool

#from six.moves.http_cookiejar import CookieJar
from six.moves.urllib.error import HTTPError, URLError
#from six.moves.urllib.parse import urlencode
#from six.moves.urllib.request import (
#    urlopen,
#    build_opener,
#    install_opener,
#    HTTPCookieProcessor,
#    Request,
#    urlretrieve,
#)
import requests

from _version import __version__

from common import (
    Course,
    Block,
    WebPage,
    Video,
    Material, 
    ExitCode,
    DEFAULT_FILE_FORMATS,
)
from parsing import (
    edx_json2srt,
    EdxExtractor,
)
from utils import (
    clean_filename,    
    get_filename_from_prefix,
    get_page_contents,
    get_page_contents_as_json,
    post_page_contents,
    post_page_contents_as_json,
    mkdir_p
)
import runtime

#CHANGES: redefining urls
BASE_URL = 'https://courses.edx.org'
EDX_HOMEPAGE = BASE_URL
LOGIN_PAGE = 'https://authn.edx.org/login'
LOGIN_API = BASE_URL + '/api/user/v2/account/login_session/'
TOKEN_API = BASE_URL + '/csrf/api/v1/token'
DASHBOARD_URL = 'https://home.edx.org'
LEARNING_URL = 'https://learning.edx.org'
COURSE_LIST_JSON_API = BASE_URL + '/api/learner_home/init'
COURSE_OUTLINE_JSON_API = BASE_URL + '/api/course_home/outline'
COURSE_SEQUENCE_JSON_API = BASE_URL + '/api/courseware/sequence'
COURSE_BLOCK_API = BASE_URL + '/xblock'

# for parallel downloading
global pool

# ######## login issues ########

def parse_args():
    """
    Parse the arguments/options passed to the program on the command line.
    CHANGES: removed -x support; works only for edx.org now
    """
    parser = argparse.ArgumentParser(prog='edxdlr',
                                     description='Get materials from edx.org',
                                     epilog='For further use information,'
                                     'see the file README.md',)
    # positional
    parser.add_argument('course_urls',
                        nargs='*',
                        action='store',
                        default=[],
                        help='target course urls '
                        '(e.g., https://learning.edx.org/course/course-v1:DoaneX+BIOL-295x+2T2020/home)')

    # optional
    parser.add_argument('-u',
                        '--username',
                        required=True,
                        action='store',
                        help='your edX username (email)')

    parser.add_argument('-p',
                        '--password',
                        action='store',
                        help='your edX password, '
                        'beware: it might be visible to other users on your system')

    parser.add_argument('-f',
                        '--format',
                        dest='format',
                        action='store',
                        default=None,
                        help='format of videos to download')

    parser.add_argument('-s',
                        '--with-subtitles',
                        dest='subtitles',
                        action='store_true',
                        default=False,
                        help='download subtitles with the videos')

    parser.add_argument('-o',
                        '--output-dir',
                        action='store',
                        dest='output_dir',
                        help='store the files to the specified directory',
                        default='Downloaded')

    parser.add_argument('-i',
                        '--ignore-errors',
                        dest='ignore_errors',
                        action='store_true',
                        default=False,
                        help='continue on download errors, to avoid stopping large downloads')

    parser.add_argument('--list-courses',
                        dest='list_courses',
                        action='store_true',
                        default=False,
                        help='list available courses')

    #CHANGE: list sections are now list chapters
    parser.add_argument('--list-chapters',
                        dest='list_chapters',
                        action='store_true',
                        default=False,
                        help='list available chapters')

    parser.add_argument('--export-filename',
                        dest='export_filename',
                        default=None,
                        help='filename where to put an exported list of urls. '
                        'Use dash "-" to output to stdout. '
                        'Download will not be performed if this option is '
                        'present')

    parser.add_argument('--export-format',
                        dest='export_format',
                        default='%(url)s',
                        help='export format string. Old-style python formatting '
                        'is used. Available variables: %%(url)s. Default: '
                        '"%%(url)s"')

    parser.add_argument('--list-file-formats',
                        dest='list_file_formats',
                        action='store_true',
                        default=False,
                        help='list the default file formats extracted')

    parser.add_argument('--file-formats',
                        dest='file_formats',
                        action='store',
                        default=None,
                        help='appends file formats to be extracted (comma '
                        'separated)')

    parser.add_argument('--overwrite-file-formats',
                        dest='overwrite_file_formats',
                        action='store_true',
                        default=False,
                        help='if active overwrites the file formats to be '
                        'extracted')

    parser.add_argument('--process',
                        dest='process',
                        action='store',
                        default=None,
                        help='speed up using multiple processes')

    parser.add_argument('--download-m3u8',
                        dest='m3u8',
                        action='store_true',
                        default=False,
                        help='download video using m3u8 (ffmpeg required)')

    parser.add_argument('--retry',
                        dest='retry',
                        action='store',
                        default=3,
                        help='download retry times')

    parser.add_argument('--short-names',
                        dest='shorten',
                        action='store_true',
                        default=False,
                        help='use short file names (<32 chars)')
    
    parser.add_argument('--cache',
                        dest='cache',
                        action='store_true',
                        default=False,
                        help='create and use a cache of extracted resources')

    parser.add_argument('--dry-run',
                        dest='dry_run',
                        action='store_true',
                        default=False,
                        help='makes a dry run, only lists the resources')

    parser.add_argument('--quiet',
                        dest='quiet',
                        action='store_true',
                        default=False,
                        help='omit as many messages as possible, only printing errors')

    parser.add_argument('--debug',
                        dest='debug',
                        action='store_true',
                        default=False,
                        help='print lots of debug information')

    parser.add_argument('--version',
                        action='version',
                        version=__version__,
                        help='display version and exit')

    args = parser.parse_args()


    # Initialize the logging system first so that other functions
    # can use it right away.
    if args.debug:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(name)s[%(funcName)s] %(message)s')
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR,
                            format='%(name)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(message)s')

    return args

def edx_get_headers():
    """
    Build the Open edX headers to create future requests.
    """
    def _get_initial_token(url):
        """
        Create initial connection to get authentication token for future
        requests.

        Returns a string to be used in subsequent connections with the
        X-CSRFToken header or the empty string if we didn't find any token in
        the cookies.
        """
        logging.info('Getting initial CSRF token.')

        response = runtime.session.get(url)

        for cookie in response.cookies:
            if cookie.name == 'csrftoken':
                logging.info('Found CSRF token.')
                return cookie.value

        logging.warn('Did not find the CSRF token.')
        return ''

    logging.info('Building initial headers for future requests.')
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        'Referer': LOGIN_PAGE,
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': _get_initial_token(TOKEN_API),
    }
    logging.debug('Headers built: %s', headers)
    return headers

def edx_login(email, password):
    """
    Log in user into the openedx website.
    """
    
    # simulate real request
    response = runtime.session.get(LOGIN_PAGE, headers=runtime.headers)
    
    # then real request
    logging.info('Logging into edX.org: %s', LOGIN_API)
    post_data = {'email_or_username': email, 'password': password}
    response = runtime.session.post(LOGIN_API, data=post_data, headers=runtime.headers)
    
    if response.status_code != 200:
        failure_info = json.loads(response.text)
        logging.info('Error, cannot login: (%s) %s', response.status_code, failure_info['value'])
    
    return response

# ######## list all courses ########

def _display_courses(courses):
    """
    List the courses that the user has enrolled.
    """
    logging.info('Detected %d courses', len(courses))

    for i, course in enumerate(courses, 1):
        logging.info('%2d - %s [%s]', i, course.name, course.id)
        logging.info('     %s', course.url)

def get_courses_info_from_dashboard(dashurl):
    """
    (obsolete) Extracts the courses information from the dashboard.
    """
    logging.info('Extracting course information from dashboard.')
    
    page = get_page_contents(dashurl, runtime.headers)
    page_extractor = EdxExtractor()
    username = page_extractor.extract_username_from_dashboard(page)
    courses = page_extractor.extract_courses_from_dashboard(page)    

    logging.debug('Data extracted: %s', courses)

    return [username, courses]

def get_username_from_cookies():
    """
    (not used) Extracts the courses information from cookies.
    """
    logging.info('Extracting user name from cookies.')
    page_extractor = EdxExtractor()    
    return page_extractor.extract_username_from_cookie(runtime.session.cookies)
    
def get_courses_info_from_json():
    """
    Extracts the courses information from cookies.
    """
    logging.info('Extracting course information from cookies.')
    
    page_extractor = EdxExtractor()
    course_json = get_page_contents_as_json(COURSE_LIST_JSON_API, runtime.headers)
    courses = page_extractor.extract_courses_from_json(course_json)  

    # get username

    logging.debug('Data extracted: %s', courses)

    return courses

def parse_courses(args, available_courses):
    """
    Parses courses options and returns the selected_courses.
    """
    if args.list_courses:
        _display_courses(available_courses)
        sys.exit(ExitCode.OK)

    if len(args.course_urls) == 0:
        logging.error('You must pass the URL of at least one course, check the correct url with --list-courses')
        sys.exit(ExitCode.MISSING_COURSE_URL)

    selected_courses = [available_course
                        for available_course in available_courses
                        for url in args.course_urls
                        if available_course.url.find(url)>=0] #CHANGE: dont know why to use find 
    if len(selected_courses) == 0:
        logging.error('You have not passed a valid course url, check the correct url with --list-courses')
        sys.exit(ExitCode.INVALID_COURSE_URL)
    return selected_courses

# ######## get blocks and sort them out

def get_available_blocks(course_id):
    """
    Extracts all blocks for a given course
    """
    logging.debug("Extracting blocks for " + course_id)
    
    url = COURSE_OUTLINE_JSON_API + '/' + course_id
    logging.debug("Extracting from " + url)    

    page = get_page_contents_as_json(url, headers=runtime.headers)
    page_extractor = EdxExtractor()
    blocks = page_extractor.extract_sequential_blocks_from_json(page)

    block_names = list(blocks.keys())
    for i, block_name in enumerate(block_names, 1):
        if block_name.find('type@sequential')>=0:
            url = COURSE_SEQUENCE_JSON_API + '/' + block_name
            logging.debug("Extracting from " + url)
            page = get_page_contents_as_json(url, headers=runtime.headers)
            blocks = page_extractor.extract_vertical_blocks_from_sequential(blocks, page, COURSE_BLOCK_API)

    blocks = page_extractor.sort_blocks(blocks);
    logging.debug("Extracted blocks: " + blocks.treeview())
    return blocks

def _display_chapters(block):
    """
    List the chapters for the given course.
    """
    #CHANGE: weeks/sections are stored as chapters now
    logging.info('%s [%s] has %d chapters', block.name, block.id, len(block.chapters()))
    for i, chapter_block in enumerate(block.chapters(), 1):
        logging.info('%2d - %s', i, chapter_block.name)

def extract_units(url, headers, file_formats):
    """
    Parses a webpage and extracts its resources e.g. video_url, sub_url, etc.
    """
    logging.info("Processing '%s'", url)

    #post_data = urlencode({ 'show_title': 0, 
    #                        'show_bookmark_button': 0,
    #                        'recheck_access': 1,
    #                        'view': 'student_view'}).encode('utf-8') 
    page = get_page_contents(url, headers)
    page_extractor = EdxExtractor()
    units = page_extractor.extract_units_from_html(url, page, file_formats)

    return units

def parse_file_formats(args):
    """
    parse options for file formats and builds the array to be used
    """
    file_formats = DEFAULT_FILE_FORMATS

    if args.list_file_formats:
        logging.info(file_formats)
        exit(ExitCode.OK)

    if args.overwrite_file_formats:
        file_formats = []

    if args.file_formats:
        new_file_formats = args.file_formats.split(",")
        file_formats.extend(new_file_formats)

    logging.debug("file_formats: %s", file_formats)
    return file_formats

# ####### download functions 

def get_subtitles_urls(available_subs_url, sub_template_url, headers):
    """
    Request the available subs and builds the urls to download subs
    """
    if available_subs_url is not None and sub_template_url is not None:
        try:
            available_subs = get_page_contents_as_json(available_subs_url,
                                                       headers)
        except HTTPError:
            available_subs = ['en']

        return {sub_lang: sub_template_url % sub_lang
                for sub_lang in available_subs}

    elif sub_template_url is not None:
        try:
            available_subs = get_page_contents(sub_template_url,
                                                       headers)
        except HTTPError:
            available_subs = ['en']

        return {'en': sub_template_url}

    return {}

def edx_get_subtitle(url, headers):
    """
    Return a string with the subtitles content from the url or None if no
    subtitles are available.
    """
    try:
        if ';' in url:  # non-JSON format (e.g. Stanford)
            return get_page_contents(url, headers)
        else:
            json_object = get_page_contents_as_json(url, headers)
            return edx_json2srt(json_object)
    except URLError as exception:
        logging.warn('edX subtitles (error: %s)', exception)
        return None
    except ValueError as exception:
        logging.warn('edX subtitles (error: %s)', exception.message)
        return None

def _build_subtitles_downloads(args, video, target_dir, filename_prefix, headers):
    """
    Builds a dict {url: filename} for the subtitles, based on the
    filename_prefix of the video
    """
    downloads = {}
    filename = get_filename_from_prefix(target_dir, filename_prefix)

    if filename is None:
        logging.warn('No video downloaded for %s', filename_prefix)
        return downloads
    if video.subs_template_url is None:
        logging.warn('No subtitles downloaded for %s', filename_prefix)
        return downloads

    # This is a fix for the case of retrials because the extension would be
    # .lang (from .lang.srt), so the matching does not detect correctly the
    # subtitles name
    re_is_subtitle = re.compile(r'(.*)(?:\.[a-z]{2})')
    match_subtitle = re_is_subtitle.match(filename)
    if match_subtitle:
        filename = match_subtitle.group(1)

    if args.shorten:
        filename = filename[:32].strip()
        
    subtitles_download_urls = get_subtitles_urls(video.subs_available_url,
                                                 video.subs_template_url,
                                                 headers)
    for sub_lang, sub_url in subtitles_download_urls.items():
        subs_filename = os.path.join(target_dir,
                                     filename + '.' + sub_lang + '.srt')
        downloads[sub_url] = subs_filename
    return downloads

def download_subtitle(url, filename, headers, args):
    """
    Downloads the subtitle from the url and transforms it to the srt format
    """
    subs_string = edx_get_subtitle(url, headers)
    if subs_string:
        full_filename = os.path.join(os.getcwd(), filename)
        with open(full_filename, 'wb+') as f:
            f.write(subs_string.encode('utf-8'))

def _build_url_downloads(args, urls, target_dir, filename_prefix):
    """
    Builds a dict {url: filename} for the given urls
    otherwise just takes the name of the file from the url
    """
    downloads = {url:
                 _build_filename_from_url(args, url, target_dir, filename_prefix)
                 for url in urls}
    return downloads

def _build_filename_from_url(args, url, target_dir, filename_prefix):
    """
    Builds the appropriate filename for the given args
    """
    original_filename = filename_prefix + '-' + url.rsplit('/', 1)[1]
    filename = original_filename.rsplit('.',1)[0]
    fileformat = original_filename.rsplit('.',1)[1]
    if args.shorten:
        filename = filename[:32].strip()
    filename = os.path.join(target_dir, filename + '.' + fileformat)
    return filename

def download_url(url, filename, headers, args):
    """
    Downloads the given url in filename.
    """
    import requests
    from tqdm.auto import tqdm
    import shutil
    # FIXME: Ugly hack for coping with broken SSL sites:
    # https://www.cs.duke.edu/~angl/papers/imc10-cloudcmp.pdf
    #
    # We should really ask the user if they want to stop the downloads
    # or if they are OK proceeding without verification.
    #
    # Note that skipping verification by default could be a problem for
    # people's lives if they happen to live ditatorial countries.
    #
    # Note: The mess with various exceptions being caught (and their
    # order) is due to different behaviors in different Python versions
    # (e.g., 2.7 vs. 3.4).
    attempts = 0
    success = False
    while not success and attempts <= args.retry:

        attempts = attempts + 1        
        try:            
            with requests.get(url, stream=True, headers=headers) as r:
                total_size = int(r.headers.get("Content-Length", 0))
                with tqdm.wrapattr(r.raw, "read", total=total_size, desc="") as data:
                    with open(filename, 'wb')as output:
                        shutil.copyfileobj(data, output)
            success = True
        except requests.ConnectionError as e:            
            logging.warning('\nNetwork error (%s), retrying [%d]', e, attempts)
        except Exception as e:
            logging.error('error occured, retrying [%d]: %s', attempts, e)

    if not success:
        os.remove(filename)
        if not args.ignore_errors:
            logging.error('error: failed to download %s', url)
            logging.warning('Hint: if you want to ignore this error, add '
                        '--ignore-errors option to the command line')
            raise e
        else:
            logging.warning('error ignored: failed to download %s', url)

def download_m3u8(url, filename, headers, args):
    """
    Downloads the given url in filename.
    """
    try:
        url = m3u8dl.choose_max_resolution(url, headers, args)
        m3u8dl.download_mp4(url, filename, headers, args)
    except Exception as e:
        logging.warning('Got error from m3u8dl: ', e)
        if not args.ignore_errors:
            logging.warning('Hint: if you want to ignore this error, add '
                            '--ignore-errors option to the command line')
            raise e
        else:
            logging.warning('error ignored: %s', e)

def skip_or_download(downloads, headers, args, f=download_url):
    """
    downloads url into filename using download function f,
    if filename exists it skips
    """
    for url, filename in downloads.items():
        if os.path.exists(filename):
            logging.info('[skipping] %s => %s', url, filename)
            continue
        else:
            logging.info('[download] %s => %s', url, filename)
        if args.dry_run:
            continue
        f(url, filename, headers, args)

def download_video(video_unit, args, target_dir, filename_prefix, headers):

    if args.m3u8 and len(video_unit.video_m3u8_urls)>0: 
        # if m3u8 not exist, fallback to mp4
        m3u8_downloads = _build_url_downloads(args, video_unit.video_m3u8_urls, target_dir, filename_prefix)
        skip_or_download(m3u8_downloads, headers, args, download_m3u8)
    
    elif len(video_unit.video_mp4_urls)>0:
        
        mp4_downloads = _build_url_downloads(args, video_unit.video_mp4_urls, target_dir, filename_prefix)
        skip_or_download(mp4_downloads, headers, args)
    
    else: 
        # force video link as mp4 download
        mp4_downloads = {url:
                        _build_filename_from_url(args, url, target_dir, filename_prefix)+'.mp4'
                        for url in video_unit.video_url}
        skip_or_download(mp4_downloads, headers, args)
        
    if args.subtitles:
        sub_downloads = _build_subtitles_downloads(args, video_unit, target_dir, filename_prefix, headers)
        skip_or_download(sub_downloads, headers, args, download_subtitle)

def save_webpage(content, filename, headers, args):
    with open(filename, 'w', encoding='utf8') as fp:
        fp.write(content)

def skip_or_save(downloads, data, headers, args, f=save_webpage):
    """
    downloads url into filename using download function f,
    if filename exists it skips
    """
    for url, filename in downloads.items():
        if os.path.exists(filename):
            logging.info('[skipping] %s => %s', url, filename)
            continue
        else:
            logging.info('[download] %s => %s', url, filename)
        if args.dry_run:
            continue
        f(data, filename, headers, args)

def download_page(webpage, args, target_dir, filename_prefix, headers):
    pagedownload = {webpage.url: os.path.join(target_dir, filename_prefix + '.html')}
    skip_or_save(pagedownload, webpage.content, headers, args)

def download_material(material_unit, args, target_dir, filename_prefix, headers):
    file_type = material_unit.url.rsplit('.',1)[1]
    file_downloads = {BASE_URL + material_unit.url: os.path.join(target_dir, filename_prefix + '.' + file_type)}
    skip_or_download(file_downloads, headers, args)

def download_unit(unit, args, target_dir, filename_prefix, headers):
    """
    Downloads the urls in unit based on args in the given target_dir
    with filename_prefix
    """
    if unit.type == 'video':
        download_video(unit, args, target_dir, filename_prefix, headers)
    elif unit.type == 'html':
        download_page(unit, args, target_dir, filename_prefix, headers)
    elif unit.type == 'file':
        download_material(unit, args, target_dir, filename_prefix, headers)

def download_course(args, course_block, headers, file_formats):
    """
    Downloads all the resources based on the selections
    """
    logging.info('Downloading %s [%s] sequentially', course_block.name, course_block.id)
    logging.info("Output directory: " + args.output_dir)

    coursename = clean_filename(course_block.name)
    base_dir = os.path.join(args.output_dir, coursename)

    # Download Videos
    for c,chapter in enumerate(course_block.children):
        chapter_dirname = clean_filename("%02d-%s" % (c+1, chapter.name))
        if args.shorten:
            chapter_dirname = chapter_dirname[:32].strip()
        for s,sequential in enumerate(chapter.children):
            sequential_dirname = clean_filename("%02d-%s" % (s+1, sequential.name))
            if args.shorten:
                sequential_dirname = sequential_dirname[:32].strip()
            target_dir = os.path.join(base_dir,chapter_dirname,sequential_dirname)
            mkdir_p(target_dir)
    
            for v,vertical in enumerate(sequential.children):
                vertical_name = clean_filename("%02d-%s" % (v+1,vertical.name))
                if args.shorten:
                    vertical_name = vertical_name[:32].strip()
                vunits = extract_units(vertical.url, headers, file_formats) 
                
                counter = 0
                for unitobj in vunits:
                    filename_prefix = vertical_name + '-' + ("%02d" % (counter))
                    download_unit(unitobj, args, target_dir, filename_prefix, headers)
                    counter += 1 

def ctrlc_handler(sig, frame):
    global pool
    pool.terminate()
    pool.join()
    raise(KeyboardInterrupt)

def pool_init(q):
    logger_init(q)
    # make it responsive to Ctrl-C
    signal.signal(signal.SIGINT, ctrlc_handler)

def download_course_parallel(args, course_block, headers, file_formats):
    """
    Downloads all the resources based on the selections
    """
    logging.info('Processing %s [%s] ', course_block.name, course_block.id)
    logging.info("Output directory: " + args.output_dir)

    coursename = clean_filename(course_block.name)
    base_dir = os.path.join(args.output_dir, coursename)

    # Download Videos
    try:
        argslist = []
        for c,chapter in enumerate(course_block.children):
            chapter_dirname = clean_filename("%02d-%s" % (c+1, chapter.name))
            for s,sequential in enumerate(chapter.children):
                sequential_dirname = clean_filename("%02d-%s" % (s+1, sequential.name))
                target_dir = os.path.join(base_dir,chapter_dirname,sequential_dirname)
                mkdir_p(target_dir)
        
                for v,vertical in enumerate(sequential.children):
                    vertical_name = clean_filename("%02d-%s" % (v+1,vertical.name))
                    vunits = extract_units(vertical.url, headers, file_formats) 

                    counter = 0
                    for unitobj in vunits:
                        filename_prefix = vertical_name + '-' + ("%02d" % (counter))
                        argslist.append((unitobj, args, target_dir, filename_prefix, headers))
                        counter += 1
        
        logging.info('Downloading %s [%s] in parallel', course_block.name, course_block.id)

        q_listener, q = setup_logger()
        global pool
        pool = Pool(int(args.process), pool_init, [q])
        pool.starmap(download_unit, argslist)
        
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()
        logging.warn("\n\nCTRL-C detected, shutting down....")

    finally:
        pool.close()
        pool.join()

    q_listener.stop()

# ####### main function

def main():
    """
    Main program function
    """
    args = parse_args()
    logging.info('edxdlr version %s', __version__)
    file_formats = parse_file_formats(args)

    # Query password, if not alredy passed by command line.
    if not args.password:
        args.password = getpass.getpass(stream=sys.stderr)

    if not args.username or not args.password:
        logging.error("You must supply username and password to log-in")
        sys.exit(ExitCode.MISSING_CREDENTIALS)
    
    # Prepare Headers and Session
    runtime.initialize()
    runtime.headers = edx_get_headers()

    # Login
    response = edx_login(args.username, args.password)
    if response.status_code != 200:
        logging.error("login failed")
        sys.exit(ExitCode.WRONG_EMAIL_OR_PASSWORD)

    # prompt for m3u8
    if args.m3u8:
        logging.info('To download using m3u8, please make sure ffmpeg is configured correctly.')
    
    # Parse and select the available courses
    runtime.headers.update({'Referer': DASHBOARD_URL})
    
    #username = get_username_from_cookies()
    courses = get_courses_info_from_json()
    available_courses = [course for course in courses if course.state == 'Started']
    selected_courses = parse_courses(args, available_courses)

    # Get all course blocks
    runtime.headers.update({'Referer': LEARNING_URL})
    runtime.headers.update({'Origin': LEARNING_URL})
    all_blocks = {selected_course:
                    get_available_blocks(selected_course.id)
                    for selected_course in selected_courses}
    for selected_course in selected_courses:
        _display_chapters(all_blocks[selected_course])

    # Download all resources
    runtime.headers.update({'Referer': BASE_URL})
    runtime.headers.update({'Origin': BASE_URL})
    if not args.process:   
        for course_block in all_blocks.values():
            download_course(args, course_block, runtime.headers, file_formats)
    else:
        for course_block in all_blocks.values():
            download_course_parallel(args, course_block, runtime.headers, file_formats)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("\n\nCTRL-C detected, shutting down....")
        sys.exit(ExitCode.OK)
