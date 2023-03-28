# -*- coding: utf-8 -*-

"""
Common type definitions and constants for edx-dl

The classes in this module represent the structure of courses in edX.  The
structure is:

* A Course contains Sections
* Each Section contains Subsections
* Each Subsection contains Units

Notice that we don't represent the full tree structure for both performance
and UX reasons:

Course ->  [Section] -> [SubSection] -> [Unit] -> [Video]

In the script the data structures used are:

1. The data structures to represent the course information:
   Course, Section->[SubSection]

2. The data structures to represent the chosen courses and sections:
   selections = {Course, [Section]}

3. The data structure of all the downloable resources which represent each
   subsection via its URL and the of resources who can be extracted from the
   Units it contains:
   all_units = {Subsection.url: [Unit]}

4. The units can contain multiple videos:
   Unit -> [Video]
"""

# The new structure is [Course]->[Chapter]->[Sequential]->[Vertical]

from urllib.request import urlcleanup


class Course(object):
    """
    Course class represents course information.
    """
    def __init__(self, id, name, url, state):
        """ course-v1:DoaneX+BIOL-295x+2T2020/home
        @param id: The id of a course in edX is composed by the path
            https://learning.edx.org/course/{course_id}/
        @type id: str or None

        @param name: Name of the course. The name is taken from course page
            h3 header.
        @type name: str

        @param url: URL of the course.
        @type url: str or None

        @param state: State of the course. One of the following values:
            * 'Not yet'
            * 'Started'
        @type state: str
        """
        self.id = id
        self.name = name
        self.url = url
        self.state = state

    def __repr__(self):
        url = self.url if self.url else "None"
        return self.name + ": " + url

class ExitCode(object):
    """
    Class that contains all exit codes of the program.
    """
    OK = 0
    MISSING_CREDENTIALS = 1
    WRONG_EMAIL_OR_PASSWORD = 2
    MISSING_COURSE_URL = 3
    INVALID_COURSE_URL = 4
    UNKNOWN_PLATFORM = 5
    NO_DOWNLOADABLE_VIDEO = 6

DEFAULT_CACHE_FILENAME = 'edx-dl.cache'
DEFAULT_FILE_FORMATS = ['eps', 'pdf', 'txt', 'doc', 'xls', 'ppt',
                        'docx', 'xlsx', 'pptx', 'odt', 'ods', 'odp', 'odg',
                        'zip', 'rar', 'gz', 'mp3', 'R', 'Rmd', 'ipynb', 'py']

#CHANGES: introduce new Block classes
class Block(object):
    """
    A tree of Blocks
    """
    def __init__(self, position, content):
        self.position = position
        self.name = content['display_name']
        self.type = content['type']
        self.id = content['id']
        self.url = content['lms_web_url']
        self.resource = None
        try:
            self.childrenid = content['children']
        except: # verticals childrenid are non-existent
            self.childrenid = []
        
        self.children = None # wait to be sorted later

    def __repr__(self):
        return self.name + ": " + str(len(self.chapters())) + " chapters"

    def treeview(self):
        contents = str(self.name)
        if self.children:
            contents = contents + '[' + ','.join([c.treeview() for c in self.children]) + ']'
        return str(contents)

    def chapters(self):
        if self.type == 'chapter':
            chapter_block = [self]
        else:
            chapter_block = []
        for x in self.children:
            chapter_block = chapter_block + x.chapters()
        return chapter_block

    def sequentials(self):
        if self.type == 'sequential':
            sequential_block = [self]
        else:
            sequential_block = []
        for x in self.children:
            sequential_block = sequential_block + x.sequentials()        
        return sequential_block

    def verticals(self):
        if self.type == 'vertical':
            vertical_block = [self]
        else:
            vertical_block = []
        for x in self.children:
            vertical_block = vertical_block + x.verticals()
        
        return vertical_block

class Unit(object):
    """
    Modified from the old Unit
    """
    def __init__(self, url, unittype):
        """
        url link
        unittype page, video, file
        """
        self.type = ''
        self.content = None

class WebPage(object):
    """
    Representation of a web page (of vertical blocks), data of Unit
    """  
    def __init__(self, url, content):
        self.url = url
        self.type = 'html'
        self.content = content

class Material(object):
    """
    Representation of a file, data of Unit
    """
    def __init__(self, url):
        self.url = url
        self.type = 'file'
        self.content = None
        
class Video(object):
    """
    Representation of a single video. data of Unit
    """
    def __init__(self, jsontext):
        self.type = 'video'
        self.video_baseurl = jsontext['lmsRootURL']
        self.video_url = jsontext['sources']
        self.video_mp4_urls = [url for url in jsontext['sources'] if url.endswith('.mp4')]
        self.video_m3u8_urls = [url for url in jsontext['sources'] if url.endswith('.m3u8')]
        self.subs_available_url = jsontext['transcriptAvailableTranslationsUrl']
        self.subs_template_url = jsontext['transcriptTranslationUrl']
        self.subs_languages = jsontext['transcriptLanguage']