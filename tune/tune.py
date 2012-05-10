#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import mpd
import sys
import socket
import Levenshtein as lev
import termcolor
import gettext
from copy import deepcopy

gettext.install("tune", unicode=True)

VERSION = "0.1.2"

def c(color, msg):
    if args.no_color:
        return msg
    else:
        if color[-2::] == "_b":
            return termcolor.colored(msg, color[:-2], attrs=['bold'])
        else:
            return termcolor.colored(msg, color)
    
def match(playlist, title, artist):
    matches = []
    # Przestaw na małe, jeżeli trzeba.
    if not args.case:
        if title is not None: title = title.lower()
        if artist is not None: artist = artist.lower()
        
        orig = deepcopy(playlist)
        temp = []
        for track in playlist:
            temp.append(dict(zip(track.keys(), map(unicode.lower, track.values()))))
        playlist = temp
    else:
        orig = playlist
    
    # Pierwsza kolejka - dopasuj dokładnie
    for track in playlist:
        if artist is not None and title is not None:
            if track['title'] == title and track['artist'] == artist:
                matches.append(orig[playlist.index(track)])
        elif title is None:
            if artist == track['artist']:
                matches.append(orig[playlist.index(track)])
        elif artist is None:
            if title == track['title']:
                matches.append(orig[playlist.index(track)])
    
    if not args.exact and len(matches) == 0:
        # Próbujemy leveshteina.
        print c("yellow", _("Not found. Searching similiar matches."))
        for track in playlist:
            if artist is not None and title is not None:
                if lev.ratio(" - ".join((artist, title)),
                             "-".join((track['artist'], track['title']))
                             ) > args.min_ratio:
                    matches.append(orig[playlist.index(track)])
            elif title is None:
                if lev.ratio(artist,track['artist']) > args.min_ratio:
                    matches.append(orig[playlist.index(track)])
            elif artist is None:
                if lev.ratio(title,track['title']) > args.min_ratio:
                    matches.append(orig[playlist.index(track)])
    return matches

def choose(playlist):
    avail = ["0", "-1"] # continue search / cancel
    for key in playlist:
        if 'id' not in key:
            key['id'] = playlist.index(key)
        avail.append(key['id'])
        print c("green", "[{0:0d}]".format(int(key['id']))), c("yellow", '=>'), key['artist'],  c('yellow', '-'), key['title'], \
        "\t", c('yellow',"("), key['album'], c('yellow',')')
    while True:
        answer = raw_input(_("Choose from the list (-1 cancels, 0 continues search): "))
        if not answer in avail:
            print c("red", _("Answer not allowed."))
        elif answer == "-1":
            sys.exit(0)
        else:
            return answer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=_('Matches a song in MPD database, then plays it.'))
    parser.add_argument('--mpd-host', '-H', type=str, required=False, default='localhost',
                        help=_('mpd host'))
    parser.add_argument('--mpd-port', '-P', type=int, required=False, default=6600,
                        help=_('mpd port'))
    parser.add_argument('--playlist', "-p", required=False, default=False, action='store_true',
                        help=_('search only tracks in playlist'))
    parser.add_argument('--dry-run', "-n", required=False, action='store_true', default=False, 
                        help=_("do not actually play the song, just show what would be played"))
    parser.add_argument("--no-color", '-C', required=False, action='store_true', default=False,
                        help=_("display messages without terminal colors"))
    parser.add_argument("--min-ratio", "-r", metavar='0.8', required=False, type=float, default=0.8,
                        help=_("Minimal ratio to match"))
    parser.add_argument("--case", "-c", required=False, action='store_true', default=False,
                        help=_("Match case in artists/titles"))
    parser.add_argument("--exact", "-x", required=False, action="store_true", default=False,
                        help=_("Only show exact matches"))
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--artist", "-a", required=False, action="store_true", default=False,
                        help=_("Search only field 'artist'"))
    group.add_argument("--title", "-t", required=False, action="store_true", default=False,
                        help=_("Search only field 'title'"))
    
    parser.add_argument('keyword', type=str, nargs='+',
                       help=_('track to search for; it may be "artist - title" (mind the space), "title" or just "artist"'))
    
    args = parser.parse_args()
    search = " ".join(args.keyword)
    
    # What are we searching for?
    if args.artist:
        title = None
        artist = unicode(search)
    elif args.title:
        title = unicode(search)
        artist = None
    elif search.find(' - ') >= 0:
        artist, title = map(unicode, search.split(" - "))
    else:
        print c('red', _("Error: Wrong arguments"))
        sys.exit(1)
        
    print c('green_b', _("---- Query ----"))
    if artist is not None: print c('green', _("Artist: ")) + artist
    if title is not None: print c('green', _("Title: ")) + title
    print c('green_b', _("---- Query ----"))
    
    # Does MPD Exists?
    daemon = mpd.MPDClient()
    daemon.use_unicode = True
    try:
        daemon.connect(args.mpd_host, args.mpd_port)
        
        # Time for the magic!
        # Get the playlist and try to match.
        playlist = daemon.playlistinfo()
        print c("magenta", _("Searching in playlist."))
        result = match(playlist, title, artist)
        if len(result) > 1:
            choice = choose(result)
        elif len(result) == 1:
            choice = result[0]['id']
        else:
            choice = 0
            
        if int(choice) > 0:
            if not args.dry_run:
                daemon.play(choice)    
            now = daemon.playlistinfo(choice)[0]
            print c("green_b", _("Tuned:")), now['artist'], "-", now['title']
            exit(0)
        
        print c('magenta', _("Searching in library."))
        
        # The trick. .find(...) matches case-sensitive, .search(...) case-insensitive
        if args.case:
            matcher = daemon.find
        else:
            matcher = daemon.search
            
        if title is not None and artist is not None:
            # Get matching artists and titles in {file: track, ...} format
            artists = {item['file']:item for item in matcher("artist", artist)}
            titles = {item['file']:item for item in matcher("title", title)}
            
            # Convert to set, intersect by keys (filenames), then return original tracks 
            matches = [titles[item] for item in (set(artists.keys()) & set(titles.keys()))]
            
        elif title is None:
            matches = matcher("artist", artist)
        elif artist is None:
            matches = matcher("title", title)
            
        if len(matches) == 0:
            print c('yellow', _("Not found."))
            sys.exit(1)
        if len(matches) == 1:
            the_track = matches[0]
        if len(matches) > 1:
            choice = choose(matches)
            if choice == "0":
                sys.exit(0)
            the_track = matches[choice]
        
        print _("This track is in album \"{album}\".\n Do you wish to play the album containing it?").format(album=the_track['album'])
        ans = raw_input("[y/N/...] ")
        
        album = matcher("album", the_track['album'])
        if not args.dry_run:
            if ans == "y":
                first_id = daemon.addid(album[0]['file']) # after adding first track, we need to get its ID
                for track in album[1:]:
                    daemon.add(track['file'])
                daemon.playid(first_id)
                the_track = album[0]
            else:
                track_id = daemon.addid(the_track['file'])
                print track_id
                daemon.playid(track_id)
                
        print c("green_b", _("Tuned:")), the_track['artist'], "-", the_track['title']
                
        
    except socket.error:
        print c('red_b', "!! ") + _("Can't connect to MPD. Exiting.")
    
    
