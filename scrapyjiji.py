#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Sebastien Bourdelin <sebastien.bourdelin@gmail.com>
#

import scrapy
import re
import geocoder
import folium
import os
import cPickle as pickle
from decimal import Decimal
from re import sub

from scrapy.crawler import CrawlerProcess
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

# Globals
DATABASE         = "map.db"

# Settings
MAP_LATLNG       = [45.5016889, -73.567256] # your city latitude and longitude (here: Montreal)
MAP_ZOOM         = 13       # default zoom
MIN_PRICE        = 600
MAX_PRICE        = 950
GREEN_PRICE      = 700
BLUE_PRICE       = 800
MAX_PAGE         = 2        # number of pages to parse (0 to 9)
USE_DB           = True     # if you want to use the already discover geocode
DRAW_ALL_DB      = False    # if you want to redraw the previously discover point store in the DB (DB must be active)
DRAW_NEW_AD_ONLY = False    # if you want to draw on map only the new ads, e.g: which are not in the DB
GEOLOCALISE      = True     # if you want to use geocoding services
SEARCH           = ""       # enter your search keyword here
MAPQUEST_API_KEY = ""       # you can request a mapquest api key here: https://developer.mapquest.com/plan_purchase/steps/business_edition/business_edition_free/register

# The following links depend on your city and your search categorie, it should be adjust accordingly
START_URL        = "http://www.kijiji.ca/b-appartement-condo/ville-de-montreal/%s/k0c37l1700281?ad=offering&siteLocale=en_CA&minNumberOfImages=1" % (SEARCH) if SEARCH else "http://www.kijiji.ca/b-appartement-condo/ville-de-montreal/c37l1700281?&siteLocale=en_CA&minNumberOfImages=1"
LINKS_NEXT_PAGE  = "http://www.kijiji.ca/b-appartement-condo/ville-de-montreal/%s" % (SEARCH) if SEARCH else "http://www.kijiji.ca/b-appartement-condo/ville-de-montreal"
LINKS_TO_FOLLOW  = "http://www.kijiji.ca/v-appartement-condo-.*"

class Appartement(scrapy.Item):
    """Definition of items which went to retrieve"""
    adId  = scrapy.Field()
    url = scrapy.Field()
    address = scrapy.Field()
    geocode = scrapy.Field()
    price = scrapy.Field()
    title = scrapy.Field()


