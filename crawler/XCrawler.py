from bs4 import BeautifulSoup
from selenium import webdriver
import time
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import re
import os
import shutil
import random
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from datetime import datetime
from exceptions.exceptions import WrongDateString, NoTweetsReturned, ElementNotLoaded
import json
import csv

# Regex to match the image link
ACTUAL_IMAGE_PATTERN = '^https:\/\/pbs\.twimg\.com\/media.*'

# Regex to match date in 'until' and 'since' parameters. Notice that it does NOT check the validity of the date according to the month (e.g., one could declare) 2023-02-31.
DATE_SINCE_UNTIL = r'^(?!0000)[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$'

# Vertical size of the scroll. This is used to scroll down the page
Y = 500

# Regex to match the video preview link
ACTUAL_VIDEO_PREVIEW_PATTERN = '^https:\/\/pbs\.twimg\.com\/ext_tw_video_thumb.*'

# Target url to be scraped
TARGET_URL = 'https://www.twitter.com/login'

class XCrawler:
    def __init__(self, username: str, password: str, query: str, email_address: str, wait_scroll_base: int = 15, wait_scroll_epsilon :float = 5, num_scrolls: int = 10, mode: int = 0, since_id: int = -1, max_id: int = -1, since: str = 'none', until: str = 'none', since_time: str = 'none', until_time: str = 'none', headless: bool = False, chromedriver='none', root: bool=False):
        """Class initializator

        Args:
            username (str): Username that will be used to access the Twitter account
            password (str): Password of the Username that will be used access the Twitter account
            query (str): Query to be searched on Twitter
            email_address (str): Email address of the account. Will be used in case twitter asks to enter the mail for confirmation purposes.
            wait_scroll_base (int): base time to wait between one scroll and the subsequent (expressed in number of seconds, default 15)
            wait_scroll_epsilon (float): random time to be added to the base time to wait between one scroll and the subsequent, in order to avoid being detected as a bot (expressed in number of seconds, default 5)
            num_scrolls (int): number of scrolls to be performed, default 10
            mode (int): Mode of operation: 0 (default) to retrieve just images and video preview, 1 to retrieve also information about tweets
            since_id (int): id of the tweet to start the search from (default = -1 means not set. Notice that need to be defined also max_id). If one between since or until is set, since_id and max_id will not be considered
            max_id (int): id of the tweet to end the search to (default = -1 means not set. Notice that need to be defined also since_id). If one between since or until is set, since_id and max_id will not be considered
            since (str): String of the date (excluded) from which the tweets will be returned. Format: YYYY-MM-DD, UTC time. Temporarily supported only for mode 1. If you set also since_time, or until_time, this will be ignored
            until (str): String of the date (included) until which the tweets will be returned. Format: YYYY-MM-DD, UTC time. Temporarily supported only for mode 1. If you set also since_time, or until_time, this will be ignored
            since_time (str): String of the time from which the tweets will be returned. Format: timestamp in SECONDS, UTC time. Temporarily supported only for mode 1
            until_time (str): String of the time until which the tweets will be returned. Format: timestamp in SECONDS, UTC time. Temporarily supported only for mode 1
        """
        
        # Parameters initialization
        self.username = username
        self.password = password
        self.wait_scroll_base = wait_scroll_base
        self.wait_scroll_epsilon = wait_scroll_epsilon
        self.num_scrolls = num_scrolls
        self.query = query
        self.mode = mode
        self.since_id = since_id
        self.max_id = max_id
        self.until = until
        self.since = since
        self.since_time = since_time
        self.until_time = until_time
        self.email_address = email_address

        try:
            self.check_date()
        except WrongDateString as e:
            print(f'{e}')
            print('           Ignoring since and until parameters since one among them was set wrong')
            self.since = 'none'
            self.until = 'none'
            print(f'           Setting them back to default values to ignore them: since = {self.since}, until = {self.until}')

        # Initialization of the lists of links and of tweets
        self.actual_images = []
        self.video_preview = []
        self.tweets = {}

        # Initialization of the chromedriver
        self.chrome_options = Options()
        self.chrome_options.add_experimental_option("detach", True)
        if headless:
            self.chrome_options.headless = True
            self.chrome_options.add_argument("--window-size=1920,1080")
            self.chrome_options.add_argument("--enable-javascript")
        if root:
            # If you try to run chromium as root, an error is shown displayng that reuquires --no-sandbox option to be set
            self.chrome_options.add_argument("--no-sandbox")
            print('Running in root mode. This is not recommended for security reasons, disabling sandbox to allow run chromium.')
        
        if chromedriver != 'none':
            self.driver = webdriver.Chrome(executable_path=chromedriver, chrome_options=self.chrome_options)
        else:
            self.driver=webdriver.Chrome(service=Service(), options=self.chrome_options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 30)
        self.driver.get(TARGET_URL)

    ###### Utility methods ######
    def go_home(self):
        print('Going to the homepage.')
        self.driver.get('https://twitter.com/home')
        print('Returned to the homepage.')

    def login(self):
        print('Logging in')
        # Input username
        try:
            username_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "text")))
        except TimeoutException:
            raise ElementNotLoaded('Username input not loaded')
        
        time.sleep(0.7)
        for character in self.username:
            username_input.send_keys(character)
            time.sleep(0.3) # pause for 0.3 seconds
        # username_input.send_keys('send username here') -> can also be used, but hey ... my robot is a human
        try:
            button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[6]/div")))
        except TimeoutException:
            raise ElementNotLoaded('Button to be pressed after the username input not loaded')
        
        time.sleep(1)
        button.click()

        # Input password
        try:
            password_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "password")))
        except TimeoutException:
            raise ElementNotLoaded('Password input not loaded')
        
        time.sleep(0.7)
        for character in self.password:
            password_input.send_keys(character)
            time.sleep(0.3) # pause for 0.3 seconds

        try:
            button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/div/div")))
        except TimeoutException:
            raise ElementNotLoaded('Button to be pressed after the password input not loaded')
        time.sleep(1)

        button.click()

        print('Logged in successfully')

    def search(self):
        # Query input
        print('From now on, it may take a while, according to parameters.')
        try:
            searchbox = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@aria-label='Search query']")))
        except TimeoutException:

            # Could be that twitter is asking to enter the mail address:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            if 'Verify your identity by entering the email address' in soup.get_text():

                print('twitter is asking to verify the identity by entering the email address')
                try:
                    email_confirmation_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "text")))
                except TimeoutException:
                    raise ElementNotLoaded('Email Confirmation input not loaded')
                print('Email Confirmation input loaded, starting input email.')
                for character in self.email_address:
                    email_confirmation_input.send_keys(character)
                    time.sleep(0.3)
                try:
                    button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div/div/div/div")))
                except TimeoutException:
                    raise ElementNotLoaded('Trying to bypass email confirmation, but button \'next\' did not load')
                button.click()

                searchbox = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@aria-label='Search query']")))
            else:
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                filename = 'postget_error_soupfile.txt'
                cwd = os.getcwd()
                file_path = os.path.join(cwd, filename)

                with open(file_path, 'w') as f:
                    f.write(soup.prettify())
                raise ElementNotLoaded(f'Searchbox not loaded in time. Check {file_path} for more details.')
        # //TODO: clear query, the second query changes location to be opened

        time.sleep(0.7)
        searchbox.clear()
        
        self.input_query = self.query

        # Higher precedence: if one between since_time and until_time is set, since and until will be ignored. N.B.: it is correct to use always "since:" and "until:" in both cases!
        if self.since_time != 'none' or self.until_time != 'none':
            if self.since_time != 'none':
                self.input_query += f' since:{self.since_time}'
            if self.until_time != 'none':
                self.input_query += f' until:{self.until_time}'
        else:
            if self.since != 'none':
                self.input_query += f' since:{self.since}'
            if self.until != 'none':
                self.input_query += f' until:{self.until}'
        
        print(f'Starting to input \'{self.input_query}\' in the searchbox')
        for character in self.input_query:
            searchbox.send_keys(character)
            time.sleep(0.5)
        
        searchbox.send_keys(Keys.ENTER)
        time.sleep(1)
            
        pause_time = self.compute_scroll_pause_time()
        print(f'Search performed successfully, waiting first content to load. Waiting {pause_time} seconds')
        time.sleep(pause_time)
        
        if self.mode == 0:
            try:
                self.simplified_search()
            except NoTweetsReturned as e:
                raise e
        else:
            try:
                self.complete_search()
            except NoTweetsReturned as e:
                raise e

    def complete_search(self):
        print('Starting complete search')
        count = 0
        destination = 0

        if self.since_id != -1 and self.max_id != -1:
            print(f'since_id and max_id are set. since_id = {self.since_id}, max_id = {self.max_id}.')
        else:
            print(f'since_id and max_id are not set. since_id = {self.since_id}, max_id = {self.max_id}.')
        
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        if len(soup.find_all('div', {'data-testid':'cellInnerDiv'})) == 0:
                raise NoTweetsReturned(self.input_query)

        while True:
            count += 1
            print(f'Performing scroll {count} of {self.num_scrolls}')

            # Scroll down
            destination = destination + Y
            self.driver.execute_script(f"window.scrollTo(0, {destination})")

            # Wait for page to load
            pause_time = self.compute_scroll_pause_time()
            print(f'Hey wait ... This content seams interesting, I\'ll wait {pause_time} seconds')
            time.sleep(pause_time)
            
            # Update page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # find all tweets (div with data-testid="tweet")
            self.raw_tweets = soup.find_all('div', {'data-testid':'cellInnerDiv'})

            for raw_tweet in self.raw_tweets:
                # get the <a>...</a> tag containing the string about the id of the discussion (composed of: <username>/status/<id>)
                username_tweet_id = raw_tweet.find('a', {'class':"css-4rbku5 css-18t94o4 css-901oao r-1bwzh9t r-1loqt21 r-xoduu5 r-1q142lx r-1w6e6rj r-37j5jr r-a023e6 r-16dba41 r-9aw3ui r-rjixqe r-bcqeeo r-3s2u2q r-qvutc0"})
                
                # checking if it is an actual tweet, or an empty div at the end of the tweets

                if type(username_tweet_id) != type(None):
                    # checking if case since_id and max_id are set, it if not in the range [since_id, max_id]), and if advanced queries for times are not set, then we will search by ids.
                    if self.since_id != -1 and self.max_id != -1 and (self.since == 'none' and self.until == 'none') and (self.since_time == 'none' and self.until_time == 'none'):
                        
                        # If the tweet is in the range [since_id, max_id]
                        if int(username_tweet_id['href'].split('/')[3]) >= self.since_id and int(username_tweet_id['href'].split('/')[3]) <= self.max_id:
                            # using the discussion id as key of the dictionary, and checking if not already analyzed
                            if username_tweet_id['href'] not in self.tweets.keys():

                                # Retrieving username, tweet id, discussion link, and timestamp
                                iso_timestamp = username_tweet_id.find('time')['datetime']
                                dt = datetime.strptime(iso_timestamp,'%Y-%m-%dT%H:%M:%S.%fZ')
                                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                                discussion_link = f'https://twitter.com{username_tweet_id["href"]}'

                                # Retrieving tweet text
                                tweet_text = raw_tweet.find('div', {'data-testid': 'tweetText'})
                                # if tweet_text is not None. If tweet_text is None, output None
                                if tweet_text:
                                    tweet_text = tweet_text.get_text()

                                # append username, tweet id, tweet text, to the dictionary, and initializing the list of links to images and video preview
                                self.tweets[username_tweet_id['href']] = {"username": username_tweet_id['href'].split('/')[1], 
                                                                          "tweet_id": username_tweet_id['href'].split('/')[3], 
                                                                          "tweet_text": tweet_text, 
                                                                          "discussion_link": discussion_link, 
                                                                          "iso_8601_timestamp": iso_timestamp, 
                                                                          "datetime_timestamp": timestamp, 
                                                                          "images": [], 
                                                                          "video_preview": []}

                                # Retrieving images and video preview links
                                images = raw_tweet.find_all('img')
                                video_tags = raw_tweet.find_all('video')
                                for image in images:
                                    if re.match(ACTUAL_IMAGE_PATTERN, image['src']):
                                        self.tweets[username_tweet_id['href']]['images'].append(image['src'])
                                for video_tag in video_tags:
                                    if re.match(ACTUAL_VIDEO_PREVIEW_PATTERN, video_tag['poster']):
                                        self.tweets[username_tweet_id['href']]['video_preview'].append(video_tag['poster'])
                        else:
                            print(f'Tweet {username_tweet_id["href"].split("/")[3]} not in the range [{self.since_id}, {self.max_id}]. Skipping it')
                    else:
                        # In this case, since_id and max_id are not set, so we can analyze all the tweets
                        # using the discussion id as key of the dictionary, and checking if not already analyzed
                        if username_tweet_id['href'] not in self.tweets.keys():
                            
                            # Retrieving username, tweet id, discussion link, and timestamp
                            iso_timestamp = username_tweet_id.find('time')['datetime']
                            dt = datetime.strptime(iso_timestamp,'%Y-%m-%dT%H:%M:%S.%fZ')
                            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                            discussion_link = f'https://twitter.com{username_tweet_id["href"]}'

                            # Retrieving tweet text
                            tweet_text = raw_tweet.find('div', {'data-testid': 'tweetText'})
                            # if tweet_text is not None. If tweet_text is None, output None
                            if tweet_text:
                                tweet_text = tweet_text.get_text()

                            # append username, tweet id, tweet text, to the dictionary, and initializing the list of links to images and video preview
                            self.tweets[username_tweet_id['href']] = {"username": username_tweet_id['href'].split('/')[1], 
                                                                      "tweet_id": username_tweet_id['href'].split('/')[3], 
                                                                      "tweet_text": tweet_text, 
                                                                      "discussion_link": discussion_link, 
                                                                      "iso_8601_timestamp": iso_timestamp, 
                                                                      "datetime_timestamp": timestamp, 
                                                                      "images": [], 
                                                                      "video_preview": []}

                            # Retrieving images and video preview links
                            images = raw_tweet.find_all('img')
                            video_tags = raw_tweet.find_all('video')
                            for image in images:
                                if re.match(ACTUAL_IMAGE_PATTERN, image['src']):
                                    self.tweets[username_tweet_id['href']]['images'].append(image['src'])
                            for video_tag in video_tags:
                                if re.match(ACTUAL_VIDEO_PREVIEW_PATTERN, video_tag['poster']):
                                    self.tweets[username_tweet_id['href']]['video_preview'].append(video_tag['poster'])
            if count == self.num_scrolls:
                break
           
            
    def simplified_search(self):
        print('Starting simplified search')

        if self.since_id != -1 or self.max_id != -1:
            print('Simplified search does not support since_id and max_id parameters, since while browsing doesen\'t retrieve those information. Ignoring them.')

        count = 0
        destination = 0

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        if len(soup.find_all('div', {'data-testid':'cellInnerDiv'})) == 0:
                raise NoTweetsReturned(self.input_query)

        while True:
            count += 1
            print(f'Performing scroll {count} of {self.num_scrolls}')

            # Scroll down
            destination = destination + Y
            self.driver.execute_script(f"window.scrollTo(0, {destination})")

            # Wait to load page
            pause_time = self.compute_scroll_pause_time()
            print(f'Hey wait ... This content seams interesting, I\'ll wait {pause_time} seconds')
            time.sleep(pause_time)
        
            # Update vectors
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            images = soup.find_all("img")
            video_tags = soup.findAll('video')

            for image in images:
                if re.match(ACTUAL_IMAGE_PATTERN, image['src']) and image['src'] not in self.actual_images:
                    self.actual_images.append(image['src'])

            for video_tag in video_tags:
                if re.match(ACTUAL_VIDEO_PREVIEW_PATTERN, video_tag['poster']) and video_tag['poster'] not in self.video_preview:
                    self.video_preview.append(video_tag['poster'])
            if count == self.num_scrolls:
                break

    def compute_scroll_pause_time(self):
        lower_bound = round(self.wait_scroll_base - self.wait_scroll_epsilon, 2)  # round to 2 decimal places
        upper_bound = round(self.wait_scroll_base + self.wait_scroll_epsilon, 2)  # round to 2 decimal places

        return round(random.uniform(lower_bound, upper_bound), 2)  # round to 2 decimal places
    
    def clear_images(self):
        self.actual_images = []

    def clear_video_previews(self):
        self.video_preview = []

    def clear_tweets(self):
        self.tweets = {}

    def quit_browser(self):
        self.driver.quit()
    
    def print_results(self):
        if self.mode == 0:
            print('Hey hey ... here are the images:')
            for image in self.get_actual_images():
                print(f'           {image}')
            print('           and here the videos:')
            for video in self.get_video_preview():
                print(f'           {video}')
        else:
            print('Hey hey ... here are the tweets:')
            for tweet in self.tweets:
                print(f'           {self.tweets[tweet]}')
    
    def save_to_json(self):
        with open('twitter.json', 'a+', encoding="utf-8") as f:
            for tweet in self.tweets:
                json.dump(self.tweets[tweet], f, indent=1, ensure_ascii=False)
        print("json saved")
    
    ###### Checks ######
    def check_date(self):
        if(self.since != 'none'):
            if not re.match(DATE_SINCE_UNTIL, self.since):
                raise WrongDateString(self.since, 'YYYY-MM-DD')
        if(self.until != 'none'):
            if not re.match(DATE_SINCE_UNTIL, self.until):
                raise WrongDateString(self.until, 'YYYY-MM-DD')
    
    def save_to_csv(self, csv_file):
        json_file_path = 'twitter.json'

        # Read the existing JSON content as lines
        with open(json_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Add '[' at the beginning
        lines.insert(0, '[\n')

        # Join the lines with commas and newlines
        for i in range(len(lines)):
            if lines[i].strip() == '}{' and i > 0:
                lines[i] = '},\n{'

        # Add ']' at the end
        lines.append('\n]')

        # Write the corrected content back to the file
        with open(json_file_path, 'w', encoding='utf-8') as file:
            file.write(''.join(lines))

        # Read the JSON data from the file
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            json_data = json.load(json_file)

        # Get the header from the first JSON object
        header = json_data[0].keys()

        # Write the JSON data to the CSV file
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            
            # Write the header
            writer.writeheader()
            
            # Write the data
            writer.writerows(json_data)
            print("csv saved successfully")

