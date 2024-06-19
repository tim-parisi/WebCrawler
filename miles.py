#!/usr/bin/env python3

''' miles.py - Web crawler to download files in parallel. '''

from typing import Iterator, Optional

import os
import concurrent.futures
import itertools
import re
import sys
import tempfile
import time
import urllib.parse

import requests

# Constants

FILE_REGEX = {
    'jpg': [r'<img.*src="?([^\" ]+.jpg)', r'<a.*href="?([^\" ]+.jpg)'],  # TODO
    'mp3': [r'<audio.*src="?([^\" ]+.mp3)', r'<a.*href="?([^\" ]+.mp3)'],  # TODO
    'pdf': [r'<a.*href="?([^\" ]+.pdf)'],  # TODO
    'png': [r'<img.*src="?([^\" ]+.png)', r'<a.*href="?([^\" ]+.png)'],  # TODO
}

MEGABYTES   = 1<<20
DESTINATION = '.'
CPUS        = 1

# Functions

def usage(exit_status: int=0) -> None:
    ''' Print usgae message and exit. '''
    print(f'''Usage: miles.py [-d DESTINATION -n CPUS -f FILETYPES] URL

Crawl the given URL for the specified FILETYPES and download the files to the
DESTINATION folder using CPUS cores in parallel.

    -d DESTINATION      Save the files to this folder (default: {DESTINATION})
    -n CPUS             Number of CPU cores to use (default: {CPUS})
    -f FILETYPES        List of file types: jpg, mp3, pdf, png (default: all)

Multiple FILETYPES can be specified in the following manner:

    -f jpg,png
    -f jpg -f png''', file=sys.stderr)
    sys.exit(exit_status)

def resolve_url(base: str, url: str) -> str:
    ''' Resolve absolute url from base url and possibly relative url.

    >>> base = 'https://www3.nd.edu/~pbui/teaching/cse.20289.sp24/'
    >>> resolve_url(base, 'static/img/ostep.jpg')
    'https://www3.nd.edu/~pbui/teaching/cse.20289.sp24/static/img/ostep.jpg'

    >>> resolve_url(base, 'https://automatetheboringstuff.com/')
    'https://automatetheboringstuff.com/'
    '''
    if 'https://' in url:
        return url
    else:
        return urllib.parse.urljoin(base, url)

def extract_urls(url: str, file_types: list[str]) -> Iterator[str]:
    ''' Extract urls of specified file_types from url.

    >>> url = 'https://www3.nd.edu/~pbui/teaching/cse.20289.sp24/'
    >>> extract_urls(url, ['jpg']) # doctest: +ELLIPSIS
    <generator object extract_urls at ...>

    >>> len(list(extract_urls(url, ['jpg'])))
    2
    '''
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return
    data = response.text
    for filetype in file_types:
        for regex in FILE_REGEX[filetype]:
            for match in re.findall(regex, data):
                yield resolve_url(url, match)

def download_url(url: str, destination: str=DESTINATION) -> Optional[str]:
    ''' Download url to destination folder.

    >>> url = 'https://www3.nd.edu/~pbui/teaching/cse.20289.sp24/static/img/ostep.jpg'
    >>> destination = tempfile.TemporaryDirectory()

    >>> path = download_url(url, destination.name)
    Downloading https://www3.nd.edu/~pbui/teaching/cse.20289.sp24/static/img/ostep.jpg...

    >>> path # doctest: +ELLIPSIS
    '/tmp/.../ostep.jpg'

    >>> os.stat(path).st_size
    53696

    >>> destination.cleanup()
    '''
    print(f'Downloading {url}...')
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    if url[-1] == '/':
        url = url[:-1]
    filename = os.path.join(destination, os.path.basename(url))
    with open(filename, 'wb') as stream:
        stream.write(response.content)
    return str(filename)
        

def crawl(url: str, file_types: list[str], destination: str=DESTINATION, cpus: int=CPUS) -> None:
    ''' Crawl the url for the specified file type(s) and download all found
    files to destination folder.

    >>> url = 'https://www3.nd.edu/~pbui/teaching/cse.20289.sp24/'
    >>> destination = tempfile.TemporaryDirectory()
    >>> crawl(url, ['jpg'], destination.name) # doctest: +ELLIPSIS
    Files Downloaded: 2
    Bytes Downloaded: 0.07 MB
    Elapsed Time:     ... s
    Bandwidth:        0... MB/s

    >>> destination.cleanup()
    '''
    sites = extract_urls(url, file_types)
    dests = itertools.repeat(destination)
    file_num = 0
    start = time.time()
    files = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpus) as executor:
        for file in executor.map(download_url, sites, dests):
            if not file:
                continue
            file_num += 1
            files.append(file)
    total_time = float(time.time()) - start
    size_list = (os.stat(file).st_size for file in files)
    size_total = sum(size_list) / 1048576
    download_speed: float = size_total/total_time
    print(f'Files Downloaded: {file_num}')
    print(f'Bytes Downloaded: {size_total:.2f} MB')
    print(f'Elapsed Time:     {total_time:.2f} s')
    print(f'Bandwidth:        {download_speed:.2f} MB/s')


# Main Execution

def main(arguments=sys.argv[1:]) -> None:
    ''' Process command line arguments, crawl URL for specified FILETYPES,
    download files to DESTINATION folder using CPUS cores.

    >>> url = 'https://www3.nd.edu/~pbui/teaching/cse.20289.sp24/'
    >>> destination = tempfile.TemporaryDirectory()
    >>> main(f'-d {destination.name} -f jpg {url}'.split()) # doctest: +ELLIPSIS
    Files Downloaded: 2
    Bytes Downloaded: 0.07 MB
    Elapsed Time:     0... s
    Bandwidth:        0... MB/s

    >>> destination.cleanup()
    '''
    destination = ''
    filetypes: list[str] = []
    cpus = CPUS
    url = ''
    while arguments:
        argument = arguments.pop(0)
        if argument == '-d':
            directory = arguments.pop(0)
            if os.path.exists(directory):
                destination = directory
            else:
                os.makedirs(directory)
                destination = directory
        elif argument == '-f':
            filetypes += arguments.pop(0).split(',')
        elif argument == '-h':
            usage(0)
        elif argument == '-n':
            cpus = int(arguments.pop(0))
        elif argument[0] == '-':
            usage(1)
        else:
            if url == '':
                url = argument
            else:
                usage(1)
    if not filetypes:
        filetypes = ['mp3', 'png', 'jpg', 'pdf']
    if not url:
        usage(1)
    crawl(url, filetypes, destination, cpus)
if __name__ == '__main__':
    main()
