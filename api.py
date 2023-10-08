#!/usr/bin/env python3

from spotipy import Spotify
from spotipy.exceptions import *
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from dotenv import load_dotenv
from json import dump as json_dump
from os import getenv, makedirs, system
from os.path import exists
from utils import *
# import subprocess
from argparse import ArgumentParser
import mutagen
from mutagen.id3 import Encoding
import requests
from sys import argv

load_dotenv()

OUT_FOLDER = "songs"

class sp_instance:
    def __init__(self, args=None):
        self.verbose = True if ('verbose' in args and args.verbose) else False
        self.headless = True if ('headless' in args and args.headless) else False
        self.infos = True if ('infos' in args and args.infos) else False
        self.sp = None
        # Basic manager
        # sp = Spotify(client_credentials_manager=SpotifyClientCredentials())

        # User-data manager
        cid = getenv('SPOTIPY_CLIENT_ID')
        secret = getenv('SPOTIPY_CLIENT_SECRET')

        self.client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)

        # redirect_uri = 'http://localhost:8888/callback'
        # username = 'xxxx'
        # self.scope = "user-library-read playlist-modify-public user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-recently-played user-read-playback-position user-top-read app-remote-control streaming"
        self.scope = "user-library-read"

        self.sp = Spotify(client_credentials_manager=self.client_credentials_manager, auth_manager=SpotifyOAuth(scope=self.scope))

    def link_to_id(self, link):
        type = False
        id = False
        if "spotify.com" in link: # LINK
            link = link.split("spotify.com/")[1]
            type = link.split("/")[0]
            id = link.split("/")[1].split("?")[0]
        elif "spotify:" in link: # URI
            link = link.split("spotify:")[1]
            type = link.split(":")[0]
            id = link.split(":")[1]
        else:
            type = "track"
            id = link
        return type, id

    # def check_latency(self):
    #     playing = self.sp.current_playback()
    #     playing2 = self.sp.current_playback()
    #     print(playing2['progress_ms'] - playing['progress_ms'])

    # def get_likes(self, filename=None):
    #     results = self.sp.current_user_saved_tracks()
    #     likes = results['items']
    #     while results['next']:
    #         results = self.sp.next(results)
    #         likes.extend(results['items'])
    #     if filename:
    #         with open(filename, "w") as fw:
    #             json_dump(likes, fw, indent=2)
    #     else:
    #         return likes

    # def currently_playing(self, filename=None):
    #     playing = self.sp.current_playback()
    #     if filename:
    #         with open(filename, "w") as fw:
    #             json_dump(playing, fw, indent=2)

    #     cp = playing['item']
    #     print(f"Listening {cp['name']} by {', '.join([a['name'] for a in cp['artists']])} [{cp['album']['name']}] on {playing['device']['name']}")

    # def get_spotify_sink(self):
    #     p = subprocess.run(
    #         """get_spotify_sink(){ spotify_sink=$(LANG=en python3 pactl-json-parser/pactl_parser.py | jq 'to_entries[] | {sink:.key} + {value:.value.Properties["media.name"]} | if (.value | contains("Spotify")) then .sink | tonumber else empty end' | tail -f -n1); }; while [ -z "$spotify_sink" ]; do get_spotify_sink; done; echo $spotify_sink""",
    #         shell=True, capture_output=True)
    #     result = p.stdout.decode()
    #     print(result.strip())

    # def record(self, filename):
    #     system(f'parecord --latency-msec=1 -d alsa_output.pci-0000_05_00.6.analog-stereo.monitor --fix-channels --fix-format --fix-rate {filename} &')

    #     # premium required.
    #     # self.sp.pause_playback()
    #     # self.sp.start_playback()

    # def search_sharelink(self, link=None, filename=None):
    def track_by_id(self, track_id=None, filename=None):
        try:
            track = self.sp.track(track_id)
        except SpotifyException as e:
            return ERROR(f"Track id was not found : {track_id} ")
        except Exception as e:
            DERROR(f"Unexpected exception : Track id couldn't be found : {track_id} ")
            return DERROR(e)

        if filename:
            with open(filename, "w") as fw:
                json_dump(track, fw, indent=2)
        return track

    def record_manager(self, track_info, args=None, playlist_id=None, record=True):
        # self.sp.print_track_info(track_info)
        uri = track_info['uri']
        duration_ms = track_info['duration_ms']
        duration_s = int(duration_ms / 1000) + 1

        filename = f"{track_info['name']} - {','.join([artist['name'] for artist in track_info['artists']])}"
        filename = filename.replace('/', '_').replace(' ', '_').replace('\"', '_').replace('\'', '_').replace(',', '_').replace('$','_')

        filepath = f"{OUT_FOLDER}/{filename}.mp3" if not playlist_id else f"{OUT_FOLDER}/{playlist_id}/{filename}.mp3"

        file_exists = exists(filepath)
        if file_exists:
            DINFO(f"An existing recorded file was found at {filepath}")

        if record:
            if not file_exists or args.overwrite:
                track_info['output_filepath'] = filepath

                spotdl_cmd = f"./spotdl.sh {uri} \"{filepath}\" {duration_s} {'1' if self.verbose else ''}"
                system(spotdl_cmd)

        if not exists(filepath):
            DERROR(f"\"{filepath}\" : Filepath does not exist. Exiting")
            return False

        if not file_exists: # If file doesn't existed before, but now exists
            self.edit_metadata(filepath, track_info)
            self.add_lyrics(args.lyrics_mode, filepath, track_info)

        return filepath

    def search_track(self, track_name=None, filename=None):
        if not track_name:
            return DINFO("No track specified")
        results = self.sp.search(q='track:' + track_name, type='track', limit=20)
        results = results['tracks']
        tracks = results['items']

        if filename:
            with open(filename, "w") as fw:
                json_dump(tracks, fw, indent=2)
        return tracks

    def playlist_by_id(self, playlist_id=None, filename=None):
        if not playlist_id:
            return INFO("No playlist specified")

        results = self.sp.playlist(playlist_id)
        tracks = results['tracks']
        while tracks['next']:
            tracks = self.sp.next(tracks)
            results['tracks']['items'].extend(tracks['items'])

        if filename:
            with open(filename, "w") as fw:
                json_dump(results, fw, indent=2)
        return results

    def print_track_info(self, info=None):
        if not info:
            return DINFO("No track info, exit")

        with open("track.json", "w") as fo:
            json_dump(info, fo)

        duration = int(info['duration_ms'])
        duration = f"{duration/60000:.0f}:{duration/1000%60:02.0f}" if duration else None

        print(f"""{C.BOLD}{C.YELLOW}Track{C.END}
* name : {C.YELLOW}{info['name']}{C.END}
* type : {info['type']}
* duration_ms : {duration}
* id : {info['id']}
* popularity : {info['popularity']}

{C.BOLD}{C.YELLOW}Artist(s){C.END}
* artists_names : {C.YELLOW}{', '.join([artist['name'] for artist in info['artists']])}{C.END}
* album : {info['album']['name']} ({info['album']['album_type']}) - {info['album']['id']}
* album_image : {info['album']['images'][0]['url']}
* album_release_date : {info['album']['release_date']}
* track_number : {info['track_number']} / {info['album']['total_tracks']}

{C.BOLD}{C.YELLOW}More info{C.END}
* FR_available : {True if "FR" in info['available_markets'] else False}
* is_local : {info['is_local']}
* href : {info['href']}
* disc_number : {info['disc_number']}
* explicit : {info['explicit']}
* external_urls['spotify'] : {info['external_urls']['spotify']}
* external_ids['isrc'] : {info['external_ids']['isrc']}
* preview_url : {info['preview_url']}
* uri : {info['uri']}""")

    # Edit music metadata
    def edit_metadata(self, filepath, track_info):
        if self.verbose:
            DINFO("Edit metadata")

        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPUB, TBPM, TCON, APIC, TDRC, TENC, TRCK, TSRC, WXXX
        f = ID3(filepath)

        # https://mutagen-specs.readthedocs.io/en/latest/id3/id3v2.4.0-frames.html

        # Update title
        f.setall('TIT2', [TIT2(text=track_info['name'])])

        # Update artist
        f.setall('TPE1', [TPE1(text=', '.join([artist['name'] for artist in track_info['artists']]))])

        # Update album
        album = track_info['album']['name'] + (" - single" if track_info['album']['album_type'] == "single" else "")
        f.setall('TALB', [TALB(text=album)])

        # Update label
        f.setall('TPUB', [TPUB(text="spotify-recorder")])

        # Update bpm
        #     f.setall('TBPM', [TBPM(text="bpm")])

        # Update ISRC
        f.setall('TSRC', [TSRC(encoding=3, text=track_info['external_ids']['isrc'])])

        # Update Genre
        if "genres" in track_info["artists"]:
            genres = ', '.join(g for g in track_info["artists"]["genres"])
            f.setall('TCON', [TCON(text=genres)])

        # Update Release date
        # #ID3 v2.3
        # f.setall('TDRC', [])
        # f.setall('TDAT', [TDAT(text=date)])
        # f.setall('TYER', [TYER(text=str(date.year))])
        #ID3 v2.4
        f.setall('TDAT', [])
        f.setall('TYER', [])
        f.setall('TDRC', [TDRC(text=track_info['album']['release_date'])])

        # Update Encoded by # TENC/TSSE
        f.setall('TENC', [TENC(text="spotify-recorder with ffmpeg, mp3splt")])

        # Update track number
        f.setall('TRCK', [TRCK(text=str(track_info['track_number']))])
        # info['album']['total_tracks']

        # Update User defined URL link frame (for spotify's URI)
        if not "spotify_uri" in [frame.desc for frame in f.getall('WXXX')]:
            f.setall('WXXX', [WXXX(encoding=Encoding.UTF8, desc=u'spotify_uri', url=track_info['uri'])])

        f.save()

        # Cover
        link_artwork = track_info["album"]["images"][0]["url"]
        # DINFO(link_artwork)
        image_data = requests.get(link_artwork, stream=True).content
        # DINFO(len(image_data))
        mime = 'image/jpeg'
        if '.png' in link_artwork:
            mime = 'image/png'

        audio = mutagen.File(filepath)
        audio.tags.add(
            APIC(
                # encoding=3, # 3 is for utf-8
                mime=mime, # image/jpeg or image/png
                type=3, # 3 is for the cover image
                desc=u'Cover',
                data=image_data))
        audio.save()


    # Available modes : 'none', 'synced', 'unsynced', 'both', 'synced_USLT'
    def add_lyrics(self, mode, filepath, track_info):
        if mode == 'none':
            if self.verbose: DINFO("Skipped lyrics")
            return

        if self.verbose:
            DINFO("Adding lyrics")

        # Download lyrics
        track_id = track_info['id']
        url = f"https://spotify-lyric-api.herokuapp.com/?trackid={track_id}&format=lrc"
        res = requests.get(url)
        if res.status_code == 200:
            lrc_lyrics = res.json()

            if self.verbose:
                with open("lyrics.lrc", "w") as fo:
                    json_dump(lrc_lyrics, fo)
        else:
            DINFO(f"Cannot get lyrics (error {res.status_code} : {res.json()})")
            return

        from mutagen.id3 import ID3, USLT, SYLT, TIT2, Encoding
        audio = ID3(filepath)

        #     "external_ids": {
        #     "isrc": "USAT21811468"
        # },



        # UNSYNCED
        if mode == 'unsycned' or mode == 'both':
            uslt_lyrics = "\n".join([a['words'] for a in lrc_lyrics['lines']])
            audio["USLT::eng"] = USLT(encoding=3, lang=u'eng', text=uslt_lyrics)

        # SYNCED
        lrc_data = []
        for item in lrc_lyrics['lines']:
            text = item['words']
            timer = item['timeTag']
            tm = timer.split(":")
            ts = tm[1].split(".")

            min = int(tm[0])
            sec = int(ts[0])
            ms = int(ts[1]) * 10
            timestamp = (min * 60 + sec) * 1000 + ms

            lrc_data.append((text, timestamp))
        if lrc_data[-1][0] == '':
            lrc_data = lrc_data[:-1]

        if mode == 'synced' or mode == 'both':
            audio.setall("SYLT", [SYLT(encoding=Encoding.UTF8, lang='eng', format=2, type=1, text=lrc_data)])

        if mode == 'synced_USLT':
            sylt_lyrics = "".join([f"[{a['timeTag']}]{a['words']}\n" for a in lrc_lyrics['lines']])
            audio["USLT::eng"] = USLT(encoding=3, lang=u'eng', text=sylt_lyrics)

        audio.setall('TIT2', [TIT2(text="both !")])

        # audio["SYLT::eng"] = SYLT(encoding=3, text=lrc_data, format=1, type=1)
        # audio.add(SYLT(encoding=3, text=lrc_data, format=2, type=1))

    __search_track = search_track
    # __get_likes = get_likes