class Kijiji(CrawlSpider):
    """Definition of the kijiji spider crawler"""
    m_map = folium.Map(location=MAP_LATLNG, zoom_start=MAP_ZOOM)
    m_list = []
    no_geocode = []
    new_items = 0
    name = "kijiji"
    allowed_domains = ["kijiji.ca"]
    start_urls = ["%s&price=%d__%d" % (START_URL, MIN_PRICE, MAX_PRICE)]
    rules = [
        # Extract link
        Rule(
            LinkExtractor(
                allow=[LINKS_TO_FOLLOW]
            ),
            callback='parse_item'),
        Rule(
            LinkExtractor(
                allow=["%s/page-[0-%d]/.*" % (LINKS_NEXT_PAGE, MAX_PAGE),
                       "%s/page-1[0-%d]/.*" % (LINKS_NEXT_PAGE, MAX_PAGE)]
            )
        )
    ]

    def __init__(self, *a, **kw):
        """Attach a callback to the spider_closed signal"""
        super(Kijiji, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        if USE_DB is True:
            self.open_database()
            if DRAW_ALL_DB is True and DRAW_NEW_AD_ONLY is False:
                # add already know marker
                for x in self.m_list:
                    self.add_marker(x, False)

    def open_database(self):
        if not os.path.exists(DATABASE):
            f = open(DATABASE, 'wb')
            f.close()

        f = open(DATABASE, 'rb')
        is_eof = f.readline()
        if len(is_eof) > 0:
            f.seek(0)
            self.m_list = pickle.load(f)

    def spider_closed(self, spider):
        """Handle the spider_closed event to save the map"""

        # create the special marker for all the ads without geocode
        print "found %d items without geocode" % (len(self.no_geocode))
        if len(self.no_geocode) > 0:
            html = ""
            for x in self.no_geocode:
                html += "<a href=%s target=_blank>%s</a> : %s<br>" % (x["url"], x["title"], x["price"])
            iframe  = folium.element.IFrame(html=html, width=500, height=100)
            popup   = folium.Popup(iframe, max_width=500)
            folium.Marker(MAP_LATLNG,
                          popup=popup,
                          icon=folium.Icon()).add_to(self.m_map)

        print "found %d new items" % (self.new_items)
        pickle.dump(self.m_list, open(DATABASE, 'wb'))
        self.m_map.save('map.html')

    def parse_item(self, response):
        """The item parser callback"""
        appartement = Appartement()

        appartement["adId"] = self._extract_id(response)

        # if the item is already in DB and has already been geolocalise
        # we draw the marker if it hasn't already been add at init
        for x in self.m_list:
            if (x["adId"] == appartement["adId"]):
                if DRAW_NEW_AD_ONLY is True:
                    return x
                if DRAW_ALL_DB is False:
                        self.add_marker(x, False)
                return x

        # otherwise this is a new item
        self.new_items += 1
        appartement["url"] = response.url
        appartement["address"] = self._extract_field(response, "Address")
        appartement["geocode"] = self.geocode(appartement["address"])
        appartement["price"] = self._extract_field(response, "Price")
        appartement["title"] = self._extract_title(response)

        # no geocode found
        if appartement["geocode"] is MAP_LATLNG:
            self.no_geocode.append(appartement)
            return appartement

        # add new marker
        self.add_marker(appartement, True)
        # store the item in the DB
        self.m_list.append(appartement)

        return appartement

    def add_marker(self, appartement, is_new):
        """Helper function to add a marker on the map"""
        if is_new is False:
            icon='info-sign'
        else:
            icon='star'

        folium.Marker(appartement["geocode"],
                      popup=self.popup(appartement),
                      icon=folium.Icon(color=self.color_price(appartement), icon=icon)).add_to(self.m_map)

    def popup(self, appartement):
        """Helper function to create a popup with appartement informations"""
        html    = "<a href=%s target=_blank>%s</a><br>%s" % (appartement["url"], appartement["title"], appartement["price"])
        iframe  = folium.element.IFrame(html=html, width=500, height=100)
        popup   = folium.Popup(iframe, max_width=500)

        return popup

    def color_price(self, appartement):
        """Helper function to return a color for marker based on price"""
        if appartement["price"] is None:
            return 'red'
        else:
            price = Decimal(sub(r'[^\d.]', '', appartement["price"]))

        if price < GREEN_PRICE:
                color = 'green'
        elif price < BLUE_PRICE:
                color = 'blue'
        else:
                color = 'red'

        return color

    def geocode(self, address):
        """Retrieve the lat and long using different fallback services"""
        if GEOLOCALISE is False:
            return MAP_LATLNG

        g = geocoder.google(address)
        if not g.latlng:
            g = geocoder.osm(address)
            if not g.latlng and MAPQUEST_API_KEY:
                g = geocoder.mapquest(address, key=MAPQUEST_API_KEY)

        # if we can't geocode the address, we return the map center
        if g.latlng:
            return g.latlng
        else:
            return MAP_LATLNG

    def _extract_id(self, response):
        """Retrieve the id based on xpath"""
        l = " ".join(response.xpath("//div[contains(@id, 'Breadcrumb')]/strong/text()").extract())
        l = " ".join(re.findall(r"\d+", l))
        return l.strip() if l else None

    def _extract_title(self, response):
        """Retrieve the title based on xpath"""
        l = " ".join(response.xpath("//h1/text()").extract())
        return l.strip() if l else None

    def _extract_field(self, response, fieldname):
        """Retrieve the html field based on xpath"""
        l = response.xpath("//th[contains(text(), '{0}')]/following::td[1]//./text()".
                           format(fieldname)).extract()
        return l[0].strip() if l else None


# Entry point
process = CrawlerProcess({
    'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
})

# Loading
process.crawl(Kijiji)
process.start()
