#!/usr/bin/env python3

from spotipy import Spotify
from spotipy.exceptions import *
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from dotenv import load_dotenv
from json import dump as json_dump
from json import load as json_load
from os import getenv, makedirs, system
import subprocess
from os.path import exists
from utils import *
from argparse import ArgumentParser
import mutagen
from mutagen.id3 import Encoding
import requests
from sys import argv

# SIG-INT control
import signal
def signal_handler(sig, frame):
    print("\nReceived Ctrl+C, stopping...")
    exit(1);
signal.signal(signal.SIGINT, signal_handler)


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

    def fix_filename(self, filename:str) -> str:
        filename = filename.replace('/', '_').replace(' ', '_').replace('\"', '_').replace('\'', '_').replace(',', '_').replace('$','_').replace(':','_')
        while '__' in filename:
            filename = filename.replace('__', '_')
        return filename

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

    def type_by_id(self, type=None, id=None, filename=None) -> dict:
        if not id:
            return INFO(f"No {type} specified"), None

        if type == "playlist": results = self.sp.playlist(id)
        elif type == "album": results = self.sp.album(id)

        else: DERROR(f"type {type} not expected here\n"); exit(1)
        tracks = results['tracks']
        while tracks['next']:
            tracks = self.sp.next(tracks)
            results['tracks']['items'].extend(tracks['items'])

        if filename:
            with open(filename, "w") as fw:
                json_dump(results, fw, indent=2)
        return results
    
    def record_multiple(self, type, info, args):
        fname, fpath = self.set_fpath(type, info)
        songs_count = len(info['tracks']['items'])
        makedirs(fpath, exist_ok=True)

        json_path = f"{fpath}/{type}.json"

        new_snapshot_id = None
        if exists(json_path) and type == "playlist":
            fo = open(json_path)
            new_snapshot_id = json_load(fo)["snapshot_id"]
            print(new_snapshot_id, info["snapshot_id"])

        if new_snapshot_id and new_snapshot_id == info["snapshot_id"]:
            print(f"No change in {type}")
            print(f"Total songs : {songs_count}")
        else :
            print(f"Creating {type} or updating {type}")
            with open(json_path, "w") as fw:
                json_dump(info, fw, indent=2)

        recorded = self.print_multiple_info(type, info)

        trackinfolist = info['tracks']['items']
        if args.order == 'random':
            from random import shuffle
            shuffle(trackinfolist)
        elif args.order == 'last':
            trackinfolist.reverse()

        for track_info in trackinfolist:
            if type == "playlist": track_info = track_info['track']
            playlist_name=track_info['name']

            filename = f"{track_info['name']} - {', '.join([artist['name'] for artist in track_info['artists']])}"
            print(f"Song : {filename} ... ", end='')
            if track_info['available_markets'] == []:
                print("It seems this isn't available in any market ... Skipping.")
                continue
            if track_info['is_local'] == True : #or not track_info['is_playable']:
                continue
            if exists(self.set_track_filename(track_info, fpath)):
                print("Track recorded - continue")
                continue
            
            print("")
            if args.verbose or args.infos: 
                if type == "album": track_info = self.sp.track(track_info['id'])
                self.print_track_info(track_info)
            self.record_manager(track_info, fpath, args, fname=fname, record=(not args.no_record), playlist_name=playlist_name)

    def record_manager(self, track_info, folder_path, args=None, fname=None, record=True, playlist_name=None):
        # self.sp.print_track_info(track_info)
        uri = track_info['uri']
        duration_ms = track_info['duration_ms']
        duration_s = duration_ms // 1000 + 1

        filepath = self.set_track_filename(track_info, folder_path)

        file_exists = exists(filepath)
        if file_exists:
            DINFO(f"An existing recorded file was found at {filepath}")
            if args.update_metadata:
                self.edit_metadata(filepath, track_info, playlist_name=playlist_name)

        if record:
            if not file_exists or args.overwrite:
                track_info['output_filepath'] = filepath

                spotdl_cmd = f"./spotdl.sh {uri} \"{filepath}\" {duration_s} {'1' if self.verbose else ''}"
                # print(spotdl_cmd)
                # system(spotdl_cmd)

                try:
                    subprocess.run(spotdl_cmd, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: Bash script exited with a non-zero status: {e.returncode}")
                except Exception as e:
                    print(f"Error while running bash script: {e}")

        if not exists(filepath):
            DERROR(f"\"{filepath}\" : Filepath does not exist. Exiting")
            return False

        if not file_exists: # If file doesn't existed before, but now exists - if file has been created
            self.edit_metadata(filepath, track_info, playlist_name=playlist_name)
            self.add_lyrics(args.lyrics_mode, filepath, track_info)

        return filepath

    def set_track_filename(self, track_info, folder_path=None):
        filename = f"{track_info['name']} - {','.join([artist['name'] for artist in track_info['artists']])}"
        filename = self.fix_filename(filename)
        filepath = f"{folder_path + '/' if folder_path else ''}{filename}.mp3"
        return filepath

    def set_fpath(self, type, info):
        if type == "playlist": author = info['owner']['display_name']
        else: author = ', '.join([artist['name'] for artist in info['artists']])
        name = info['name']
        fname = self.fix_filename(f"{info['id']} - {author} - {name}")
        fpath = f"{OUT_FOLDER}/{fname}"
        return fname, fpath

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

    def print_multiple_info(self, type, info):
        if not info:
            return DINFO(f"No {type} info, exit")

        fname, fpath = self.set_fpath(type, info)

        total_songs = info['tracks']['total']

        recorded = [False for x in range(total_songs)]
        print(f"Recorded {'Song':^26s}  | filepath")

        for i, item in enumerate(info['tracks']['items']):
            if type == "playlist": item = item['track']

            filepath = self.set_track_filename(item, fpath)

            filename = f"{item['name']} - {','.join([artist['name'] for artist in item['artists']])}"
            if len(filename) > 30: filename = filename[:29] + "…"

            str_exists = ' '
            if exists(filepath): recorded[i] = True; str_exists = 'x'

            print(f"  [{str_exists}] {filename[0:30].ljust(30, ' ')} | {filepath}")

        total_recorded = sum(x for x in recorded)
        # print(total_recorded)
        # print(len(recorded))
        print(f"Songs recorded : {total_recorded} / {total_songs} ({total_recorded/total_songs * 100:.1f}%)")
        print(f"Playlist folder path : \"{fpath}\"")

    # Edit music metadata
    def edit_metadata(self, filepath, track_info, playlist_name=None):
        if self.verbose:
            DINFO("Edit metadata")

        from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TPUB, TBPM, TCON, APIC, TDRC, TENC, TRCK, TSRC, WXXX, COMM
        f = ID3(filepath)

        # https://mutagen-specs.readthedocs.io/en/latest/id3/id3v2.4.0-frames.html

        # Update title
        f.setall('TIT2', [TIT2(text=track_info['name'])])

        # Update artist
        f.setall('TPE1', [TPE1(text=', '.join([artist['name'] for artist in track_info['artists']]))])

        # Update album artist
        f.setall('TPE2', [TPE2(text=', '.join([artist['name'] for artist in track_info['album']['artists']]))])

        # Update album
        album = track_info['album']['name'] + (" - single" if track_info['album']['album_type'] == "single" else "")
        f.setall('TALB', [TALB(text=album)])

        # Update label
        f.setall('TPUB', [TPUB(text="spotify-recorder")])

        # Update bpm
        #     f.setall('TBPM', [TBPM(text="bpm")])

        # Update TSRC
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

        # Update comments. Usable for example to sort by spotify playlist in user's library
        comm = "Recorded from Spotify"
        if playlist_name:
            comm += f":{playlist_name}"
        f.setall('COMM', [COMM(text=comm)])

        # Update track number
        f.setall('TRCK', [TRCK(text=str(track_info['track_number']))])
        # info['album']['total_tracks']

        # Update User defined URL link frame (for spotify's URI)
        if not "spotify_uri" in [frame.desc for frame in f.getall('WXXX')]:
            f.setall('WXXX', [WXXX(encoding=Encoding.UTF8, desc=u'spotify_uri', url=track_info['uri'])])

        f.save()

        # Album Cover
        album_cover_link = track_info["album"]["images"][0]["url"]
        try:
            res = requests.get(album_cover_link, stream=True)
            if not res.status_code == 200:
                raise requests.exceptions.RequestException("Request didn't get through")
            album_cover_data = res.content
        except:
            pass
        finally:
            mime = 'image/jpeg'
            if '.png' in album_cover_link:
                mime = 'image/png'

            audio = mutagen.File(filepath)
            audio.tags.add(
                APIC(
                    # encoding=3, # 3 is for utf-8
                    mime=mime, # image/jpeg or image/png
                    type=3, # 3 is for the cover image
                    desc=u'Cover',
                    data=album_cover_data))
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
        try:
            res = requests.get(url)
            if res.status_code == 200 and res.headers.get('Content-Type') == 'application/json':
                lrc_lyrics = res.json()
            else:
                DERROR(f"Failed to get lyrics. Status: {res.status_code}, Content-Type: {res.headers.get('Content-Type')}, Response: {res.text}")
                return
        except ValueError as e:
            return DERROR(f"Failed to download lyrics. Invalid JSON response: {res.text}")
        except Exception as e:
            DERROR(f"Failed to download lyrics. Unexpected error : {e}")
            return

        # Handle lyrics
        from mutagen.id3 import ID3, USLT, SYLT, TIT2, Encoding
        audio = ID3(filepath)

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

    __search_track = search_track
    # __get_likes = get_likes


def main():
    parser = ArgumentParser(description='Spotify Recorder')
#     parser = ArgumentParser(description='Spotify Recorder', usage=f"""
# python3 {argv[0]} <share link> or <query>  [options]
# Example : python3 {argv[0]} https://open.spotify.com/track/X  [options]
#           python3 {argv[0]} https://open.spotify.com/playlist/X  [options]
#           python3 {argv[0]} --search \"song name author\"  [options]""")

    parser.add_argument("links", action='store', nargs='*') # song / playlist uri
    parser.add_argument('-s', '--search', action='store', nargs=1, help="search for a song")

    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="enable verbose mode")
    parser.add_argument('--headless', action='store_true', default=False, help="[NOT YET SUPPORTED] enable spotify headless mode (requires xfvb)")
    parser.add_argument('--infos', action='store_true', default=False, help="print infos")
    parser.add_argument('--overwrite', action='store_true', default=False, help="overwrite song if already exist")
    parser.add_argument('--update-metadata', action='store_true', default=False, help='update metadata if file already exists')
    parser.add_argument('--lyrics-mode', choices=['none', 'synced', 'unsynced', 'both', 'synced_USLT'], default='none', help='Lyrics writing mode')
    parser.add_argument('--order', choices=['first', 'last', 'random'], default='last', help='Which song to start with when recording playlist')

    parser.add_argument('--no-record', action='store_true', default=False, help='don\'t actually record')
    parser.add_argument('-f', '--file', action='store', nargs=1, help='Input file')

    args = parser.parse_args()
    # args, unknown = parser.parse_known_args()
    if args.verbose:
        DINFO(f"Arguments : {args}")

    sp = sp_instance(args)

    if not args.search and len(args.links) == 0:
        INFO(f"Usage : python3 {argv[0]} <share link> or <query>\n  [options]")
        print(f"Example : python3 {argv[0]} https://open.spotify.com/track/X  [options]")
        print(f"          python3 {argv[0]} https://open.spotify.com/playlist/X  [options]")
        print(f"          python3 {argv[0]} --search \"song name author\"  [options]")
        return

    if args.search:
        requested = " ".join(args.search)

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

        sp.record_manager(track_info, ".", args, record=(not args.no_record))

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
            sp.record_manager(track_info, ".", args, record=(not args.no_record))

        elif type == "album" or type == "playlist":
            info = sp.type_by_id(type, id)

            if args.verbose or args.infos: sp.print_multiple_info(type, info)

            sp.record_multiple(type, info, args)

if __name__ == "__main__":
    main()
