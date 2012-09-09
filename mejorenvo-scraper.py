__author__ = 'valetin'

import sys
import urllib
from pyquery import PyQuery

FILTER = 'HDTV'

def main(url):
    pq = PyQuery(url)
    title = pq('span')[0].text
    hdtv_span = pq('span').filter(lambda i: PyQuery(this).text() == globals()['FILTER'])

    for span in hdtv_span:
        parent_table = list(span.iterancestors())[2]
        episodes_tr = PyQuery(parent_table).find('table').find('tr')

    for episode_tr in episodes_tr:
        episode_tds = list(episode_tr.iterchildren())
        episode_title = PyQuery(episode_tds[0]).find('a').text()
        links = PyQuery(episode_tds[1]).find('a')
        torrents = [ link.values()[0] for link in links if 'torrent' in link.values()[0] ]
        subtitles = [ link.values()[0] for link in links if 'subtitulos' in link.values()[0] ]

        for torrent in torrents:
            # print '%s - %s - %s' % (title, episode_title, torrent)
            _ = urllib.urlretrieve('http://www.mejorenvo.com' + torrent, '%s - %s.torrent' % (title, episode_title))

        for subtitle in subtitles:
            pq = PyQuery(subtitle)
            sub_anchor = pq('.descargar_ficha')
            if sub_anchor:
                sub_link = sub_anchor.attr('href')
                sub_ext = sub_link.split('&')[-1][-3:]
                # print '%s - %s - %s - %s' % (title, episode_title, sub_link, sub_ext)
                _ = urllib.urlretrieve('http://www.solosubtitulos.com' + sub_link, '%s - %s.%s' % (title,
                                                                                                   episode_title,
                                                                                                   sub_ext))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
