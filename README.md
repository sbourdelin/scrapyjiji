# scrapyjiji
Scrape and localise kijiji ads out of a map.

![map](https://raw.githubusercontent.com/sbourdelin/scrapyjiji/master/map.png)

This tool has been inspired by the scrapy crawler [kijiji_scraper](https://github.com/mfournierca/kijiji_scraper).
It is not intended to be generic but can be easily adapted to fit your needs.

The scraper is based on the [scrapy framework](http://scrapy.org) to retrieve attributes like the title, address and price of an ad.
The kijiji start url should use the english locale setting to be scraped.

The geocoding is based on the [geocoder module](https://pypi.python.org/pypi/geocoder) and uses the following geocoding services: google, osm, mapquest.
Take a look at the geocoder providers informations to know limits of each services (for example mapquest requires an API key).

The map is generated using the [folium module](https://pypi.python.org/pypi/folium) with the default setting to use the openstreetmap tile.

#### Prerequisites:
Due to the scrapy limitation, this script only work on Python 2.

**Packages requirements**:
* scrapy v1.0.5
* geocoder v1.9.0
* folium v0.2.0

Each packages can be install using pip:
```
$ pip install <package>
```

#### How it works:
Enter the following to generate the map, and let it run until the end otherwise the map won't be generated.
*note:* it could take few minutes depending the number of pages you want to scrap.

```
$ ./scrapyjiji
```

Open the generate map file in your browser:
```
$ firefox map.html
```
