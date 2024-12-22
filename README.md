# tinder-bot-local

## Setup

1. Install requirements.txt

```
pip install -r requirements.txt
``` 
2. Add your facebook credentials and an OpenAI API key to the .env file

3. Create an images directory in the current directory. Also ideally create a popups directory, and a profiles.json file.

4. Run the bot

```
python bot.py
```

5. During the first run, you might need to approve the facebopok login on your phone. Cookies should be saved for future runs.

--> Then play around with the system prompt in bot.py and the swipe threshold to see what works best for you.

## Notes

- The bot will run in browser mode by default, but you can set `headless=True` in the TinderAutomation class to run in headless mode.
- The bot will run in the current directory, so make sure you have a user-data directory with the appropriate permissions.
- The bot will use the default geolocation of London, UK. You can change this to your desired location by setting the `geolocation` parameter in the TinderAutomation class.