def main():
    parser = ArgumentParser(description='Spotify Recorder')
#     parser = ArgumentParser(description='Spotify Recorder', usage=f"""
# python3 {argv[0]} <share link> or <query>  [options]
# Example : python3 {argv[0]} https://open.spotify.com/track/X  [options]
#           python3 {argv[0]} https://open.spotify.com/playlist/X  [options]
#           python3 {argv[0]} --search \"song name author\"  [options]""")

    parser.add_argument("links", action='store', nargs='+') # song / playlist uri
    parser.add_argument('-s', '--search', action='store', nargs=1, help="search for a song")

    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="enable verbose mode")
    parser.add_argument('--headless', action='store_true', default=False, help="[NOT YET SUPPORTED] enable spotify headless mode (requires xfvb)")
    parser.add_argument('--infos', action='store_true', default=False, help="print infos")
    parser.add_argument('--overwrite', action='store_true', default=False, help="overwrite song if already exist")
    parser.add_argument('--lyrics-mode', choices=['none', 'synced', 'unsynced', 'both', 'synced_USLT'], default='', help='Lyrics writing mode')

    parser.add_argument('--no-record', action='store_true', default=False, help='don\'t actually record')
    parser.add_argument('-f', '--file', action='store', nargs=1, help='Input file')

    args = parser.parse_args()
    # args, unknown = parser.parse_known_args()
    if args.verbose:
        DINFO(f"Arguments : {args}")

    sp = sp_instance(args)

    if len(args.links) == 0:
        INFO(f"Usage : python3 {sys.argv[0]} <share link> or <query>\n  [options]")
        print(f"Example : python3 {sys.argv[0]} https://open.spotify.com/track/X  [options]")
        print(f"          python3 {sys.argv[0]} https://open.spotify.com/playlist/X  [options]")
        print(f"          python3 {sys.argv[0]} --search \"song name author\"  [options]")
        return

    if args.search:
        requested = " ".join(args.links)

        if args.verbose:
            DINFO(f"Requested : {requested}")

        tracks = sp.search_track(requested, "tracks.json")

        id = 0
        if len(tracks) == 0:
            return ERROR("No song found.")
        elif len(tracks) > 1:
            INFO("\n".join([
                f"{itrack} : {track['name']} - {', '.join([artist['name'] for artist in track['artists']])} [{track['album']['name']}]"
                for itrack, track in enumerate(tracks)]))
            id = input("Choose id : ")
            if not id.isnumeric() or int(id) < 0 or int(id) > len(tracks) - 1:
                return DERROR(f"Must be an integer from 0 to {len(tracks)-1}")
        track_info = tracks[int(id)]

        if args.verbose or args.infos: sp.print_track_info(track_info)

        sp.record_manager(track_info, args, record=(not args.no_record))

    if args.file:
        filepath = args.file[0]
        if not exists(filepath):
            DERROR(f"--file can't access {filepath}")
            exit()
        args.no_record = True

        link = args.links[0]
        type, id = sp.link_to_id(link)
        if type != "track":
            DERROR("--file requires that URI type must be \"track\"")

        track_info = sp.track_by_id(id)
        if args.verbose or args.infos: sp.print_track_info(track_info)
        sp.edit_metadata(filepath, track_info)
        sp.add_lyrics(args.lyrics_mode, filepath, track_info)
        exit()

    for link in args.links:
        type, id = sp.link_to_id(link)
        if args.verbose:
            DINFO(f"Requested : [{type}] {id}")

        if type == "track":
            track_info = sp.track_by_id(id)

            if args.verbose or args.infos: sp.print_track_info(track_info)
            sp.record_manager(track_info, args, record=(not args.no_record))

        elif type == "playlist":
            playlist_path = f"{OUT_FOLDER}/{id}"
            makedirs(playlist_path, exist_ok=True)
            playlist = sp.playlist_by_id(id, filename=f"{playlist_path}/playlist.json")

            # print(len(playlist['tracks']['items']))
            for track_info in playlist['tracks']['items']:
                if track_info['is_local'] == True : #or not track_info['is_playable']:
                    # DINFO(f"Local track : {track_info['track']['name']} - {','.join([artist for artist in track_info['track']['artists']])}")
                    continue
                track_info = track_info['track']
                if args.verbose or args.infos: sp.print_track_info(track_info)
                sp.record_manager(track_info, args, playlist_id=id, record=(not args.no_record))


if __name__ == "__main__":
    main()
