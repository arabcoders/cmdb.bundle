# -*- coding: utf-8 -*-

### Imports ###
import sys                  # getdefaultencoding, getfilesystemencoding, platform, argv
import os                   # path.abspath, join, dirname
import re                   #
import inspect              # getfile, currentframe
import urllib              #
import urllib2              #
import json

### Mini Functions ###
# Avoid 1, 10, 2, 20... #Usage: list.sort(key=natural_sort_key), sorted(list, key=natural_sort_key)


def natural_sort_key(s): return [int(text) if text.isdigit(
) else text for text in re.split(re.compile('([0-9]+)'), str(s).lower())]
# Make sure the path is unicode, if it is not, decode using OS filesystem's encoding ###


### Variables ###
PluginDir = os.path.abspath(os.path.join(os.path.dirname(
    inspect.getfile(inspect.currentframe())), "..", ".."))
PlexRoot = os.path.abspath(os.path.join(PluginDir, "..", ".."))

### Get media directory ###
RX_LIST = []

DEFAULT_RX = [
    # YY?YY(-._)MM(-._)DD -? series -? epNumber -? title
    '^(?P<year>\d{2,4})(\-|\.|_)?(?P<month>\d{2})(\-|\.|_)?(?P<day>\d{2})\s-?(?P<series>.+?)(?P<epNumber>\#(\d+)|ep(\d+)|DVD[0-9.-]+|SP[0-9.-]+) -?(?P<title>.+)',
    # YY?YY(-._)MM(-._)DD -? title
    '^(?P<year>\d{2,4})(\-|\.|_)?(?P<month>\d{2})(\-|\.|_)?(?P<day>\d{2})\s?-?(?P<title>.+)',
    # title YY?YY(-._)MM(-._)DD at end of filename.
    '(?P<title>.+?)(?P<year>\d{2,4})(\-|\.|_)?(?P<month>\d{2})(\-|\.|_)?(?P<day>\d{2})$',
    # series - YY?YY(-._)MM(-._)DD -? title
    '(?P<series>.+?)(?P<year>\d{2,4})(\-|\.|_)?(?P<month>\d{2})(\-|\.|_)?(?P<day>\d{2})\s?-?(?P<title>.+)?',
    # series ep0000 Title
    '(?P<series>.+?)\s?(ep|sp|\#|S)(?P<episode>[0-9]{1,4})\s? \-?(?P<title>.+)',
    # S00E00 - Title
    '^[Ss](?P<season>[0-9]{1,2})[Ee](?P<episode>[0-9]{1,4})\s?-?(?P<title>.+)',
    # Title ep0000
    '(?P<title>.+?)\s?[Ee][Pp](?P<episode>[0-9]{1,4})$',
]

# load custom path from env
customFile = os.path.join(PlexRoot, 'jp_scanner.json')
if os.path.exists(os.path.join(customFile)):
    try:
        data = json.load(Core.storage.load(customFile))
        for rx in data:
            if not rx:
                continue
            try:
                pat = re.compile(rx, re.IGNORECASE)
                RX_LIST.append(pat)
            except Exception as e:
                Log.Error("Error compiling custom regex: " +
                          str(rx) + " - " + str(e))
    except Exception as e:
        Log.Error(
            "Error loading custom regex file [%s] - [%s]" % (customFile, str(e)))

# Load default scanner regex.
for rx in DEFAULT_RX:
    try:
        pat = re.compile(rx, re.IGNORECASE)
        RX_LIST.append(pat)
    except Exception as e:
        Log.Error("Error compiling regex: " + str(rx) + " - " + str(e))


def Start():
    HTTP.CacheTime = 0
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.54'
    HTTP.Headers['Accept-Language'] = 'en-us'


