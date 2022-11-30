#!/bin/sh
### SPOTIFY RECORDER

command -v jq >/dev/null 2>&1 || { echo >&2 "jq was not found"; exit 1; }
command -v parecord >/dev/null 2>&1 || { echo >&2 "parecord was not found"; exit 1; }
command -v spotify >/dev/null 2>&1 || { echo >&2 "spotify was not found"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo >&2 "ffmpeg was not found"; exit 1; }
command -v mp3splt >/dev/null 2>&1 || { echo >&2 "mp3splt was not found"; exit 1; }

# Get Spotify's pulseaudio sink ID
get_spotify_sink(){
    spotify_sink=$(LANG=en python3 pactl-json-parser/pactl_parser.py | jq 'to_entries[] | {sink:.key} + {value:.value.Properties["media.name"]} | if (.value | contains("Spotify")) then .sink | tonumber else empty end' | tail -f -n1)
}


mkdir -p songs_build
mkdir -p songs

uri=$1
filename="$2"
duration="$3"

if [ -z "$uri" ] || [ -z "$filename" ] || [ -z "$duration" ]; then
    echo "Invalid usage, missing uri, filename or song duration."
    echo "Usage : $0 [URI] [filename] [song duration]"
fi

# Start Spotify using URI
pkill spotify
spotify --uri="$uri" > /dev/null 2>&1 &

export LANG="en_EN.UTF-8"

# Wait until Spotify's sink is spotted
while [ -z "$spotify_sink" ];
do 
    get_spotify_sink
done

# Start recording
parecord --latency-msec=1 --monitor-stream="$spotify_sink" --record --fix-channels --fix-format --fix-rate "songs_build/$filename.rec" &

echo "Recording $uri as $filename.mp3 for $duration seconds"

# Wait till the end & stop
sleep "$duration"
pkill parecord
pkill spotify

# Convert file & Trim it
ffmpeg -i "songs_build/$filename.rec" -acodec mp3 -b:a 320k "songs_build/$filename.mp3"
mp3splt -r -p rm -p min=0.3 -p trackmin="$(echo "$duration"-2 | bc)" "songs_build/$filename".mp3

if [ ! -f "songs_build/$filename"_trimmed.mp3 ];
then
    mv "songs_build/$filename.mp3" songs/"$(echo "$filename" | sed s/_/\ /g)".mp3
else
    mv "songs_build/$filename"_trimmed.mp3 songs/"$(echo "$filename" | sed s/_/\ /g)".mp3
fi;
