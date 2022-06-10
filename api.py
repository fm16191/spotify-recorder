import spotipy
from spotipy.exceptions import *
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import dotenv
import json
import os
import sys
from datetime import datetime

dotenv.load_dotenv()

def DOK(content):
    print(f"\033[92m[{datetime.now().strftime('%Y %b.%d %H:%M:%S')}] {content}\033[0m")
def DINFO(content):
    print(f"\033[93m[{datetime.now().strftime('%Y %b.%d %H:%M:%S')}] {content}\033[0m")
def DERROR(content):
    print(f"\033[91m[{datetime.now().strftime('%Y %b.%d %H:%M:%S')}] {content}\033[0m")
def OK(content):
    print(f"\033[92m{content}\033[0m")
def INFO(content):
    print(f"\033[93m{content}\033[0m")
def ERROR(content):
    print(f"\033[91m{content}\033[0m")

class sp_instance:
    def __init__(self):
        self.sp = None
        # Basic manager
        # sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

        # User-data manager
        cid = os.getenv('SPOTIPY_CLIENT_ID')
        secret = os.getenv('SPOTIPY_CLIENT_SECRET')

        self.client_credentials_manager = SpotifyClientCredentials(
            client_id=cid, client_secret=secret)

        # redirect_uri = 'http://localhost:8888/callback'
        # username = 'xxxx'
        self.scope = "user-library-read playlist-modify-public user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-recently-played user-read-playback-position user-top-read app-remote-control streaming"

        self.sp = spotipy.Spotify(client_credentials_manager=self.client_credentials_manager,
                            auth_manager=SpotifyOAuth(scope=self.scope))

    def check_latency(self):
        playing = self.sp.current_playback()
        playing2 = self.sp.current_playback()
        print(playing2['progress_ms'] - playing['progress_ms'])

    def get_likes(self, filename = None):
        results = self.sp.current_user_saved_tracks()
        likes = results['items']
        while results['next']:
            results = self.sp.next(results)
            likes.extend(results['items'])
        if filename:
            with open(filename, "w") as fw:
                json.dump(likes, fw, indent=2)
        else: return likes

    def currently_playing(self, filename=None):
        playing = self.sp.current_playback()
        if filename:
            with open(filename, "w") as fw:
                json.dump(playing, fw, indent=2)

        cp = playing['item']
        print(f"Listening {cp['name']} by {', '.join([a['name'] for a in cp['artists']])} [{cp['album']['name']}] on {playing['device']['name']}")

    def record(self, filename):
        os.system(f'parecord --latency-msec=1 -d alsa_output.pci-0000_05_00.6.analog-stereo.monitor --fix-channels --fix-format --fix-rate {filename} &')

        # premium required.
        # self.sp.pause_playback()
        # self.sp.start_playback()

    def search_sharelink(self, link=None, filename=None):
        track_id = link.split("track/")[1].split("?")[0]
        track = self.sp.track(track_id)

        if filename:
            with open(filename, "w") as fw:
                json.dump(track, fw, indent=2)
        return track

    def search_track(self, track_name=None, filename=None):
        if not track_name:
            print("No track specified")
            return None
        results = self.sp.search(q='track:' + track_name, type='track', limit=20)
        results = results['tracks']
        tracks = results['items']

        # while results['next']:
        #     results = self.sp.next(results)
        #     results = results['tracks']
        #     tracks.extend(results['items'])

        if filename:
            with open(filename, "w") as fw:
                json.dump(tracks, fw, indent=2)
        return tracks

    def print_track_info(self, info=None):
        if not info:
            print("No track info, exit")
            return None
        INFO(f"""
        name : {info['name']}
        type : {info['type']}
        duration_ms : {info['duration_ms']}
        id : {info['id']}
        popularity : {info['popularity']}

        # Artists
        artists_names : {', '.join([artist['name'] for artist in info['artists']])}
        album : {info['album']['name']} ({info['album']['album_type']}) - {info['album']['id']}
        album_image : {info['album']['images'][0]['url']}
        album_release_date : {info['album']['release_date']} ({info['album']['release_date_precision']})
        track_number : {info['track_number']} / {info['album']['total_tracks']}

        # More info
        FR_available : {True if "FR" in info['available_markets'] else False}
        is_local : {info['is_local']}
        href : {info['href']}
        disc_number : {info['disc_number']}
        explicit : {info['explicit']}
        external_urls['spotify'] : {info['external_urls']['spotify']}
        external_ids['isrc'] : {info['external_ids']['isrc']}
        preview_url : {info['preview_url']}
        uri : {info['uri']}
        """)

    __search_track = search_track
    __get_likes = get_likes


def main():
    sp = sp_instance()

    if len(sys.argv) == 1:
        INFO(f"Usage : python {sys.argv[0]} <query> or <share link>\n")
        print(f"Example : python {sys.argv[0]} song name author")
        print(f"          python {sys.argv[0]} https://open.spotify.com/track/X?si=Y")
        return

    if len(sys.argv) > 1:
        requested = " ".join(sys.argv[1:])

        if "open.spotify.com" in requested:
            try:
                track = sp.search_sharelink(requested, "track.json")
            except SpotifyException as e:
                ERROR(f"Track was not found")
                exit
            except Exception as e:
                DERROR(f"Track couldn't be found. Unexpected exception")
                exit
            else:
                artists = f"{', '.join([artist['name'] for artist in track['artists']])}"
                DINFO(f"{track['name']} - {artists} found")
        else:
            tracks = sp.search_track(requested, "track.json")

            id = 0
            if len(tracks) == 0:
                ERROR("No song found.")
                return
            elif len(tracks) > 1:
                INFO("\n".join([f"{itrack} : {track['name']} - {', '.join([artist['name'] for artist in track['artists']])} [{track['album']['name']}]" for itrack, track in enumerate(tracks)]))
                id = input("Choose id : ")
                if not id.isnumeric() or int(id) < 0 or int(id) > len(tracks)-1:
                    DERROR(f"Must be an integer from 0 to {len(tracks)-1}")
                    return
            track = tracks[int(id)]

    sp.print_track_info(track)
    uri = track['uri']
    duration_ms = track['duration_ms']
    duration_s = int(duration_ms / 1000) + 1
    filename = f"{track['name']} - {', '.join([artist['name'] for artist in track['artists']])}"
    filename = filename.replace(" ","_")
    os.system(f"./spotdl.sh {uri} \"{filename}\" {duration_s}")


if __name__ == "__main__":
    main()
