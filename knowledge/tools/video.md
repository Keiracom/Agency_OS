# Video & Design Tools

## ffmpeg
- **What:** Video/audio processing CLI
- **Install:** `sudo apt-get install ffmpeg`
- **Extract frames:** `ffmpeg -i video.mp4 -vf "fps=1" frame_%03d.jpg`
- **Extract at 5fps:** `ffmpeg -i video.mp4 -vf "fps=5" frame_%03d.jpg`
- **Get video info:** `ffprobe -v error -show_entries stream=duration,r_frame_rate video.mp4`
- **Learned:** 2026-01-30
- **Applied:** Landing page video → 82 frames

## screenshot-to-code
- **What:** AI-powered video/screenshot → working code
- **Repo:** https://github.com/abi/screenshot-to-code
- **Install:** 
  ```bash
  git clone https://github.com/abi/screenshot-to-code.git
  cd screenshot-to-code
  docker-compose up -d
  ```
- **Access:** http://localhost:5173
- **Requires:** Anthropic API key (we have it)
- **Output:** React + Tailwind code
- **Video mode:** Records 20 frames, generates interactive prototype
- **Learned:** 2026-01-30
- **Status:** Cloned, pending docker setup
