#!/bin/sh
### SPOTIFY RECORDER

# command -v jq >/dev/null 2>&1 || { echo >&2 "jq was not found"; exit 1; }
command -v grep >/dev/null 2>&1 || { echo >&2 "grep was not found"; exit 1; }
command -v tr >/dev/null 2>&1 || { echo >&2 "tr was not found"; exit 1; }
command -v parecord >/dev/null 2>&1 || { echo >&2 "parecord was not found"; exit 1; }
command -v spotify >/dev/null 2>&1 || { echo >&2 "spotify was not found"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo >&2 "ffmpeg was not found"; exit 1; }
command -v mp3splt >/dev/null 2>&1 || { echo >&2 "mp3splt was not found"; exit 1; }

# Get Spotify's pulseaudio sink ID
get_spotify_sink(){
    # spotify_sink=$(LANG=en python3 pactl-json-parser/pactl_parser.py | jq 'to_entries[] | {sink:.key} + {value:.value.Properties["media.name"]} | if (.value | contains("Spotify")) then .sink | tonumber else empty end' | tail -f -n1)
    # spotify_sink=$(pactl list sink-inputs | grep -E "Input #|media.name" | xargs | grep -Eoi "#[0-9]* media.name = Spotify" | grep -oi "[0-9]*") # 8x faster
    spotify_sink=$(pactl list sink-inputs | grep -E "Input #|media.name" | tr -d "[:space:]" | tr -d "\"" | grep -Eoi "#[0-9]*media.name=Spotify" | grep -oi "[0-9]*") # 1.3x even faster + remove xargs dependency
}


mkdir -p songs_build
mkdir -p songs

uri=$1
filename="$2"
duration="$3"
verbose="$4"

if [ -z "$uri" ] || [ -z "$filename" ] || [ -z "$duration" ]; then
    echo "Invalid usage, missing uri, filename or song duration."
    echo "Usage : $0 [URI] [filename] [song duration]"
fi

# Get default output
pactl_default_output=$(pactl get-default-sink)
if ! pactl list sinks | grep rec-play > /dev/null;
then
    echo "Load new module rec-play"
    pactl load-module module-combine-sink sink_name=rec-play slaves="$pactl_default_output" sink_properties=device.description="[spotify-recorder]Record-and-Play"
fi

if ! pactl list sinks | grep rec-play > /dev/null; then
    echo "Load failed ... exit";
    exit 1;
fi

# Set default sink for starting recording before spotify sink is spotted
pactl set-default-sink rec-play

# Start Spotify using URI
pkill spotify
spotify --uri="$uri" > /dev/null 2>&1 &

export LANG="en_EN.UTF-8"

# Start recording before spotify_sink is spotted
parecord --latency-msec=20 --device=rec-play.monitor --record --fix-channels --fix-format --fix-rate "songs_build/$filename.rec" &

# Wait until Spotify's sink is spotted
while [ -z "$spotify_sink" ];
do
    get_spotify_sink
done

# Start recording
# parecord --latency-msec=1 --monitor-stream="$spotify_sink" --record --fix-channels --fix-format --fix-rate "songs_build/$filename.rec" &

echo "Recording $uri as \"$filename.mp3\" for $duration seconds"

# Wait till the end & stop
sleep "$duration"
pkill parecord
pkill spotify

# Convert file & Trim it
echo "$verbose"
[ -z "$verbose" ] && verbose_flags=" -hide_banner -loglevel error"
ffmpeg $verbose_flags -i "songs_build/$filename.rec" -acodec mp3 -b:a 320k "songs_build/$filename.mp3"
[ -z "$verbose" ] && verbose_flags="-q"
mp3splt $verbose_flags -r -p rm -p min=0.3 -p trackmin="$(echo "$duration"-2 | bc)" "songs_build/$filename".mp3 | ( [ -z "$verbose" ] || grep -Ev "^ info:" )

final_filepath="songs/$filename.mp3"

[ ! -f "songs_build/$filename"_trimmed.mp3 ] && f="songs_build/$filename.mp3" || f="songs_build/$filename"_trimmed.mp3;
mv "$f" "$final_filepath"

# Set back the default sink
pactl set-default-sink "$pactl_default_output"