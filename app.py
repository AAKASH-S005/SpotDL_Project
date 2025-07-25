from flask import Flask, render_template, request, send_file, jsonify
import subprocess
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
import glob

app = Flask(__name__)

# ✅ Ensure downloads folder exists
Download_path = os.path.join(os.getcwd(), "downloads")
os.makedirs(Download_path, exist_ok=True)

# ✅ Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id="6d68856a91f648c4ad19dc60ab082675",
    client_secret="1bc5b338f4d645919104fe22fc0f9021"
))

@app.route('/')
def index():
    return render_template('about.html')

@app.route('/index')
def find_songs():
    return render_template('index.html')


# ✅ Song or Playlist Metadata
@app.route('/Song_details', methods=['POST'])
def get_song_details():
    data = request.get_json()
    spotify_url = data.get("song")

    if not spotify_url:
        return jsonify({"error": "Please enter a valid Spotify URL"}), 400

    try:
        if "playlist" in spotify_url:
            playlist_id = spotify_url.split("/")[-1].split("?")[0]
            playlist_info = sp.playlist_tracks(playlist_id)

            if not playlist_info.get("items"):
                return jsonify({"error": "Playlist is empty or not found"}), 404

            songs = []
            for index, item in enumerate(playlist_info["items"], start=1):
                track = item.get("track")
                if not track or "id" not in track:
                    continue
                songs.append({
                    "index": index,
                    "track_id": track["id"],
                    "title": track["name"],
                    "artists": [artist["name"] for artist in track["artists"]],
                    "album": track["album"]["name"],
                    "cover_url": track["album"]["images"][0]["url"] if track["album"]["images"] else ""
                })

            if not songs:
                return jsonify({"error": "No valid songs found in the playlist"}), 404

            return jsonify({"playlist": songs, "playlist_cover_url": songs[0]["cover_url"]})

        else:
            track_id = spotify_url.split("/")[-1].split("?")[0]
            metadata = sp.track(track_id)
            if not metadata or "id" not in metadata:
                return jsonify({"error": "Track not found"}), 404

            song_details = {
                "track_id": track_id,
                "title": metadata["name"],
                "artists": [artist["name"] for artist in metadata["artists"]],
                "album": metadata["album"]["name"],
                "cover_url": metadata["album"]["images"][0]["url"] if metadata["album"]["images"] else "",
            }
            return jsonify(song_details)

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


# ✅ Get Track Title
@app.route('/get_title', methods=['POST'])
def get_title():
    data = request.get_json()
    trackid = data.get('trackid')

    if not trackid:
        return jsonify({"error": "Invalid track ID"}), 400

    try:
        metadata = sp.track(trackid)
        title = metadata.get('name', 'Unknown Title')
        return jsonify(title)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch track details: {str(e)}"}), 500


# ✅ Download Track using spotdl
@app.route('/download_song', methods=['POST'])
def Download():
    data = request.get_json()
    url = data.get('url')
    file_format = data.get('format', 'mp3')

    if not url:
        return jsonify({"error": "Please enter a valid URL"}), 400

    try:
        # Clear old downloads
        for file in glob.glob(f"{Download_path}/*.{file_format}"):
            os.remove(file)

        # ✅ Add --bitrate
        output_template = os.path.join(Download_path, "{title}")
        command = ["spotdl", url, "--output", f"{output_template}.{file_format}", "--format", file_format, "--bitrate", "192k"]

        subprocess.run(command, check=True)

        # Wait for file system
        time.sleep(2)

        downloaded_files = sorted(
            glob.glob(f"{Download_path}/*.{file_format}"),
            key=os.path.getmtime,
            reverse=True
        )

        if downloaded_files:
            return send_file(downloaded_files[0], as_attachment=True)
        else:
            return jsonify({"error": "File not found after download"}), 500

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"spotdl failed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
