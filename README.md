# Spotify-recorder

Spotify-recorder is, as it name suggest a Spotify recorder for Linux.
Given a song name URI or a share link, it starts Spotify with the given song, records it in its maximum bitrate (160 for free accounts, 320 for premium accounts), and finaly close. There you go ! You get the song in MP3 format.

> This tool is (for now) Linux exclusive. As long as the dependencies are met, it should work fine.

> This tool is in beta stage. Please don't mind if you you encounter a problem, and feel free to open an Issue for any suggestion or bug !

## Features :
- Record a song given a title name
- Record a song given an URI/share link

Features to be added in future :
- Add bitrate and file extension choice support.
- Record a song based on user's likes.
- Record the current played song.
- Record multiple songs, and split them.
- Add support for pipewire

## Installation : 
`git clone https://github.com/fm16191/spotify-recorder.git`

`cd spotify-recorder`

`pip install -r requirements.txt`

## Usage :
`py api.py query`
`<query> could take the format of <song name author>`
This will lookup for the query, and if multiple results, ask for one.
Then starts Spotify with the song's uri, plays and records it, and then quit.

final files

## Recommended Spotify setup

Disable all music fading (improve song trimming)
![spotify_settings_0.png](spotify_settings_0.png)

Improve audio quality
![spotify_settings_1.png](spotify_settings_1.png)


## Recommended pulseaudio setup
- In `/etc/pulse` edit the `default.pa` file and uncomment the `load-module module-udev-detect`, and change it for `load-module module-udev-detect tsched=0`
This would greatly improve the sink latency for recording

- In `/etc/pulse` edit the `daemon.conf` file and add `avoir-resampling = true`
If you still getting audio crackling, you can overwrite the defaults for `default-fragments = 2` and `default-fragment-size-msec = 10`

## Dependances :
`Python 3+` with `python-dotenv` and `spotipy` modules.

`jq, mp3splt, ffmpeg`


## Known issues : 

*Due to Pulseaudio sink latency, after a while, audio might start to overwrite itself, resulting in an awful output.* **Solution** -> restart Spotify
