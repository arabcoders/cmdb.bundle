# -*- coding: utf-8 -*-

### Imports ###
import sys                  # getdefaultencoding, getfilesystemencoding, platform, argv
import os                   # path.abspath, join, dirname
import re                   #
import inspect
import time              # getfile, currentframe
import urllib              #
import urllib2              #
import json
from dateutil.parser import parse

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
    '^(?P<year>\d{2,4})(\-|\.|_)?(?P<month>\d{2})(\-|\.|_)?(?P<day>\d{2})\s-?(?P<series>.+?)(?P<epNumber>\#(\d+)|ep(\d+)|DVD[0-9.-]+|DISC[0-9.-]+|SP[0-9.-]+|Episode\s(\d+)) -?(?P<title>.+)',
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

    def getShowInfo(self, media):

        def getFile(media):
            if not media or not media.seasons:
                return None

            for s in media.seasons:
                for e in media.seasons[s].episodes:
                    file = media.seasons[s].episodes[e].items[0].parts[0].file
                    if not file:
                        continue
                    return file
            return None

        filename = getFile(media)
        if not filename:
            Log(u"getShowInfo() - No file found in media object.")
            return None

        info = {}
        filename = urllib.unquote(filename).decode('utf8')
        dirName = os.path.dirname(os.path.dirname(filename))
        parentDirName = os.path.basename(dirName)
        Log(u"getShowInfo() - filename: {} dirName: {} parentDirName: {}".format(
            filename,
            dirName,
            parentDirName
        ))

        try:
            nfoFile = os.path.join(dirName, "tvshow.nfo")
            if not os.path.exists(nfoFile):
                Log(u"getShowInfo() - No tvshow.nfo file found in: {}.".format(dirName))
                return None

            nfoText = Core.storage.load(nfoFile)
            # work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
            nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
            # remove empty xml tags from nfo
            nfoText = re.sub(r'^\s*<.*/>[\r\n]+', '', nfoText, flags=re.MULTILINE)

            try:
                nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
            except:
                Log(u"ERROR: Cant parse XML in '{}' Aborting!".format(nfoFile))
                return None

            # Title
            try:
                info['title'] = nfoXML.xpath("title")[0].text.strip()
            except:
                Log(u"ERROR: No <title> tag in '{}' Aborting!".format(nfoFile))
                return None

            # original title
            try:
                info['original_title'] = nfoXML.xpath('originaltitle')[0].text.strip()
            except:
                pass

            # Network
            try:
                info['studio'] = nfoXML.xpath("studio")[0].text.strip()
            except:
                pass

            # Summary
            try:
                info['summary'] = nfoXML.findall("plot")[0].text.strip()
            except:
                pass

            # Premiere
            try:
                air_string = None
                try:
                    air_string = nfoXML.xpath("aired")[0].text.strip()
                except:
                    pass
                if not air_string:
                    try:
                        air_string = nfoXML.xpath("premiered")[0].text.strip()
                    except:
                        pass
                if not air_string:
                    try:
                        air_string = nfoXML.xpath("dateadded")[0].text
                    except:
                        pass

                if air_string:
                    try:
                        info['premiered'] = Datetime.ParseDate(air_string).date()
                    except:
                        pass
            except:
                pass

            Log(u"getShowInfo() - info: {}".format(info))

            return info
        except Exception as e:
            Log(u'getShowInfo() Exception: {}'.format(e))
            Log(u'getShowInfo() Traceback: {}'.format(traceback.format_exc()))
            return None

    def search(self, results,  media, lang, manual):
        Log("".ljust(60, '='))
        Log(u"Search() - Looking for: {}".format(media.show))
        Log("".ljust(60, '='))
        json = self.searchCustomDB('series', media.show)
        if not json:
            Log(u"Search() - No results found for: [{}]".format(media.show))
            return

        for item in json:
            Log(u"Search() - found - id: {}, title: {}".format(item['id'], item['title']))
            results.Append(MetadataSearchResult(
                id=item['id'],
                name=item['title'],
                lang=lang,
                score=100
            ))

        results.Sort('score', descending=True)
        Log(''.ljust(157, '='))

    def update(self, metadata, media, lang, force):
        Log("".ljust(60, '='))
        Log("Entering update function")
        Log("".ljust(60, '='))

        # Get the path to an media file to process channel data.
        nfo_file = self.getShowInfo(media)
        if nfo_file:
            if nfo_file.get('title'):
                metadata.title = nfo_file.get('id')

            if nfo_file.get('studio'):
                metadata.studio = nfo_file.get('studio')

            if nfo_file.get('summary'):
                metadata.summary = nfo_file.get('summary')

            if nfo_file.get('premiered'):
                metadata.originally_available_at = nfo_file.get('premiered')

        @parallelize
        def UpdateEpisodes():
            for s in media.seasons:
                for e in sorted(media.seasons[s].episodes, key=natural_sort_key):
                    episode = metadata.seasons[s].episodes[e]
                    episode_file = media.seasons[s].episodes[e].items[0].parts[0].file

                    @task
                    def updateEpisode(episode=episode, realFile=episode_file, metadata=metadata):
                        filename = os.path.basename(realFile)
                        (fileOnly, _) = os.path.splitext(filename)
                        found = False
                        for rx in RX_LIST:
                            match = rx.match(fileOnly)
                            if not match:
                                continue

                            data = self.handleMatch(
                                match, metadata.title, episode_file)
                            if not data:
                                continue

                            episode.index = int(data.get('episode'))
                            episode.absolute_index = int(data.get('episode'))

                            if data.get('title'):
                                episode.title = data.get('title')
                                if not episode.summary:
                                    episode.summary = fileOnly

                            if data.get('released_date'):
                                episode.originally_available_at = Datetime.ParseDate(
                                    data.get('released_date')).date()
                                if metadata.originally_available_at is None:
                                    metadata.originally_available_at = episode.originally_available_at

                            found = True
                            Log(u"updateEpisode() - season: {}, episode: {}, title: {}, released_date: {}, file: {}".format(
                                s,
                                episode.index,
                                episode.title,
                                episode.originally_available_at,
                                filename,
                            ))
                            break

                        if not found:
                            Log(u"updateEpisode() - No match for: [{}]".format(filename))

    def handleMatch(self, match, show, file=None):
        series = match.group('series') if match.groupdict().has_key('series') else None
        month = match.group('month') if match.groupdict().has_key('month') else None
        day = match.group('day') if match.groupdict().has_key('day') else None
        year = match.group('year') if match.groupdict().has_key('year') else None
        episode = match.group('episode') if match.groupdict().has_key('episode') else None
        title = match.group('title') if match.groupdict().has_key('title') else None
        if title:
            if show and show.lower() in title.lower():
                title = re.sub(re.escape(show), '', title, flags=re.IGNORECASE)
            title = re.sub('\[.+?\]', ' ', title).strip('-').strip()

        season = match.group('season') if match.groupdict().has_key('season') else None

        if year and len(year) == 2:
            year = '20' + year

        released_date = "%s-%s-%s" % (year, month, day) if year and month and day else None

        if not season:
            season = int(year) if year else 1

        if not episode:
            episode = int('1' + match.group('month') + match.group('day'))

        if not title or title == series and released_date:
            title = released_date

        if title:
            title = title.strip().strip('-').strip()
            if match.groupdict().has_key('epNumber'):
                title = match.group('epNumber') + ' - ' + title
            elif title and released_date != title and released_date:
                title = u"{} ~ {}".format(
                    released_date.replace('-', '')[2:],
                    title
                )

            title = title.strip()

        if season is None and episode is None:
            return None

        if file and released_date and len(str(episode)) < 8 and os.path.exists(file):
            json_ts = time.gmtime(os.path.getmtime(file))
            minute = json_ts[4]
            seconds = json_ts[5]
            episode = int('{}{:>02}{:>02}'.format(episode, minute, seconds))

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
            return JSON.ObjectFromString(contents)
        except urllib2.HTTPError as e:
            print(e.reason)
            Log.Error(e.reason)
            return None
        except urllib2.URLError as e:
            print(e.reason)
            Log.Error(e.reason)
            return None
