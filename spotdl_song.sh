#!/bin/sh
### SPOTIFY RECORDER

# USING SPOTIFY'S APP


mkdir -p songs_build
mkdir -p songs

filename="test_audio"

# START RECORD BEFORE (LATENCY)
uri=$1
filename="$2"
duration="$3"

# parecord --latency-msec=1 --device=spotrec.monitor --fix-format --fix-rate --fix-channels "$filename" &
# parecord --latency-msec=1 --monitor-stream=0 --record --fix-channels --fix-format --fix-rate test.mp3

# parecord --latency-msec=1 -d alsa_output.pci-0000_05_00.6.analog-stereo.monitor --fix-format --fix-rate --fix-channels "$filename" &


if [ "$uri" != none ];
then
    pkill spotify
    spotify --uri="$uri" > /dev/null 2>&1 &
fi

# SELECT SINK
export LANG="en_EN.UTF-8"

# If not started
# spotrec_status=$(pactl list modules | grep -c spotrec)
# if [ "$spotrec_status" -eq 0 ]
# then
#     pactl load-module module-combine-sink sink_name=spotrec
#     # pactl load-module module-null-sink sink_name=spotrec
#     echo "New sink module : spotrect"
#     # pactl set-default-sink spot_rec.monitor
# fi

while [ -z "$(LANG=en python3 pactl-json-parser/pactl_parser.py | jq 'to_entries[] | {sink:.key} + {value:.value.Properties["media.name"]} | if (.value | contains("Spotify")) then .sink | tonumber else empty end')" ];
do 
    :
done

spotify_sink=$(LANG=en python3 pactl-json-parser/pactl_parser.py | jq 'to_entries[] | {sink:.key} + {value:.value.Properties["media.name"]} | if (.value | contains("Spotify")) then .sink | tonumber else empty end' | tail -f -n1)
# echo $spotify_sink

parecord --latency-msec=1 --monitor-stream="$spotify_sink" --record --fix-channels --fix-format --fix-rate "songs_build/$filename" &

# pactl move-sink-input "$spotify_sink" spotrec

echo "Recording $uri as $filename.mp3 for $duration seconds"

# parecord --device=spotrec.monitor --fix-format --fix-rate --fix-channels $filename &
# sleep "$duration"
sleep 2
pkill parecord
pkill spotify
ffmpeg -i "songs_build/$filename" -acodec mp3 -b:a 320k "songs_build/$filename.mp3"
mp3splt -r -p rm -p min=0.3 -p trackmin="$(echo "$duration"-2 | bc)" "songs_build/$filename".mp3

if [ ! -f "songs_build/$filename"_trimmed.mp3 ];
then
    mv "songs_build/$filename.mp3" songs/"$(echo "$filename" | sed s/_/\ /g)".mp3
else
    mv "songs_build/$filename"_trimmed.mp3 songs/"$(echo "$filename" | sed s/_/\ /g)".mp3
fi;


# pactl load-module module-null-sink sink_name=spotrec
# pactl load-module module-combine-sink sink_name=spot_rec
# pactl set-default-source spot_rec.monitor
# parecord --device=spot_rec.monitor --fix-format --fix-rate --fix-channels filename