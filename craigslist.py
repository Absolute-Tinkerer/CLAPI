# -*- coding: utf-8 -*-
"""
Created on Sat May  1 12:13:59 2021

@author: The Absolute Tinkerer
"""

import os
import sys
import math
import shutil
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from .viewer import MainWindowHandlers

from PyQt5.QtWidgets import QApplication


class Post:
    GPS = 'https://www.google.com/maps/search/%s,%s'  # lat, long

    def __init__(self, city, recordSoup):
        """
        Constructor

        Parameters:
        -----------
        city : str
            The post city (the city from the craigslist url)
        recordSoup : BeautifulSoup
            The html loaded into a BeautifulSoup instance for a particular
            post. The post section must have originated from the Craigslist
            search results page
        """
        # Collect the post id, datetime, post url, post title, price, "hood",
        # image urls, and google maps url of this post
        pid = recordSoup['data-pid']
        dt = recordSoup.findAll('time', {'class': 'result-date'})[0]
        dt = datetime.strptime(dt['datetime'], '%Y-%m-%d %H:%M')
        url = recordSoup.findAll('a', {'class': 'result-title hdrlnk'})[0]
        text = url.text
        url = url['href']

        price = recordSoup.findAll('span', {'class': 'result-meta'})[0]
        hood = price.findAll('span', {'class': 'result-hood'})
        price = price.findAll('span', {'class': 'result-price'})
        # sometimes there is no price
        if len(price) == 0:
            price = 0
        else:
            price = int(price[0].text.replace('$', '').replace(',', ''))        
        # sometimes there is no hood
        if len(hood) == 0:
            hood = city
        else:
            hood = hood[0].text.strip()[1:-1]

        # Sometimes there are no pictures
        imgs = recordSoup.findAll('a', {'class': 'result-image gallery'})
        if len(imgs) == 0:
            self._img_urls = []
        else:
            base_url = CraigsList.IMG_URL
            items = imgs[0]['data-ids'].split(',')
            self._img_urls = [base_url % item.split(':')[1] for item in items]

        # Bind to class variables
        self._pid = pid
        self._dt = dt
        self._url = url
        self._text = text
        self._price = price
        self._city = city
        self._hood = hood
        # Since this requires a separate request, only get if the user calls
        # the property
        self._gps = None

    """
    ##########################################################################
                                Public Functions
    ##########################################################################
    """
    def downloadImages(self, folder, fmt='jpg', maxImgs=-1):
        """
        Public function used to download the images for this post. All images
        are 300x300 pixels (CL's thumbnail size).

        Parameters:
        -----------
        folder : str
            The output folder
        fmt : str
            The output format
        maxImgs : int
            -1 if you want all images, otherwise specify the maximum allowed
            images to download
        """
        for i, url in enumerate(self.image_urls):
            if maxImgs != -1 and i >= maxImgs:
                break
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                fname = '%s/%s_%s.%s' % (folder, self.pid, i, fmt)
                with open(fname, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)

    """
    ##########################################################################
                                Properties
    ##########################################################################
    """
    @property
    def pid(self):
        return self._pid

    @property
    def dt(self):
        return self._dt

    @property
    def url(self):
        return self._url

    @property
    def image_urls(self):
        return self._img_urls

    @property
    def text(self):
        return self._text

    @property
    def price(self):
        return self._price

    @property
    def city(self):
        return self._city

    @property
    def hood(self):
        return self._hood

    @property
    def gps(self):
        if self._gps is None:
            self._gps = self._getGPSLocation()
        return self._gps

    """
    ##########################################################################
                                Private Functions
    ##########################################################################
    """
    def _getGPSLocation(self):
        """
        Private function used to retrieve the google maps url to this post
        """
        # Make our request
        params = {}
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64'}
        response = requests.get(url=self.url,
                                headers=headers,
                                params=params)

        # If there was an error, a non-200 status code is thrown
        if response.status_code != 200:
            s = 'Failed to fetch requested data with status code: %s'
            raise Exception(s % response.status_code)

        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Get lat & long
        ll = soup.findAll('div', {'class': 'viewposting'})[0]

        return self.GPS % (ll['data-latitude'], ll['data-longitude'])

    """
    ##########################################################################
                                Built-In Functions
    ##########################################################################
    """
    def __str__(self):
        return '%s:%s: %s | $%s' % (self.city, self.hood,
                                    self.text, self.price)


