import random
import time
import pickle
import os
import errno
import json

from sys import exit as clean_exit
from contextlib import contextmanager
from bs4 import BeautifulSoup

@contextmanager
def smart_run(session):
    try:
        session.session_load()
        yield
    except KeyboardInterrupt:
        clean_exit("You have exited successfully.")
    finally:
        session.session_quit()

def random_sleep(random_time, logger=None):
    action_time = random.randint(random_time[0], random_time[1])
    if logger:
        logger.info(f'Sleep in ({action_time}) second....')
    time.sleep(action_time)
    return action_time

def load_cookie(browser, url, spider_name, logger):
    cookie_file_path = f'assets/cookies/{spider_name}.pkl'
    try:
        logger.info(f'Loading cookie file {cookie_file_path}')
        cookies = pickle.load(open(cookie_file_path, "rb"))
        browser.delete_all_cookies()

        # have to be on a page before you can add any cookies, any page - does not matter which
        browser.get(url)
        
        for cookie in cookies:
            if isinstance(cookie.get('expiry'), float): #Checks if the instance expiry a float 
                cookie['expiry'] = int(cookie['expiry']) # it converts expiry cookie to a int 
            browser.add_cookie(cookie)
        time.sleep(10)
        browser.refresh()
        return True
    except IOError:
        logger.info(f'Not find cookie file at {cookie_file_path}')
        return False

def save_cookie(browser, spider_name, logger):
    cookie_file_path = f'assets/cookies/{spider_name}.pkl'
    pickle.dump(browser.get_cookies() , open(cookie_file_path,"wb"))
    logger.info(f'Saved cookie file at {cookie_file_path}')
    time.sleep(10)

def check_and_create_file(file_path):
    if not os.path.exists(os.path.dirname(file_path)):
        try:
            os.makedirs(os.path.dirname(file_path))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    if os.path.isfile(file_path) is not True:
        f = open(file_path, "w")

def check_and_create_folder(path):
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    
def save_excel(df, file_path, logger=None, message=None):
    df.to_excel(file_path, engine='openpyxl', index=False)
    if message and logger:
        logger.info(message)

def load_json_file(file_path):
    try:
        with open(file_path) as rf:
            data = json.loads(rf.read())
        return data
    except:
        return False


def update_json_file(file_path, data):
    try:
        with open(file_path, 'w') as wf:
            json.dump(data, wf)
        return True
    except:
        return False

def random_user_agent():
    """
        The random User-Agent function from using random-user-agent package

        software_names: The name of web browser
        operating_systems: The name of Operation System
        user_agent_rotator : Create random User-Agent by choosing software_names, operating_systems and lmit 100 useragent
    """
    hardware_types = [HardwareType.COMPUTER.value, ]
    software_types = [SoftwareType.WEB_BROWSER.value]
    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value,
                      SoftwareName.OPERA.value, SoftwareName.SAFARI.value]
    operating_systems = [OperatingSystem.WINDOWS.value,
                         OperatingSystem.LINUX.value, OperatingSystem.MACOS.value]
    popularity = [Popularity.POPULAR.value]
    user_agent_rotator = UserAgent(hardware_types=hardware_types, software_types=software_types,
                                   software_names=software_names, operating_systems=operating_systems, popularity=popularity, limit=100)

    return user_agent_rotator.get_random_user_agent()

def convert_html_to_text(html_data):
    soup = BeautifulSoup(html_data.encode('ascii', errors='ignore').decode("utf-8"), 'lxml')
    return soup.text.strip()

def convert_html_to_json(html_data, browser):
    # Load json data from chrome driver
    content = browser.find_element_by_tag_name('pre').text

    # Load json data from firefox driver
    # content = browser.find_element_by_id('json').text
    return json.loads(content)

def remove_special_characters(text):
    if text:
        text.encode('ascii', errors='ignore').decode("utf-8")
        # Remove " character
        text = text.replace('"','')
    
    return text
