#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This module contains generic functions, ideally useful to any other module
from six.moves.urllib.request import urlopen, Request
import sys
if sys.version_info[0] >= 3:
    import html
else:
    from six.moves import html_parser    
    html = html_parser.HTMLParser()

import errno
import json
import logging
import os
import string
import subprocess
import runtime

def get_filename_from_prefix(target_dir, filename_prefix):
    """
    Return the basename for the corresponding filename_prefix.
    """
    # This whole function is not the nicest thing, but isolating it makes
    # things clearer. A good refactoring would be to get the info from the
    # video_url or the current output, to avoid the iteration from the
    # current dir.
    filenames = os.listdir(target_dir)
    for name in filenames:  # Find the filename of the downloaded video
        if name.startswith(filename_prefix):
            basename, _ = os.path.splitext(name)
            return basename
    return None


def execute_command(cmd, args):
    """
    Creates a process with the given command cmd.
    """
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        if args.ignore_errors:
            logging.warn('External command error ignored: %s', e)
        else:
            raise e


def directory_name(initial_name):
    """
    Transform the name of a directory into an ascii version
    """
    result = clean_filename(initial_name)
    return result if result != "" else "course_folder"


def post_page_contents(url, headers, postdata):
    response = runtime.session.post(url, data=postdata, headers=headers)
    if response.status_code == 200:
        return response.content.decode('utf-8')
    else:
        return ''

def get_page_contents(url, headers, params=None):
    """
    Get the contents of the page at the URL given by url. While making the
    request, we use the headers given in the dictionary in headers.
    """
    if not params is None:
        url = url+'?'+params
    response = runtime.session.get(url, params=params, headers=headers)
    if response.status_code == 200:
        return response.content.decode('utf-8')
    else:
        return ''


def post_page_contents_as_json(url, headers, postdata):
    # CHANGE: add new Post method
    json_string = post_page_contents(url, headers, postdata)
    json_object = json.loads(json_string)
    return json_object


def get_page_contents_as_json(url, headers, params=None):
    """
    Makes a request to the url and immediately parses the result asuming it is
    formatted as json
    """
    json_string = get_page_contents(url, headers, params)
    json_object = json.loads(json_string)
    return json_object

def remove_duplicates(orig_list, seen=set()):
    """
    Returns a new list based on orig_list with elements from the (optional)
    set seen and elements of orig_list removed.

    The function tries to maintain the order of the elements in orig_list as
    much as possible, only "removing" a given element if it appeared earlier
    in orig_list or if it was already a member of seen.

    This function does *not* modify any of its input parameters.
    """
    new_list = []
    new_seen = set(seen)

    for elem in orig_list:
        if elem not in new_seen:
            new_list.append(elem)
            new_seen.add(elem)

    return new_list, new_seen


# The next functions come from coursera-dl/coursera
def mkdir_p(path, mode=0o777):
    """
    Create subdirectory hierarchy given in the paths argument.
    """
    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def clean_filename(s, minimal_change=True):
    """
    Sanitize a string to be used as a filename.
    If minimal_change is set to true, then we only strip the bare minimum of
    characters that are problematic for filesystems (namely, ':', '/' and
    '\x00', '\n').
    """

    # First, deal with URL encoded strings
    h = html
    s = h.unescape(s)

    # remove reserved characters <>:"/\|?* for windows
    s = (
        s.replace(':', '')
        .replace('?', '')
        .replace('"', '')
        .replace('<', '_') 
        .replace('>', '_')
        .replace('/', '-')
        .replace('|', '-')
        .replace('\\', '-')
        .replace('*', '-')
        .replace('\x00', '-')
        .replace('\n', '')
        .replace('\t', '')
        .strip(' ')  # Unpredictable spaces that disrupt the os
        .rstrip('.') # Remove excess of trailing dots
    )

    if minimal_change:
        return s

    s = s.replace('(', '').replace(')', '')
    s = s.strip().replace(' ', '_')
    valid_chars = '-_.()%s%s' % (string.ascii_letters, string.digits)
    return ''.join(c for c in s if c in valid_chars)
