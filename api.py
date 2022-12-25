import spotipy
from spotipy.exceptions import *
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import dotenv
import json
import os
import sys
from utils import *
import subprocess
import argparse

dotenv.load_dotenv()


class sp_instance:
    def __init__(self):
        self.sp = None
        # Basic manager
        # sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

        # User-data manager
        cid = os.getenv('SPOTIPY_CLIENT_ID')
        secret = os.getenv('SPOTIPY_CLIENT_SECRET')

        self.client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)

        # redirect_uri = 'http://localhost:8888/callback'
        # username = 'xxxx'
        self.scope = "user-library-read playlist-modify-public user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-recently-played user-read-playback-position user-top-read app-remote-control streaming"

        self.sp = spotipy.Spotify(client_credentials_manager=self.client_credentials_manager, auth_manager=SpotifyOAuth(scope=self.scope))

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
    #             json.dump(likes, fw, indent=2)
    #     else:
    #         return likes

    # def currently_playing(self, filename=None):
    #     playing = self.sp.current_playback()
    #     if filename:
    #         with open(filename, "w") as fw:
    #             json.dump(playing, fw, indent=2)

    #     cp = playing['item']
    #     print(f"Listening {cp['name']} by {', '.join([a['name'] for a in cp['artists']])} [{cp['album']['name']}] on {playing['device']['name']}")

    # def get_spotify_sink(self):
    #     p = subprocess.run(
    #         """get_spotify_sink(){ spotify_sink=$(LANG=en python3 pactl-json-parser/pactl_parser.py | jq 'to_entries[] | {sink:.key} + {value:.value.Properties["media.name"]} | if (.value | contains("Spotify")) then .sink | tonumber else empty end' | tail -f -n1); }; while [ -z "$spotify_sink" ]; do get_spotify_sink; done; echo $spotify_sink""",
    #         shell=True, capture_output=True)
    #     result = p.stdout.decode()
    #     print(result.strip())

    # def record(self, filename):
    #     os.system(f'parecord --latency-msec=1 -d alsa_output.pci-0000_05_00.6.analog-stereo.monitor --fix-channels --fix-format --fix-rate {filename} &')

    #     # premium required.
    #     # self.sp.pause_playback()
    #     # self.sp.start_playback()

    # def search_sharelink(self, link=None, filename=None):
    def track_by_id(self, track_id=None, filename=None):
        # track_id = link.split("track/")[1].split("?")[0]
        try:
            track = self.sp.track(track_id)
        except SpotifyException as e:
            return ERROR(f"Track id was not found : {track_id} ")
        except Exception as e:
            DERROR(f"Unexpected exception : Track id couldn't be found : {track_id} ")
            return DERROR(e)

        if filename:
            with open(filename, "w") as fw:
                json.dump(track, fw, indent=2)
        return track

    def check_file_exists(self, filename):
        filepath = f"songs/{filename}.mp3"
        return filepath if os.path.exists(filepath) else False

    def record_track(self, track_info=None):
        # self.sp.print_track_info(track_info)
        uri = track_info['uri']
        duration_ms = track_info['duration_ms']
        duration_s = int(duration_ms / 1000) + 1
        filename = f"{track_info['name']} - {','.join([artist['name'] for artist in track_info['artists']])}"

        if filepath := self.check_file_exists(filename):
            DINFO(f"Song was already recorded at {filepath}")
            return True

        filename = filename.replace(" ", "_")

        os.system(f"./spotdl.sh {uri} \"{filename}\" {duration_s}")

    def search_track(self, track_name=None, filename=None):
        if not track_name:
            DINFO("No track specified")
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

    def playlist_by_id(self, playlist_id=None, filename=None):
        if not playlist_id:
            INFO("No playlist specified")
            return None
        results = self.sp.playlist(playlist_id)
        if filename:
            with open(filename, "w") as fw:
                json.dump(results, fw, indent=2)
        return results

    def print_track_info(self, info=None):
        if not info:
            DINFO("No track info, exit")
            return None


# print(f"{C.BOLD}{C.GREEN}{'Times':5}{C.YELLOW}{'Time'}\t{C.CYAN}{'Window Name'}{C.END}\n")

        print(f"""{C.BOLD}{C.YELLOW}Track{C.END}
* name : {C.YELLOW}{info['name']}{C.END}
* type : {info['type']}
* duration_ms : {info['duration_ms']}
* id : {info['id']}
* popularity : {info['popularity']}

{C.BOLD}{C.YELLOW}Artist(s){C.END}
* artists_names : {C.YELLOW}{', '.join([artist['name'] for artist in info['artists']])}{C.END}
* album : {info['album']['name']} ({info['album']['album_type']}) - {info['album']['id']}
* album_image : {info['album']['images'][0]['url']}
* album_release_date : {info['album']['release_date']} ({info['album']['release_date_precision']})
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

    __search_track = search_track
    # __get_likes = get_likes


def main():
    parser = argparse.ArgumentParser(description='Spotify Recorder')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Enable verbose mode")
    parser.add_argument("links", action='store', nargs='+')
    parser.add_argument('-s', '--search', action='store', nargs=1, help="Search for a song")
    parser.add_argument('--headless', action='store_true', default=False, help="Enable spotify headless mode (requires xfvb)")

    args = parser.parse_args()
    # args, unknown = parser.parse_known_args()
    if args.verbose:
        DINFO(f"Arguments : {args}")

    sp = sp_instance()

    if len(args.links) == 0:
        INFO(f"Usage : python {sys.argv[0]} <share link> or <query>\n")
        print(f"Example : python3 {sys.argv[0]} https://open.spotify.com/track/X")
        print(f"          python3 {sys.argv[0]} https://open.spotify.com/playlist/X")
        print(f"          python3 {sys.argv[0]} song name author")
        return

    if args.search:
        requested = " ".join(args.links)

        if args.verbose:
            DINFO(f"Requested : {requested}")

        tracks = sp.search_track(requested, "tracks.json")

        id = 0
        if len(tracks) == 0:
            ERROR("No song found.")
            return
        elif len(tracks) > 1:
            INFO("\n".join([
                f"{itrack} : {track['name']} - {', '.join([artist['name'] for artist in track['artists']])} [{track['album']['name']}]"
                for itrack, track in enumerate(tracks)]))
            id = input("Choose id : ")
            if not id.isnumeric() or int(id) < 0 or int(id) > len(tracks) - 1:
                DERROR(f"Must be an integer from 0 to {len(tracks)-1}")
                return
        track_info = tracks[int(id)]
        if args.verbose: sp.print_track_info(track_info)
        sp.record_track(track_info)
        return

    for link in args.links:
        type, id = sp.link_to_id(link)
        if args.verbose:
            DINFO(f"Requested : [{type}] {id}")

        if type == "track":
            track_info = sp.track_by_id(id)
            if args.verbose: sp.print_track_info(track_info)
            sp.record_track(track_info)

        elif type == "playlist":
            playlist = sp.playlist_by_id(id, "playlist.json")

            for track_info in playlist['tracks']['items']:
                if track_info['is_local'] ==True:
                    # DINFO(f"Local track : {track_info['track']['name']} - {','.join([artist for artist in track_info['track']['artists']])}")
                    continue
                track_info = track_info['track']
                # track_id = track_info['track']['id']
                if args.verbose: sp.print_track_info(track_info)
                sp.record_track(track_info)


if __name__ == "__main__":
    main()
