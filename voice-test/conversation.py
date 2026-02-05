#!/usr/bin/env python3
"""
Generate a voice conversation between two AI agents using Cartesia.
Emma (AI Agent) and Sarah (Lead) - Australian females
"""

import os
import json
import requests
import subprocess
from pathlib import Path

CARTESIA_API_KEY = "sk_car_ujsgJQvuJcLSkGdwdYY3VR"
OUTPUT_DIR = Path("/home/elliotbot/clawd/voice-test")

# Two different female voices
VOICE_EMMA = "f786b574-daa5-4673-aa0c-cbe3e8534c02"  # Katie - Friendly Fixer (for AI agent)
VOICE_SARAH = "e07c00bc-4134-4eae-9ea4-1a55fb45746b"  # Brooke - Big Sister (for lead)

# Conversation transcript
CONVERSATION = [
    ("emma", "Hey Sarah, this is Emma calling from Agency OS. I'm following up on an email we sent over — you'd mentioned you were interested in learning more about scaling your client acquisition. Did I catch you at an okay time?"),
    ("sarah", "Oh, yeah, I remember that. Um, I've got a few minutes. What is this about exactly?"),
    ("emma", "Perfect, I'll keep it quick. So we work specifically with agencies like Bloom Digital to help them book more qualified meetings without adding headcount. I saw you're doing some great work in the digital marketing space — are you currently looking to bring on more clients, or is the pipeline pretty full right now?"),
    ("sarah", "I mean, we're always looking for more clients. But honestly, most of our work comes from referrals. We've tried outbound before and it just didn't really work for us."),
    ("emma", "Yeah, I hear that a lot actually. When you say it didn't work — was that cold email, LinkedIn, or something else?"),
    ("sarah", "Mostly email. We tried it for a few months but barely got any responses. I think we sent like, I don't know, maybe a thousand emails? Got two meetings out of it. Didn't feel worth the effort."),
    ("emma", "Two meetings from a thousand emails — yeah, that's frustrating. That's like a 0.2% conversion rate. Were you doing that manually, or using some kind of tool?"),
    ("sarah", "Mostly manual. I mean, we used Mailchimp or something to send them, but finding the leads, writing the emails — that was all me. Between client work, I just couldn't keep up with it."),
    ("emma", "That makes total sense. So what we do is a bit different — we run multi-channel campaigns across email, LinkedIn, and even SMS, all automated. But the key thing is we target based on intent signals, so you're only reaching out to people who are actually in-market. Most of our agency clients see somewhere between 10 to 15 qualified meetings per month."),
    ("sarah", "10 to 15 meetings a month? That would be... I mean, we close maybe one in four. That would basically double our revenue."),
    ("emma", "Exactly. And you wouldn't have to do any of the outreach yourself — you'd just show up to the meetings. Would it make sense to schedule a quick call with one of our strategists? They can walk you through exactly how this would work for Bloom Digital specifically. Takes about 20 minutes."),
    ("sarah", "Um, yeah, actually. Yeah, let's do it. What times do you have?"),
    ("emma", "Great! I've got availability tomorrow at 2pm or Thursday at 10am. Either of those work for you?"),
    ("sarah", "Thursday at 10 works. Is that Sydney time?"),
    ("emma", "Yep, 10am Sydney time. Perfect. I'll send over a calendar invite to sarah@bloomdigital.com.au — is that still your best email?"),
    ("sarah", "That's the one."),
    ("emma", "Awesome. You'll get that invite in the next few minutes. Thanks so much for your time, Sarah — really looking forward to showing you what we can do for Bloom Digital."),
    ("sarah", "Sounds good. Thanks, Emma. Talk soon."),
]

def generate_audio(text: str, voice_id: str, output_path: Path) -> bool:
    """Generate audio using Cartesia API."""
    url = "https://api.cartesia.ai/tts/bytes"
    
    headers = {
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2025-04-16",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model_id": "sonic-2",
        "transcript": text,
        "voice": {
            "mode": "id",
            "id": voice_id
        },
        "language": "en",
        "output_format": {
            "container": "mp3",
            "bit_rate": 128000,
            "sample_rate": 44100
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"✓ Generated: {output_path.name}")
        return True
    else:
        print(f"✗ Failed: {response.status_code} - {response.text[:200]}")
        return False

def main():
    print("Generating voice conversation...\n")
    
    audio_files = []
    
    for i, (speaker, text) in enumerate(CONVERSATION):
        voice_id = VOICE_EMMA if speaker == "emma" else VOICE_SARAH
        output_path = OUTPUT_DIR / f"{i:02d}_{speaker}.mp3"
        
        if generate_audio(text, voice_id, output_path):
            audio_files.append(output_path)
    
    if len(audio_files) == len(CONVERSATION):
        print(f"\n✓ Generated {len(audio_files)} audio clips")
        
        # Create file list for ffmpeg
        list_file = OUTPUT_DIR / "files.txt"
        with open(list_file, "w") as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file}'\n")
        
        # Combine all audio files
        output_file = OUTPUT_DIR / "full_conversation.mp3"
        result = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_file)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✓ Combined into: {output_file}")
        else:
            print(f"✗ FFmpeg error: {result.stderr[:200]}")
    else:
        print(f"\n✗ Only generated {len(audio_files)}/{len(CONVERSATION)} clips")

if __name__ == "__main__":
    main()
