# OmniFetch

OmniFetch checks a public media link, offers MP4/MKV/MP3 and video quality choices, estimates the size, and saves the prepared file through your browser's normal Downloads flow. It can run locally or as an open public website.

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

- Public links on YouTube, Snapchat Spotlight, Instagram, TikTok, X, and Twitter. Snapchat support covers Spotlight links recognized by yt-dlp.
- MP4, MKV, or MP3 output.
- Maximum video quality of 480p, 720p, 1080p, or 2160p when available.
- One media item per link.

The app does not use account cookies or sign-in credentials. Private, sign-in-only, and DRM-protected media are not supported. Only save media you own or have permission to download.

The local Python server binds to 127.0.0.1, so it runs on your computer and is not open to other devices on the network. Preparing a file needs temporary disk space about the size of the selected media. Prepared files are held in a temporary folder and removed after the browser download or after one hour.

## Publish it publicly

This package includes a Dockerfile and Render Blueprint for a public web service. The public service is open without a password, so anyone with its URL can request media preparation. It accepts only links from the supported media platforms, limits API requests to 20 per minute per IP, and prepares one file at a time. Prepared files are temporary and removed after the download or after one hour. Only use it for media you own or have permission to save.

To publish: upload the files at this folder's root to a GitHub repository, then in Render choose **New > Blueprint** and connect that repository. Render builds the service from `render.yaml` and gives it an `onrender.com` URL. The OmniFetch GitHub repository used for this deployment is public, so its source files are visible to everyone. Do not put passwords, browser cookies, API keys, or other private information in the repository. Render web services need to bind to `0.0.0.0`, which the included Docker start command does.

The Blueprint selects Render's Free service for a first deployment. Free services sleep after 15 minutes without traffic, may take about a minute to wake, have temporary storage, and have usage and bandwidth limits. If included bandwidth is exceeded, Render may bill for additional usage. This is suitable for trying the site, not for promising reliable service to everyone. Check the current [Render Free plan limits](https://render.com/docs/free) before deploying it publicly.

The free `onrender.com` address works without buying a domain. A `www.your-domain` address requires a domain you own; add it to the service in Render and configure DNS with your domain provider. See [Render custom domains](https://render.com/docs/custom-domains).

## Dependencies

This app uses [Flask](https://flask.palletsprojects.com/) for its web interface and [yt-dlp](https://github.com/yt-dlp/yt-dlp) to inspect and prepare media. The yt-dlp default package installs its EJS component. Full YouTube support also needs a supported JavaScript runtime such as Node.js 22+ or Deno 2.3+. FFmpeg/ffprobe are required for merging and post-processing. See the [yt-dlp dependency notes](https://github.com/yt-dlp/yt-dlp#dependencies) and [EJS setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

If setup previously failed while building a Brotli wheel, install Python 3.14 (64-bit) from the link above and run **start.bat** again. The installer now detects Python 3.15 and stops with instructions instead of attempting that failed build. You do not need to install Microsoft C++ Build Tools for this issue.
