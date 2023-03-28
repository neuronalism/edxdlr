#!/usr/bin/env python
# -*- coding: utf-8 -*-

# this module shares variables across files

import requests

global session
global headers

def initialize():
    global session
    global headers
    session = requests.session()
    headers = []
