#!/bin/sh
### SPOTIFY RECORDER

# command -v jq >/dev/null 2>&1 || { echo >&2 "jq was not found"; exit 1; }
command -v spotify >/dev/null 2>&1 || { echo >&2 "spotify was not found"; exit 1; }
command -v grep >/dev/null 2>&1 || { echo >&2 "grep was not found"; exit 1; }
command -v tr >/dev/null 2>&1 || { echo >&2 "tr was not found"; exit 1; }
command -v pactl >/dev/null 2>&1 || { echo >&2 "pactl was not found"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo >&2 "ffmpeg was not found"; exit 1; }
command -v mp3splt >/dev/null 2>&1 || { echo >&2 "mp3splt was not found"; exit 1; }

# Check if sound server is pipewire
pactl info | grep -i pipewire && pipewire=1 || pipewire=0
printf "Sound Server : " 
[ $pipewire = 1 ] && echo "PipeWire" || echo "PulseAudio"

if [ $pipewire = 1 ]; then 
    command -v pw-record >/dev/null 2>&1 || { echo >&2 "pw-record was not found"; exit 1; }
else
    command -v parecord >/dev/null 2>&1 || { echo >&2 "parecord was not found"; exit 1; }
fi

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

if [ ! -z $verbose ]; then
    echo "* URI      : $uri"
    echo "* filename : $filename"
    echo "* duration : $duration"
    echo "* Verbose  : $verbose"
fi

if [ $pipewire = 0 ]; then
    # Get default output
    pactl_default_output=$(pactl get-default-sink)
    # pactl_default_source=$(pactl get-default-source)
    module_name="rec-play"

    if ! pactl list sinks | grep "$module_name" > /dev/null;
    then
        printf "[ ] Loading new module %s" "$module_name"
        record_id=$(pactl load-module module-combine-sink sink_name="$module_name" slaves="$pactl_default_output" sink_properties=device.description="[spotify-recorder]Record-and-Play") # channels=2 channel_map=stereo remix=no
    else
        record_id=$(pactl list short modules | grep "$module_name" | grep -Eo "^[0-9]*")
    fi

    if ! pactl list sinks | grep "$module_name" > /dev/null; then
        printf "\r[!] Error : Loading new module %s\n" "$module_name"
        exit 1;
    elif [ -n "$verbose" ]; then
        printf "\r[x] Module loaded %s : %s\n" "$module_name" "$record_id"
    else
        printf "\r"
    fi
fi

# Set default sink for starting recording before spotify sink is spotted
# pactl set-default-sink "$module_name"

# Start Spotify using URI
pkill spotify
spotify --uri="$uri" > /dev/null 2>&1 &

# Start recording before spotify_sink is spotted
[ $pipewire = 0 ] && (parecord --latency-msec=20 --device="$module_name".monitor --record --fix-channels --fix-format --fix-rate "songs_build/$filename.rec" || (printf "[!] Error : Recording\n"; exit 0)) &

# (pw-record --latency=20ms --target="$module_name".monitor "songs_build/$filename.rec" || (printf "[!] Error : Recording\n"; exit 0)) &

# Wait until Spotify's sink is spotted
while [ -z "$spotify_sink" ];
do
    get_spotify_sink
done

if [ $pipewire = 0 ]; then
    pactl move-sink-input "$spotify_sink" "$module_name"
else
    # using `pw-top` to match spotify's format and rate
    pw-record --latency=20ms --volume=1.0 --format=f32 --channel-map stereo --latency=20ms --rate 44100 --target="$spotify_sink" "songs_build/$filename.rec" &
fi

# Start recording
# parecord --latency-msec=1 --monitor-stream="$spotify_sink" --record --fix-channels --fix-format --fix-rate "songs_build/$filename.rec" &

printf "==> Recording %s as \"%s\" for %s seconds\r" "$uri" "$filename.mp3" "$duration"

# Wait till the end & stop
sleep "$duration"
# 0.05 to 0.1 lost (but we don't care as spotify takes some time to play)
pkill spotify
[ $pipewire = 1 ] && pkill pw-record || pkill parecord

# Convert file & Trim it
[ -z $verbose ] && verbose_flags="-hide_banner -loglevel error"
ffmpeg $verbose_flags -y -i "songs_build/$filename.rec" -acodec mp3 -b:a 320k "songs_build/$filename.mp3"
[ -z $verbose ] && verbose_flags="-q"
mp3splt $verbose_flags -r -p rm -p min=0.3 -p trackmin="$(echo "$duration"-2 | bc)" "songs_build/$filename".mp3 | ( [ -z "$verbose" ] || grep -Ev "^ info:" )

final_filepath="songs/$filename.mp3"

[ ! -f "songs_build/$filename"_trimmed.mp3 ] && f="songs_build/$filename.mp3" || f="songs_build/$filename"_trimmed.mp3;
mv "$f" "$final_filepath"
printf "\033[K[+] File saved at %s\n" "$final_filepath"

# Back to default settings
[ $pipewire = 0 ] && pactl unload-module "$record_id"
# pactl set-default-sink "$pactl_default_output"
