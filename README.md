# OmniFetch

OmniFetch is a local web app for checking a public media link, selecting MP4/MKV/MP3 and video quality, reviewing an estimated size, and saving the prepared file through your browser's normal Downloads flow.

## Run it on Windows

1. Install 64-bit Python 3.10 through 3.14. Python 3.14 is recommended. Python 3.15 currently makes pip try to compile OmniFetch's Brotli dependency on Windows, which fails unless a compatible wheel is available. [Download Python 3.14.8 from Python.org](https://www.python.org/downloads/release/python-3148/).
2. Install FFmpeg and make sure **ffmpeg** and **ffprobe** are available on PATH. They are needed for MP3 conversion and for combining separate audio/video streams.
3. Double-click **start.bat**. It selects Python 3.14 or earlier if available, creates a private Python environment, and installs the app packages. If an earlier attempt created the app's `.venv` using Python 3.15, the updated installer replaces that environment automatically.
4. Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in your browser.
5. Paste a public link, choose a format and quality, and select **Check link**.
6. Select **Download media**, review the estimated size, and choose **Confirm & prepare**.
7. When preparation finishes, the app shows the final size. Select **Save to Downloads** to start the browser download.

The browser uses its configured download location. If it is set to ask where to save files, choose the Downloads folder in the browser prompt.

The size shown before preparation is an estimate. The app uses the advertised stream size when available and estimates from duration and bitrate when needed. The final file size may differ, especially for MP3 conversion or merged streams.

## What the app supports

- Public links on YouTube, Instagram, TikTok, X, and Twitter.
- MP4, MKV, or MP3 output.
- Maximum video quality of 480p, 720p, 1080p, or 2160p when available.
- One media item per link.

The app does not use account cookies or sign-in credentials. Private, sign-in-only, and DRM-protected media are not supported. Only save media you own or have permission to download.

The Python server binds to 127.0.0.1, so it runs on your computer and is not open to other devices on the network. Preparing a file needs temporary disk space about the size of the selected media. Prepared files are held in a temporary folder and removed after the browser download or after one hour.

## Hosting

The Tiiny Host page is static HTML and cannot run this Python backend. A public version needs a Python-capable server that hosts both index.html and app.py, plus appropriate authentication and abuse protections. The app in this folder is configured for local use and deliberately binds only to your own computer.

## Dependencies

This app uses [Flask](https://flask.palletsprojects.com/) for its local web interface and [yt-dlp](https://github.com/yt-dlp/yt-dlp) to inspect and prepare media. The yt-dlp default package installs its EJS component. Full YouTube support also needs a supported JavaScript runtime such as Node.js 22+ or Deno 2.3+. FFmpeg/ffprobe are required for merging and post-processing. See the [yt-dlp dependency notes](https://github.com/yt-dlp/yt-dlp#dependencies) and [EJS setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

If setup previously failed while building a Brotli wheel, install Python 3.14 (64-bit) from the link above and run **start.bat** again. The installer now detects Python 3.15 and stops with instructions instead of attempting that failed build. You do not need to install Microsoft C++ Build Tools for this issue.
