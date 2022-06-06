#!/bin/sh
### SPOTIFY RECORDER

get_spotify_sink(){
    spotify_sink=$(LANG=en python3 pactl-json-parser/pactl_parser.py | jq 'to_entries[] | {sink:.key} + {value:.value.Properties["media.name"]} | if (.value | contains("Spotify")) then .sink | tonumber else empty end' | tail -f -n1)
}


mkdir -p songs_build
mkdir -p songs

filename="test_audio"

# START RECORD BEFORE (LATENCY)
uri=$1
filename="$2"
duration="$3"

if [ "$uri" != none ];
then
    pkill spotify
    spotify --uri="$uri" > /dev/null 2>&1 &
fi

# SELECT SINK
export LANG="en_EN.UTF-8"

# Wait until Spotify's sink is spotted
while [ -z "$spotify_sink" ];
do 
    get_spotify_sink
done

# Start recording
parecord --latency-msec=1 --monitor-stream="$spotify_sink" --record --fix-channels --fix-format --fix-rate "songs_build/$filename" &

echo "Recording $uri as $filename.mp3 for $duration seconds"

# Wait till the end & stop
sleep "$duration"
pkill parecord
pkill spotify

# Convert file & Trim it
ffmpeg -i "songs_build/$filename" -acodec mp3 -b:a 320k "songs_build/$filename.mp3"
mp3splt -r -p rm -p min=0.3 -p trackmin="$(echo "$duration"-2 | bc)" "songs_build/$filename".mp3

if [ ! -f "songs_build/$filename"_trimmed.mp3 ];
then
    mv "songs_build/$filename.mp3" songs/"$(echo "$filename" | sed s/_/\ /g)".mp3
else
    mv "songs_build/$filename"_trimmed.mp3 songs/"$(echo "$filename" | sed s/_/\ /g)".mp3
fi;
