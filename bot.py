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

def compress_and_grayscale(input_path, output_path, quality=50, grayscale=False):
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

    system_prompt = """You are assisting a young, attractive male in his 20s who is articulate, active, adventurous, and inquisitive. He is searching for fun, attractive women who are compatible with his dynamic lifestyle, tastes, and desires.
This user has a vibrant personality and enjoys exploring new activities, engaging in stimulating conversations, and maintaining an active and health-conscious lifestyle. He appreciates individuality and seeks someone who shares his enthusiasm for adventure, curiosity, and ambition.


You will be given profile photos of a potential match, and you must evaluate the quality of this match out of 100.
Please evaluate the candidate based on their compatibility with the user above - they should have many things in common. When analyzing profiles, focus on identifying women whose traits, style, or demeanor align with the user's. Consider additional  aspects such as confidence, sense of adventure, and intellectual curiosity. Provide detailed observations and hypothesize how certain characteristics might complement or resonate with the user's personality and preferences.

Some of the photos may contain multiple people, you should analyse all of the photos to identify which person the profile belongs to, then return to each photo and identify any characteristics of the person in the profile.
Please be suitably harsh. This information needs to distinguish between potential matches. They should not all be rated as good.
Note the photos have been compressed and are in grayscale, so you should not judge them based on their quality. The photos you see are for one candidate only.
Go through each photo and explain what features you identify that define the person and how they might attract the user.
Then considering all of the photos together, please return a rating of how attractive the person is to the user on a scale of 1 to 100, with 1 being the lowest and 100 being the highest. A rating of 70 or above should be exceptional (i.e. only happen for 1 out of every 10 profiles). A rating of 50 is average. If you analyse 10 profiles, 4 of them shoukld be rated below 60.
Return ###RATING### followed by only a single number between 1 and 100. """
    
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
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=10000
    )
    output = response.choices[0].message.content
    print(output)
    return output

def extract_info(profile_data):
    system_prompt = """You are given an analysis of three profile photos of a potential dating partner for a young, attractive male in his 20s.
    Extract from this analysis key words and phrases that describe the person, their interests, and their lifestyle.
    Return these as a list of strings in this fomrat: ["one","two","three",etc.]. Do not include new lines or escape characters. You should aim for 10-15 items.
    DO NOT RETURN ANYTHING ELSE.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [{"type": "text", "text": "Extract key words and phrases from the following analysis:"}, {"type": "text", "text": profile_data}]}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )

    extracted_info = response.choices[0].message.content
    print(extracted_info)
    return extracted_info


try:
    tinder_bot = TinderAutomation()
    tinder_bot.open_tinder(facebook_email, facebook_password)
    profiles = []
    for i in range(10):
        profile_data = tinder_bot.view_profile()
        if profile_data['distance'] is not None:
            if int(profile_data['distance']) > 20:
                print('too far away - distance:', profile_data['distance'])
                tinder_bot.swipe_left()
                continue

        print('distance:', profile_data['distance'])

        output = analyze_images(profile_data['id'])
        rating = output.split('###RATING###')[1].strip()
        profile_data['attractiveness_rating'] = rating
        profile_data['extracted_info'] = extract_info(output)
        profiles.append(profile_data)
        tinder_bot.save_profiles(profiles)

        try:
            rating = int(rating)
            if rating > 64:
                tinder_bot.swipe_right()
            else:
                tinder_bot.swipe_left()
        except:
            print('error converting rating to int')
            tinder_bot.swipe_left()

        
finally:
    tinder_bot.cleanup()