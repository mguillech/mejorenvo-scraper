import sys
import requests
import urllib
import re
import gzip
from itertools import chain
from pyquery import PyQuery

BASE_URL = 'http://www.mejorenvo.com'
RE_MOVIES = r'{}/descargar-.+-pelicula-\d+.html'.format(BASE_URL)
RE_SHOWS = r'{}/descargar-.+-serie-\d+.html'.format(BASE_URL)
FILTER = 'HDTV'
SUBSWIKI_TAG_LANGUAGE = set(['espaã±ol', 'espaã±a', 'español', 'españa'])
SUBSWIKI_TAG_MOST_RECENT_SUB = 'más actualizado'
SUBSWIKI_TAG_COMPLETED_SUB = 'completado'


def _print_msg(message, extra_info='', msg_type='INFO'):
    msg = '[{}] {}'.format(msg_type, message)
    if extra_info:
        msg += " '{}'".format(extra_info)
    print(msg)


def download_movie(pq):
    title = pq('a').children('span').text()
    _print_msg('Attempting to download movie', title)
    links = pq('a')
    _print_msg('Getting torrent for movie', title)
    torrent = get_torrent(links)
    _print_msg('Getting subtitle for movie', title)
    subtitle = get_subtitle(links)
    _print_msg('Downloading torrent for movie', title)
    torrent_name = download_torrent(torrent, title)
    _print_msg('Downloading subtitle for movie', title)
    download_subtitle(subtitle, title, torrent_name)


def download_show(pq):
    title = pq('span')[0].text
    _print_msg('Attempting to download show', title)
    hdtv_span = pq('span').filter(lambda i: PyQuery(this).text() == FILTER)

    episodes_tr = []

    for span in hdtv_span:
        parent_table = list(span.iterancestors())[2]
        episodes_tr = PyQuery(parent_table).find('table').find('tr')

    for episode_tr in episodes_tr:
        episode_tds = list(episode_tr.iterchildren())
        episode_title = PyQuery(episode_tds[0]).find('a').text()
        episode_name = '{} - {}'.format(title, episode_title)
        links = PyQuery(episode_tds[1]).find('a')
        _print_msg('Getting torrent for', episode_name)
        torrent = get_torrent(links)
        _print_msg('Getting subtitle for', episode_name)
        subtitle = get_subtitle(links)
        _print_msg('Downloading torrent for', episode_name)
        torrent_name = download_torrent(torrent, episode_name)
        _print_msg('Getting subtitle for', episode_name)
        download_subtitle(subtitle, episode_name, torrent_name)


def get_torrent(links):
    return [link.values()[0] for link in links if 'torrent=1' in link.values()[0]][0]


def _get_torrent_name(url):
    if '.torrent' in url:
        parsed_url = urllib.parse.urlparse(url)
        if '.torrent' in parsed_url.path:
            return parsed_url.path
        else:
            # Torrent filename is inside a query parameter
            for query_string in chain.from_iterable(urllib.parse.parse_qs(url).values()):
                if '.torrent' in query_string:
                    return query_string


def download_torrent(torrent, episode_name=''):
    try:
        r = requests.get(urllib.parse.urljoin(BASE_URL, torrent))
    except requests.HTTPError:
        _print_msg('Downloading torrent at {} failed, skipping...'.format(torrent), msg_type='ERROR')
    else:
        with open('{}.torrent'.format(episode_name), 'wb') as fd:
            fd.write(r.content)

        # Get torrent file name
        torrent_name = ''
        if r.history:
            for history in r.history:
                torrent_name = _get_torrent_name(history.url)
                if torrent_name:
                    break
        else:
            torrent_name = r.headers['Content-Disposition'].replace('"', '').replace('attachment; filename=', '')

        return torrent_name.replace('.torrent', '')


def get_subtitle(links):
    return [link.values()[0]
            for link in links if 'title' in link.attrib and 'subtitulos' in link.attrib['title'].lower()][0]