class CustomMetadataDBSeries(Agent.TV_Shows):
    name = 'Custom Metadata DB Agent'
    primary_provider = True
    fallback_agent = None
    contributes_to = None
    accepts_from = ['com.plexapp.agents.xbmcnfotv',
                    'com.plexapp.agents.localmedia']
    languages = [Locale.Language.NoLanguage]

    def search(self, results,  media, lang, manual):
        json = self.searchCustomDB('series', media.show)
        if not json:
            Log(u"Search() - No results found for: [{}]".format(media.show))
            return

        Log(u"Search() - id: {}, title: {}".format(json['id'], json['title']))
        results.Append(MetadataSearchResult(
            id=json['id'],
            name=json['title'],
            score=100,
            lang=lang
        ))
        Log(''.ljust(157, '='))

    def update(self, metadata, media, lang, force):
        for s in sorted(media.seasons, key=natural_sort_key):
            episodes = 1
            for e in sorted(media.seasons[s].episodes, key=natural_sort_key):
                realFile = media.seasons[s].episodes[e].items[0].parts[0].file
                filename = os.path.basename(realFile)
                (fileOnly, _) = os.path.splitext(filename)
                found = False
                for rx in RX_LIST:
                    match = rx.match(fileOnly)
                    if not match:
                        continue

                    data = self.handleMatch(match, media.title)
                    if not data:
                        continue

                    if episodes == 1:
                        metadata.title = media.title

                    metadata.seasons[s].episodes[e].index = int(
                        data.get('episode'))
                    metadata.seasons[s].episodes[e].absolute_index = int(
                        data.get('episode'))
                    if data.get('title'):
                        metadata.seasons[s].episodes[e].title = data.get(
                            'title')

                    if data.get('released_date'):
                        metadata.seasons[s].episodes[e].originally_available_at = Datetime.ParseDate(
                            data.get('released_date')).date()

                    found = True
                    Log(u"Update() - episode: {}, title: {}, released_date: {}, file: {}".format(
                        metadata.seasons[s].episodes[e].index,
                        metadata.seasons[s].episodes[e].title,
                        metadata.seasons[s].episodes[e].originally_available_at,
                        filename,
                    )
                    )
                    break

                episodes += 1

                if not found:
                    Log(u"Update() - No match for: [{}]".format(filename))

    def handleMatch(self, match, show):
        series = match.group('series') if match.groupdict().has_key(
            'series') else None
        month = match.group('month') if match.groupdict().has_key(
            'month') else None
        day = match.group('day') if match.groupdict().has_key('day') else None
        year = match.group('year') if match.groupdict().has_key(
            'year') else None
        episode = match.group('episode') if match.groupdict().has_key(
            'episode') else None
        title = match.group('title') if match.groupdict().has_key(
            'title') else None
        if title:
            if show and show.lower() in title.lower():
                title = re.sub(re.escape(show), '', title, flags=re.IGNORECASE)
            title = re.sub('\[.+?\]', ' ', title).strip('-').strip()

        season = match.group('season') if match.groupdict().has_key(
            'season') else None

        if year and len(year) == 2:
            year = '20' + year

        released_date = "%s-%s-%s" % (year, month,
                                      day) if year and month and day else None

        if not season:
            season = int(year) if year else 1

        if not episode:
            episode = int('1' + match.group('month') + match.group('day'))

        if not title or title == series:
            title = released_date

        if title:
            title = title.strip().strip('-').strip()
            if match.groupdict().has_key('epNumber'):
                title = match.group('epNumber') + ' - ' + title
            elif title and released_date != title:
                title = u"{} ~ {}".format(
                    released_date.replace('-', '')[2:],
                    title
                )

            title = title.strip()

        if season is None and episode is None:
            return None

        return {"season": season, "episode": episode, "title": title, "year": year, "month": month, "day": day, 'released_date': released_date}

    def searchCustomDB(self, type, query):
        apiUrl = Prefs["api_url"]
        if not apiUrl:
            Log.Error("No API URL set in library preferences.")
            return None

        apiUrl += "&" if "?" in apiUrl else "?"
        apiUrl += urllib.urlencode({
            "type": type,
            "query": query,
        })

        Log(u"_searchCustomDB() - path: {}, key: {}".format(apiUrl, query))

        try:
            request = urllib2.Request(apiUrl)
            response = urllib2.urlopen(request)
            status_code = response.getcode()
            if 200 != status_code:
                Log.Error("_searchCustomDB() - HTTP Error: %s" % status_code)
                return None

            contents = response.read()
            return JSON.ObjectFromString(contents)[0]
        except urllib2.HTTPError as e:
            print(e.reason)
            Log.Error(e.reason)
            return None
        except urllib2.URLError as e:
            print(e.reason)
            Log.Error(e.reason)
            return None
