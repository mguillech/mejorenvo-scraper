import re
import sys
import urllib2
from pyquery import PyQuery

BASE_URL = 'http://www.mejorenvo.com'
RE_MOVIES = r'%s/descargar-.+-pelicula-\d+.html' % BASE_URL
RE_SHOWS = r'%s/descargar-.+-serie-\d+.html' % BASE_URL
FILTER = 'HDTV'

def _print_msg(message, extra_info):
    print '%s "%s"' % (message, extra_info)

def download_movie(pq):
    title = pq('a').children('span').text()
    _print_msg('Attempting to download movie', title)
    links = pq('a')
    _print_msg('Getting torrents for movie', title)
    torrents = get_torrents(links)
    _print_msg('Getting subtitles for movie', title)
    subtitles = get_subtitles(links)
    _print_msg('Downloading torrents for movie', title)
    try:
        download_torrents(torrents, title)
    except urllib2.HTTPError:
        _print_msg('Error downloading torrents! Site down?', title)
    _print_msg('Downloading subtitles for movie', title)
    try:
        download_subtitles(subtitles, title)
    except urllib2.HTTPError:
        _print_msg('Error downloading subtitles! Site down?', title)

def download_show(pq, filter_by='HDTV'):
    title = pq('span')[0].text
    _print_msg('Attempting to download show', title)
    hdtv_span = pq('span').filter(lambda i: PyQuery(this).text() == filter_by)

    for span in hdtv_span:
        parent_table = list(span.iterancestors())[2]
        episodes_tr = PyQuery(parent_table).find('table').find('tr')

    for episode_tr in episodes_tr:
        episode_tds = list(episode_tr.iterchildren())
        episode_title = PyQuery(episode_tds[0]).find('a').text()
        links = PyQuery(episode_tds[1]).find('a')
        _print_msg('Getting torrents for', '%s - %s' % (title, episode_title))
        torrents = get_torrents(links)
        _print_msg('Getting subtitles for', '%s - %s' % (title, episode_title))
        subtitles = get_subtitles(links)
        _print_msg('Downloading torrents for', '%s - %s' % (title, episode_title))
        try:
            download_torrents(torrents, '%s - %s' % (title, episode_title))
        except urllib2.HTTPError:
            _print_msg('Error downloading torrents! Site down?', '%s - %s' % (title, episode_title))
        _print_msg('Getting subtitles for', '%s - %s' % (title, episode_title))
        try:
            download_subtitles(subtitles, '%s - %s' % (title, episode_title))
        except urllib2.HTTPError:
            _print_msg('Error downloading subtitles! Site down?', '%s - %s' % (title, episode_title))

def get_torrents(links):
    return [ link.values()[0] for link in links if 'torrent=1' in link.values()[0] ]

def download_torrents(torrents, filename_prefix=''):
    for torrent in torrents:
        url = 'http://www.mejorenvo.com' + torrent
        # print '%s - %s' % (filename_prefix, url)
        handler = urllib2.urlopen(url)
        with open('%s.torrent' % filename_prefix, 'w') as fd:
            fd.write(handler.read())

def get_subtitles(links):
    return [ link.values()[0] for link in links if 'solosubtitulos' in link.values()[0] or
                                                   'subswiki' in link.values()[0]]

def download_subtitles(subtitles, filename_prefix=''):
    for subtitle in subtitles:
        SOLOSUBTITULOS = 'solosubtitulos' in subtitle
        pq = PyQuery(subtitle)
        sub_anchor = pq('.descargar_ficha') if SOLOSUBTITULOS else pq('a').filter(lambda i: this.text == 'descargar')
        sub_anchor = sub_anchor.make_links_absolute('http://www.solosubtitulos.com' if SOLOSUBTITULOS else\
        'http://www.subswiki.com')
        if sub_anchor:
            sub_link = sub_anchor.attr('href')
            handler = urllib2.urlopen(sub_link)
            sub_ext = handler.headers['content-type'].split('/')[-1] if SOLOSUBTITULOS else\
            handler.headers['content type'].split('/')[-1]
            # print '%s - %s - %s' % (filename_prefix, sub_link, sub_ext)
            with open('%s.%s' % (filename_prefix, sub_ext), 'w') as fd:
                fd.write(handler.read())

def main(url):
    pq = PyQuery(url)
    if re.match(RE_MOVIES, url):
        download_movie(pq)
    elif re.match(RE_SHOWS, url):
        download_show(pq, globals()['FILTER'])
    else:
        print 'Invalid movie/show URL given'
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print 'Use: %s movie-or-show-URL' % sys.argv[0]