def _build_table_subtitle_dict(table):
    table_dict = {}
    sub_version = PyQuery(table).find('td.NewsTitle').text().lower().replace('versión ', '')
    for sub_language in PyQuery(table).find('td.language'):
        language_tokens = [term.lower().replace('(', '').replace(')', '')
                           for term in PyQuery(sub_language).text().split()]
        if not (set(language_tokens) & SUBSWIKI_TAG_LANGUAGE):
            continue
        subtitle_row = PyQuery(sub_language).parent()
        completed_status = subtitle_row.find('td[width="19%"]').text().lower()
        sub_link = ''
        if completed_status == SUBSWIKI_TAG_COMPLETED_SUB:
            table_dict[sub_version] = {'best_guess_count': 0, 'download_link': ''}
            most_recent_stored = False
            for sub_link_anchor in PyQuery(subtitle_row.find('td[colspan="3"]')).find('a'):
                if most_recent_stored:
                    break
                if PyQuery(sub_link_anchor).text().lower() == SUBSWIKI_TAG_MOST_RECENT_SUB:
                    most_recent_stored = True
                sub_link = sub_link_anchor
            table_dict[sub_version]['download_link'] = sub_link
    return table_dict


def _tokenize_name(name):
    return set([token.lower() for token in re.split('[.\-_/\s\[\]]', name) if token])


def _get_subswiki_subtitle(torrent_name, subs_page):
    """
    Provided a torrent file name and a subtitles page in subswiki, attempt to guess the subtitle version which
    matches the torrent file name.
    """
    table_dict = {}
    tokenized_torrent_name = _tokenize_name(torrent_name)

    for table in subs_page.find('table[width="90%"]'):      # Tables with downloadable subtitles
        table_dict.update(_build_table_subtitle_dict(table))

    for sub_version, version_dict in table_dict.items():
        tokenized_version = _tokenize_name(sub_version)
        version_dict['best_guess_count'] = len(tokenized_version & tokenized_torrent_name)

    best_guess = table_dict[max(table_dict.items(), key=lambda x: x[1]['best_guess_count'])[0]]
    return best_guess['download_link']


def download_subtitle(subtitle_url, episode_name='', torrent_name=''):
    SOLOSUBTITULOS = 'solosubtitulos' in subtitle_url
    pq = PyQuery(subtitle_url)
    if SOLOSUBTITULOS:
        sub_anchor = pq('.descargar_ficha')
    else:
        # For subswiki we need to tokenize the torrent file name and try to 'guess' which subtitle file matches our
        # torrent file
        sub_anchor = _get_subswiki_subtitle(torrent_name, pq)
    sub_anchor.make_links_absolute('http://www.solosubtitulos.com' if SOLOSUBTITULOS else 'http://www.subswiki.com')

    if sub_anchor is not None:
        sub_link = sub_anchor.attrib['href']
        try:
            r = requests.get(sub_link)
        except requests.HTTPError:
            _print_msg('Downloading subtitle at {} failed, skipping...'.format(sub_link), msg_type='ERROR')
        else:
            if 'Content-Type' in r.headers:
                sub_ext = r.headers['content-type'].split('/')[-1]
            elif 'Content Type' in r.headers:
                sub_ext = r.headers['content type'].split('/')[-1]
            else:
                sub_ext = 'srt'

            content = r.content
            # Identify if the content is gzipped
            if content.startswith(b'\x1f\x8b\x08'):
                content = gzip.decompress(content)

            with open('{}.{}'.format(episode_name, sub_ext), 'wb') as fd:
                fd.write(content)


def main(url):
    pq = PyQuery(url)
    # Identify the type of content we're trying to download
    if re.match(RE_MOVIES, url):    # it's a movie
        download_movie(pq)
    elif re.match(RE_SHOWS, url):   # it's a show
        download_show(pq)
    else:
        print('Invalid movie/show URL given')
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print('Use: {} movie-or-show-URL'.format(sys.argv[0]))