class CraigsList:
    BASE_URL = 'https://%s.craigslist.org'
    GEO_URL = 'https://geo.craigslist.org/iso/us/%s'
    URL = 'https://%s.craigslist.org/d/for-sale/search/sss?query=%s&sort=%s'
    IMG_URL = 'https://images.craigslist.org/%s_300x300.jpg'
    SORT_RELEVANT = 'rel'
    SORT_ASCENDING = 'priceasc'
    SORT_DECENDING = 'pricedsc'
    NUM_PAGE_RECORDS = 120

    def __init__(self, city, query, sortby, lookback=-1):
        """
        Constructor

        Parameters:
        -----------
        city : str
            The city you're getting posts from. Must be a valid token for a
            CraigsList url
        query : str
            The query string you want to search
        sortby : str
            Either of SORT_RELEVANT, SORT_ASCENDING, or SORT_DECENDING
        lookback : float
            The number of days in the past you want to get posts for. -1 if
            you want all posts
        """
        query = '+'.join([requests.utils.quote(q) for q in query.split(' ')])

        # Bind to class variables
        self._city = city.lower().replace(' ', '')
        self._query = query
        self._sortby = sortby
        self._lookback = lookback
        self._posts = []
        self._start = datetime.now()

        # Make our query
        self._makeQuery()

    """
    ##########################################################################
                                Properties
    ##########################################################################
    """
    @property
    def city(self):
        return self._city

    @property
    def query(self):
        return self._query

    @property
    def sortby(self):
        return self._sortby

    @property
    def lookback(self):
        return self._lookback

    @property
    def posts(self):
        return self._posts

    """
    ##########################################################################
                                Private Functions
    ##########################################################################
    """
    @staticmethod
    def _getSoup(url, params, headers):
        """
        Private static function used to get the soup from a specific request

        Parameters:
        -----------
        url : str
            The url the request is being made to
        params : dict
            The parameters you want to pass in
        headers : dict
            The associated headers for the request

        Returns:
        --------
        <value> : BeautfulSoup
            The soup from the reponse's html
        """
        # Make our request
        response = requests.get(url=url,
                                headers=headers,
                                params=params)

        # If there was an error, a non-200 status code is thrown
        if response.status_code != 200:
            s = 'Failed to fetch requested data with status code: %s'
            raise Exception(s % response.status_code)

        # Parse with BeautifulSoup
        return BeautifulSoup(response.content, 'html.parser')

    def _makeQuery(self):
        """
        Private function used to make the specific query to CraigsList and
        put all posts into the list of Post objects (self._posts)
        """
        # Build the url, parameters, and headers for the initial request
        url = self.URL % (self.city, self.query, self.sortby)
        params = {'sort': self.sortby,
                  'query': self.query}
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64'}

        # Get the total record count
        soup = self._getSoup(url, params, headers)
        n_recs = soup.findAll('span', {'class', 'totalcount'})

        # Not always going to have a response - this means there are zero
        # posts
        if len(n_recs) > 0:
            n_recs = int(n_recs[0].text)
        else:
            return

        # Initialize the data object with the starting page
        for item in soup.findAll('li', {'class', 'result-row'}):
            post = Post(self.city, item)
            if(self._lookback != -1 and
               post.dt < self._start - timedelta(days=self._lookback)):
                return
            self._posts.append(post)

        # Get records after the first page
        for i in range(math.ceil(n_recs/self.NUM_PAGE_RECORDS)-1):
            params['s'] = str((i+1)*self.NUM_PAGE_RECORDS)
            soup = self._getSoup(url, params, headers)
            for item in soup.findAll('li', {'class': 'result-row'}):
                post = Post(self.city, item)
                if(self._lookback != -1 and
                   post.dt < self._start - timedelta(days=self._lookback)):
                    return
                self._posts.append(post)

    """
    ##########################################################################
                                Static Functions
    ##########################################################################
    """
    @staticmethod
    def OpenViewer(posts, maxImgs=-1):
        """
        Static function to open a local GUI to view annotated versions of
        posts. The post images will be downloaded to a local, temporary
        directory and discarded when the viewer is closed

        Parameters:
        -----------
        posts : list<Post>
            List of Post objects
        maxImgs : int
            The maximum number of images per post you want to download. -1 if
            you want all images.
        """
        folder = 'tmp'
        def saveImages():
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.mkdir(folder)
    
            for j, post in enumerate(posts):
                print('Post (%s/%s) images downloading.' % (
                    j+1, len(posts)))
                post.downloadImages(folder, maxImgs=maxImgs)
        def rmImages():
            if os.path.exists(folder):
                shutil.rmtree(folder)

        # Download all images
        saveImages()

        # Initialize the application
        app = QApplication(sys.argv)
        window = MainWindowHandlers()

        # Now call the initialize function on this window
        window.initialize(posts)
        window.show()
        app.exec_()

        # Remove all images
        rmImages()

    @staticmethod
    def GetNearbyCities(city):
        """
        Static function used to retrieve a list of nearby cities to the
        provided city

        Parameters:
        -----------
        city : str
            The city name in the CraigsList url format

        Returns:
        --------
        cities : list<str>
            A list of city names in string form, in the Craigslist url format
        """
        # Build the url, parameters, and headers
        url = CraigsList.BASE_URL % city
        params = {}
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64'}

        # Get the soup
        soup = CraigsList._getSoup(url, params, headers)

        # Get all nearby URLs
        cities = []
        group = soup.findAll('ul', {'class': 'acitem'})[0]
        for sub_item in group.findAll('li', {'class': 's'}):
            link = sub_item.findAll('a')[0]['href']
            cities.append(link.replace('/', '').split('.')[0])

        return cities

    @staticmethod
    def GetCitiesByState(state):
        """
        Get the cities with CraigsList from the provided state, in two-letter
        postal-code form

        Parameters:
        -----------
        state : str
            The postal-code format of the state of interest

        Returns:
        --------
        cities : list<str>
            A list of city names in string form, in the Craigslist url format
        """
        # Build the url, parameters, and headers
        url = CraigsList.GEO_URL % state.lower()
        params = {}
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64'}

        # Get the soup
        soup = CraigsList._getSoup(url, params, headers)

        # Get all cities
        cities = []
        group = soup.findAll('ul', {'class': 'geo-site-list'})[0]
        for sub_item in group.findAll('a'):
            link = sub_item['href']
            cities.append(link.replace('https://', '').split('.')[0])

        return cities
