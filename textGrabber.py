#!/usr/bin/env python3

''' textGrabber.py - Script to download text from a website '''

import sys
import time
from bs4 import BeautifulSoup as soup
import requests

# Constants

DESTINATION = 'text_grabber_data.txt'
URL = 'https://automatetheboringstuff.com'

# Functions

def usage(exit_status: int=0) -> None:
    ''' Print usgae message and exit. '''
    print(f'''Usage: textGrabber.py [-d DESTINATION] URL

Download the text of the given url.
    -d DESTINATION      Save the files to this file (default: {DESTINATION})
''', file=sys.stderr)
    sys.exit(exit_status)

def download_html(url: str) -> str:
    ''' Download url and return html as string
    '''
    print(f'Downloading {url}...')
    start = time.time()
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return ''
    if url[-1] == '/':
        url = url[:-1]
    total_time = float(time.time()) - start
    print(f'Elapsed Time:     {total_time:.2f} s')
    return response.text
    
def format_remove_html(html_data: str, destination: str):
    ''' Removes everything but plaintext from html file and writes to specified file
    '''
    file_soup = soup(html_data, 'html.parser')
    with open(destination, 'w') as write_stream:
        write_stream.write(file_soup.get_text())

# Main Execution
def main(arguments=sys.argv[1:]) -> None:
    ''' Download html data, format into plaintext, save to file
    '''
    destination = DESTINATION
    url = URL
    url_set = 0
    while arguments:
        argument = arguments.pop(0)
        if argument == '-d':
            destination = arguments.pop(0)
        elif argument == '-h':
            usage(0)
        else:
            if url_set == 1:
                usage(1)
            url_set = 1
            url = argument
    html_data = download_html(url)
    if not html_data:
        exit(1)
    format_remove_html(html_data, destination)
    print(f'Saved to {destination}')
    
if __name__ == '__main__':
    main()
