from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import uuid

class TinderAutomation:
    def __init__(self):
        self.profiles_file = "profiles.json"
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir="./user-data",
            geolocation={"latitude": 51.5074, "longitude": -0.1278},  # London
            permissions=["geolocation"],
            headless=False # debugging mode
        )
        self.page = self.context.new_page()

    def cleanup(self):
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()

    def open_tinder(self, email, password):
        # Navigate to Tinder
        self.page.goto("https://tinder.com")

        # Handle cookies if present
        try:
            cookies_decline_button = self.page.wait_for_selector('//div[contains(text(), "I decline")]', timeout=2000)
            cookies_decline_button.click()
            print("Declined cookies")
        except:
            print("No cookies button found")

        # Click on the Log In button
        try:
            login_button = self.page.wait_for_selector('//div[contains(text(), "Log in")]', timeout=2000)
            login_button.click()
            print("Clicked login button")
            # Handle Facebook login
            self.facebook_login(email, password)
        except:
            print("No element found for login")

        # Switch back to the main Tinder window
        self.page.bring_to_front()

        # Handle potential popups
        try:
            allow_location_button_again = self.page.wait_for_selector('[aria-label="Allow"]', timeout=2000)
            allow_location_button_again.click()
            print("Allowed location for Tinder")
        except:
            print("No location popup found")

        try:
            enable_button = self.page.wait_for_selector('//div[contains(text(), "Allow")]', timeout=2000)
            enable_button.click()
            print("Enabled location in browser")
        except:
            print("No enable popup found")

    def facebook_login(self, email, password):
        # Wait for and click on "Log in with Facebook"
        try:
            login_with_facebook = self.page.wait_for_selector('//div[contains(text(), "Login with Facebook")]', timeout=2000)
            login_with_facebook.click()
            print("Clicked Facebook login")
        except:
            print("No Facebook login button found")
            return

        # Switch to Facebook login popup
        fb_popup_page = self.context.wait_for_event("page")
        fb_popup_page.bring_to_front()

        # Handle cookies if present
        try:
            cookies_decline_button = fb_popup_page.wait_for_selector('[aria-label="Decline optional cookies"]', timeout=2000)
            cookies_decline_button.click()
            print("Declined fb cookies")
        except:
            print("No cookies button found")

        # Fill in Facebook login credentials
        try:
            fb_popup_page.fill('input[name="email"]', email, timeout=2000)
            print("Filled in email")
            fb_popup_page.fill('input[name="pass"]', password, timeout=2000)
            print("Filled in password")
            fb_popup_page.click('input[name="login"]', timeout=2000)
            print("Clicked login")
        except:
            print("Failed to log in to Facebook")

        
        
        try:
            continue_button = fb_popup_page.wait_for_selector('div[aria-label^="Continue as"]', timeout=2000)
            continue_button.click()
            print("Continued as User")
        except:
            print("No continue option")
            try:
                twofactor = fb_popup_page.wait_for_selector('//div[.//text()[contains(., "Check your notifications")]]', timeout=10000)
                print("Closed Facebook popup page")
                if twofactor:
                    print("Authorise on phone - you have ~30 seconds to do this.")
                    try:
                        self.page.wait_for_timeout(20000)
                        # Switch back to the main Tinder window
                        print("Switching back to Tinder window")
                        self.page.bring_to_front()
                        print("Retrying login with Facebook")
                        self.facebook_login(email, password)
                    except:
                        print("Still can't login with facebook")
                        raise Exception("Failed to login with Facebook after retry")
            except:
                print("No twofactor popup found")


        

    def scrape_profile(self):
        """Scrape profile data from the current page."""
        profile_data = {}

        # Extract name and age
        try:
            name_element = self.page.wait_for_selector('h1[aria-label*="years"] span:first-child', timeout=1000).inner_text()
            age_element = self.page.wait_for_selector('h1[aria-label*="years"] span:last-child', timeout=1000).inner_text()
            profile_data['name'] = name_element
            profile_data['age'] = age_element
        except:
            profile_data['name'] = None
            profile_data['age'] = None

        # Extract text using the unique C($c-ds-text-secondary) class
        try:
            text_content = self.page.locator('section.C\\(\\$c-ds-text-secondary\\)').inner_text()
            profile_data['bio'] = text_content
        except:
            profile_data['bio'] = None

        # Extract distance
        try:
            print('finding distance...')
            distance_text = self.page.wait_for_selector('//div[contains(text(), "mile")]', timeout=2000).text_content()
            print('distance_text: ', distance_text)
            distance = distance_text.split(' ')[0]
            profile_data['distance'] = distance
        except:
            profile_data['distance'] = None

        # Extract passions
        try:
            passions = self.page.locator('section:has(h2:has-text("Passions")) li').all_inner_texts()
            profile_data['passions'] = passions
        except:
            profile_data['passions'] = []

        # Extract lifestyle
        try:
            lifestyle_section = self.page.locator('div:has(h2:has-text("Lifestyle")) div[role="checkbox"]')
            lifestyle_items = {}
            elements = lifestyle_section.element_handles()
            for element in elements:
                category = element.query_selector('span.Hidden').inner_text()
                value = element.inner_text().replace(category, '').strip()  # Remove category name to get the value
                lifestyle_items[category] = value
            profile_data['lifestyle'] = lifestyle_items
        except Exception as e:
            print(f"Failed to extract lifestyle data: {str(e)}")
            profile_data['lifestyle'] = []

        return profile_data
    
    def extract_images(self, id):
        """Extract images from the current profile."""
        # Clear any popups before starting
        self.clear_popups()
        
        # slides_count = len(self.page.locator('div.profileCard__slider div.keen-slider__slide').all())
        # print(f'Found {slides_count} slides')
        slides_count = 3 # fixed number of images initially.
        
        for i in range(slides_count):
            print(f'screenshotting slide {i+1}...')
            self.page.wait_for_timeout(500)
            
            # Clear any popups before taking screenshot - very slow!!! WE DON'T HAVE A WAY OF CHECKING FOR A POPUP OTHER THAN A FAILED ACTION.
            # self.clear_popups()
            
            # Take screenshot of the currently visible slide
            visible_slides = self.page.locator('div.keen-slider__slide[aria-hidden="false"]').all()
            if visible_slides:
                visible_slides[0].screenshot(path=f"./images/{id}_{i+1}.png")
            
            # Press space and check if the image changed
            self.page.keyboard.press('Space')
            self.page.wait_for_timeout(1000)
        
    def save_profiles(self, new_profiles):
        """Save profile data to a JSON file."""
        print('saving profiles...')
        try:
            # Load existing profiles
            profiles = []
            try:
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
            except FileNotFoundError:
                pass  # File doesn't exist yet

            # Append new profile
            profiles += new_profiles

            # Save back to file
            with open(self.profiles_file, 'w') as f:
                json.dump(profiles, f, indent=2)
                print(f"Saved profiles to {self.profiles_file}")
            
        except Exception as e:
            print(f"Failed to save profile: {str(e)}")

    def view_profile(self):
        """View a profile and scrape its data."""
        profile_data = {
            'timestamp': datetime.now().isoformat(),
            'id': str(uuid.uuid4())
        }

        # Clear any existing popups before expanding
        # self.clear_popups()
        
        if self.expand():
            print("Expanded profile")
        else:
            print("Failed to expand profile")

        # Clear any popups that might have appeared after expanding
        # self.clear_popups()
        
        # Update profile_data with scraped information
        profile_data.update(self.scrape_profile())
        self.extract_images(profile_data['id'])
        
        print(f"Scraped profile for {profile_data['name']}")
        return profile_data

    """
    def is_popup_present(self):
        # Check if there's currently a popup visible on the screen.
        # Common popup indicators
        popup_indicators = [
            "div[role='dialog']",  # Most Tinder popups are dialogs
            "div.modal-overlay",   # Common modal overlay class
            "//div[contains(@style, 'z-index: 9999')]",  # High z-index elements are often popups
            "//div[contains(text(), 'Subscribe') or contains(text(), 'Premium') or contains(text(), 'Upgrade')]",  # Common popup text
            "//div[contains(@class, 'Pos(f)')]"  # Fixed position elements (often overlays)
        ]
        
        for indicator in popup_indicators:
            try:
                element = self.page.wait_for_selector(indicator, timeout=1000)
                if element and element.is_visible():
                    print(f"Detected popup with selector: {indicator}")
                    return True
            except:
                continue
        return False
    """

    def handle_popup(self):
        """Handle any popup by taking a screenshot and determining the action needed."""
        try:
            try:
                # Take screenshot of the current page
                screenshot_path = f"./popups/popup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.page.screenshot(path=screenshot_path)
            except:
                print("Failed to take screenshot of the current page")
            
            # Common popup handling patterns
            popup_actions = [
                {
                    "selector": "//div[contains(text(), 'Allow')]",
                    "action": "click"
                },
                {
                    "selector": "//div[contains(text(), 'Not interested')]",
                    "action": "click"
                },
                {
                    "selector": "//div[contains(text(), 'Maybe later')]",
                    "action": "click"
                },
                {
                    "selector": "//div[contains(text(), 'No thanks')]",
                    "action": "click"
                },
                {
                    "selector": "//div[contains(text(), 'Got it')]",
                    "action": "click"
                },
                {
                    "selector": "//div[contains(text(), 'Dismiss')]",
                    "action": "click"
                },
                # Sometimes we need to click outside the popup to dismiss it
                {
                    "selector": "div.modal-overlay",
                    "action": "click"
                },
                # Escape key can dismiss some popups
                {
                    "selector": "div[role='dialog']",
                    "action": "escape"
                }
            ]
            
            for pattern in popup_actions:
                try:
                    element = self.page.wait_for_selector(pattern["selector"], timeout=2000)
                    if element and element.is_visible():
                        if pattern["action"] == "click":
                            element.click()
                        elif pattern["action"] == "escape":
                            self.page.keyboard.press('Escape')
                        print(f"Handled popup: {pattern['action']} on {pattern['selector']}")
                        self.page.wait_for_timeout(1000)  # Wait for popup animation
                        
                        # Verify popup was dismissed
                        if not element.is_visible():
                            return True
                except:
                    continue
            
            return False  # No popup was handled
            
        except Exception as e:
            print(f"Error handling popup: {str(e)}")
            return False

    def clear_popups(self):
        """Attempt to clear all popups before performing actions."""
        # need to work on this.
        self.handle_popup()
        self.page.wait_for_timeout(500)  # Wait between attempts

    def perform_action_with_popup_check(self, action_func, max_retries=3):
        """Wrapper to perform an action with popup handling."""
        retries = 0
        while retries < max_retries:
            try:
                action_func()
                return True
            except Exception as e:
                print(f"Action failed: {str(e)}")
                if self.handle_popup():
                    print("Popup handled, retrying action...")
                    retries += 1
                    continue
                else:
                    print("No popup found, action failed")
                    return False
        return False

    def swipe_right(self):
        """Swipe right on the current profile."""
        def action():
            print('swiping right...')
            self.page.keyboard.press('ArrowRight')
            self.page.wait_for_timeout(1000)
        return self.perform_action_with_popup_check(action)

    def swipe_left(self):
        """Swipe left on the current profile."""
        def action():
            print('swiping left...')
            self.page.keyboard.press('ArrowLeft')
            self.page.wait_for_timeout(1000)
        return self.perform_action_with_popup_check(action)

    def expand(self):
        """Expand the current profile."""
        def action():
            self.page.keyboard.press('ArrowUp')
            self.page.wait_for_timeout(1000)
        return self.perform_action_with_popup_check(action)