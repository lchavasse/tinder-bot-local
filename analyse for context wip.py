from playwright.sync_api import sync_playwright
import time
import os
import dotenv
import json
from datetime import datetime
import uuid
from openai import OpenAI
import base64
import openai

from classes.tinder import TinderAutomation

dotenv.load_dotenv()
facebook_email = os.getenv("FACEBOOK_EMAIL")
facebook_password = os.getenv("FACEBOOK_PASSWORD")
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)

from PIL import Image

def compress_and_grayscale(input_path, output_path, quality=30, grayscale=False):
    """
    Compresses and optionally converts an image to grayscale.
    
    Parameters:
        input_path (str): Path to the input image.
        output_path (str): Path to save the processed image.
        quality (int): Compression quality (1-100, lower means more compression).
        grayscale (bool): Whether to convert the image to grayscale.
    """
    try:
        # Open the image
        with Image.open(input_path) as img:
            # Convert to grayscale if required
            if grayscale:
                img = img.convert("L")
            
            # Save with compression
            img.save(output_path, "JPEG", quality=quality)
            print(f"Image saved to {output_path} with quality={quality} and grayscale={grayscale}")
    except Exception as e:
        print(f"Error processing image {input_path}: {e}")



def analyze_images(id):
    outputs = []

    system_prompt = "You are a matchmaking assistant for the users Tinder account. Please analyse a set of photos of another profile you are given"

    initial_prompts = [
        'Identify any specific sports or activities from the photos and return them in a list. Return only the list as a comma separated string',
        'Can you identify any specific locations from the photos, such as a city or country. If yes, please return a list of all locations as a comma separated string, if no, return "None"',
        """Now establish traits of the person in photos. Some of the photos may contain multiple people, you should analyse all of the photos to identify which person the profile belongs to, then return to each photo and identify any characteristics of the person in the profile.
Please be suitably harsh. This information needs to distinguish between people. They should not all be rated as good.
Please return you answer giving keyword or phrases  in a list"""
    ]
    
    # Find all images for the given ID
    image_files = [f for f in os.listdir("./images") if f.startswith(f"{id}_") and f.endswith(".png")]
    
    if not image_files:
        raise FileNotFoundError(f"No images found for ID: {id}")
    else:
        print(f"Found {len(image_files)} images for ID: {id}")
    
    # Process all images
    base64_images = []
    for image_file in image_files:
        compress_and_grayscale(os.path.join("./images", image_file), os.path.join("./images", "compressed_temp.png"), quality=30, grayscale=True)
        with open(os.path.join("./images", "compressed_temp.png"), "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
            base64_images.append(base64_image)

    print('images converted')

    # Construct the messages array with all images
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyse the following profile images."},
            ]
        }
    ]

    # Add all profile images
    for base64_image in base64_images:
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
        })

    print('calling api')
    for prompt in initial_prompts:
        if len(messages) == 2:
            print('adding prompt to user message')
            messages[1]["content"].append({"type": "text", "text": prompt})
        else:
            print('adding prompt as new user message')
            messages.append({"role": "user", "content": prompt})
        # Retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.5,
                    max_tokens=10000
                )
                output = response.choices[0].message.content
                print(output)
                outputs.append(output)
                messages.append({"role": "assistant", "content": output})
                break  # Exit the retry loop if successful
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retrying
                else:
                    raise  # Re-raise the exception if all retries fail
        

    return outputs

try:
    tinder_bot = TinderAutomation()
    tinder_bot.open_tinder(facebook_email, facebook_password)
    profiles = []
    for i in range(3):
        profile_data = tinder_bot.view_profile()
        outputs = analyze_images(profile_data['id'])
        profile_data['llm_activities'] = outputs[0]
        if outputs[1] != 'None':
            profile_data['llm_locations'] = outputs[1]
        condensed_output = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": 'Extract from the following evaluation of a person keywords that define them'},
                {"role": "user", "content": str(outputs[2])}
            ],
            temperature=0.5,
            max_tokens=10000
        )
        profile_data['llm_traits'] = condensed_output.choices[0].message.content
        profiles.append(profile_data)
        print('swiping...')
        tinder_bot.page.keyboard.press('ArrowRight')
        tinder_bot.page.wait_for_timeout(1000)

    tinder_bot.save_profiles(profiles)
finally:
    tinder_bot.cleanup()