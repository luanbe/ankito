import json
import urllib.request
import requests
import traceback
import sys
import logging
from dotenv import dotenv_values

from logging.handlers import RotatingFileHandler
from .utils import check_and_create_file
from bs4 import BeautifulSoup
from googletrans import Translator
from functools import wraps



    
class AnkiInput:
    keyword = None
    image_allow = True
    config = dotenv_values('.env')
    add_note_action = 'addNote'
    find_note_action = 'findNotes'
    create_deck_action = 'createDeck'
    anki_api = 'http://' + config.get('ANKI_API_HOST') + ':' + config.get('ANKI_API_PORT')

    def __init__(self):
        self.logger = self.get_logger('Anki')
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }

    def __str__(self):
        print("The AnkiInput Class")

    def logit(func):
        @wraps(func)
        def wapper_logit(self, *args, **kwargs):
            # An action before run function
            self.logger.info(f'The {func.__name__} is starting....')
            func_ = func(self, *args, **kwargs)
            # An action after run fucntion
            self.logger.info(f'The {func.__name__} is done!')
            return func_
        return wapper_logit


    @logit
    def words_to_anki(self, keyword, deck_name, model_name, image_allow=True, ):
        """Send data to anki

        Returns:
            json: return a json result or None
        """
        self.image_allow = image_allow
        self.keyword = keyword
        self.deck_check_and_add(deck_name)
        # note_status = self.find_note(deck_name)

        # if not note_status:
        #     oxford = self.oxforddictionaries()
        #     full_vi = self.tracau_vn()
        #     if oxford and full_vi:
        #         # Convert random keyword to _
        #         # Example: table = __b__
        #         suggestion = ''
        #         import random
        #         i = 0
        #         rand_number = random.randrange(len(self.keyword[1:-1]))
        #         for w in self.keyword[1:-1]:
        #             if  rand_number == i:
        #                 suggestion += w
        #             else:
        #                 suggestion += '_'
        #             i += 1
                
        #         # Create a cloze for anki
        #         definition = oxford['definition']
        #         example = oxford['example']
        #         cloze = '{{c1::cloze}}'.replace('cloze', self.keyword)
        #         suggestion = f'_{suggestion}_'
        #         if example:
        #             explanation = f'{definition}<br/>→ {example}'.lower().replace(self.keyword, cloze)
        #         else:
        #             explanation = f'{definition}'.lower().replace(self.keyword, cloze)
                
        #         return self.invoke(self.add_note_action, note=self.note_template(
        #             deck_name,
        #             model_name,
        #             self.keyword,
        #             self.g_translate(),
        #             oxford['ipa'],
        #             suggestion,
        #             explanation,
        #             full_vi,
        #             oxford['audio'],
        #             self.image_search()
        #             ))
        # else:
        #     self.logger.info(f'Keyword: {self.keyword}| is existing in {deck_name} deck')
        #     return True

    def deck_check_and_add(self, deck_name):
        query = f'"deck:{deck_name}"'
        deck = self.invoke(self.find_note_action, query=query)
        if not deck:
            self.invoke(self.create_deck_action, deck=deck_name)

    def find_note(self, deck_name):
        query = f'"deck:{deck_name}" AND "Keyword:{self.keyword}"'
        return self.invoke(self.find_note_action, query=query)

    @logit
    def image_search(self):
        if self.image_allow:
            api_url = f'https://www.googleapis.com/customsearch/v1?key={self.config.get("GOOGLE_API_KEY")}&cx={self.config.get("GOOGLE_PROJECT_CX")}&searchType=image&fileType=jpg&imgSize=large&q={self.keyword}'
            response = self.session.get(api_url)
            try:
                return response.json()['items'][0]['link']
            except:
                if self.debug:
                    self.logger.error(traceback.format_exc())
                else:
                    self.logger.error('Have something errors...please allow debug = True to see more.')

    def invoke(self, action, **params):
        """An action for inserting data to anki by API
        Raises:
            Exception with len(response) != 2: response has an unexpected number of fields
            Exception 'error' not in response: response is missing required error field
            Exception 'result' not in response: response is missing required result field'
            Exception response['error'] is not None: error

        Returns:
            json: The result of requesting anki API
        """
        requestJson = json.dumps({'action': action, 'params': params, 'version': 6}).encode('utf-8')
        response = json.load(urllib.request.urlopen(urllib.request.Request(self.anki_api, requestJson)))
        if len(response) != 2:
            raise Exception('response has an unexpected number of fields')
        if 'error' not in response:
            raise Exception('response is missing required error field')
        if 'result' not in response:
            raise Exception('response is missing required result field')
        if response['error'] is not None:
            self.logger.error(f'Keyword: {self.keyword}| ' +response['error'])
        return response['result']

    @logit
    def tracau_vn(self):
        """tracau.vn scraping. Crawl full vocabulary from EN to VN

        Returns:
            str: Full HTML vocabulary
        """
        response = self.session.get(f'https://api.tracau.vn/WBBcwnwQpV89/s/{self.keyword}/en')
        # Get full vocabulary from tracau..vn
        try:
            text = response.json()['tratu'][0]['fields']['fulltext']
            soup = BeautifulSoup(text, 'lxml')
            definition = soup.select_one('#definition')
            if definition:
                tag_remove = soup.select_one('#definition tr#pa')
                if tag_remove:
                    tag_remove.decompose()
                return definition.prettify()
            else:
                return self.parse_laban()
        except:
            if self.debug:
                self.logger.error(traceback.format_exc())
            else:
                self.logger.error('Have something errors...please allow debug = True to see more.')

    @logit
    def g_translate(self):
        """Translate a word or sentence from EN to VN
        Args:
            keyword (str): The word EN to translate

        Returns:
            str: The result of translator
        """
        translator = Translator()
        return translator.translate(self.keyword, src='en', dest='vi').text

    @logit
    def oxforddictionaries(self):
        """Oxforddictionaries.com API request for crawling data.
        Returns:
            dict: The list data with keywords
            [audio], [ipa], [definition], [example]
        """
        app_id = "c24bf9db"
        app_key = "62594cb7887034bc8f91ae989d74103d"
        language = "en-us"
        word_id = self.keyword
        url = "https://od-api.oxforddictionaries.com:443/api/v2/entries/" + language + "/" + word_id.lower()
        r = self.session.get(url, headers={"app_id": app_id, "app_key": app_key})
        try:
            audio = r.json()['results'][0]['lexicalEntries'][0]['entries'][0]['pronunciations'][1]['audioFile']
            ipa = r.json()['results'][0]['lexicalEntries'][0]['entries'][0]['pronunciations'][1]['phoneticSpelling']
            ipa = f'/{ipa}/'
            definition = r.json()['results'][0]['lexicalEntries'][0]['entries'][0]['senses'][0]['shortDefinitions'][0]
            try:
                example = r.json()['results'][0]['lexicalEntries'][0]['entries'][0]['senses'][0]['examples'][0]['text']
            except:
                example = self.parse_yourdictionary()
            return {'audio': audio, 'ipa': ipa, 'definition': definition, 'example': example}
        except:
            if self.debug:
                self.logger.error(traceback.format_exc())
            else:
                self.logger.error('Have something errors...please allow debug = True to see more.')

    @logit
    def parse_yourdictionary(self):
        """Crawling examples on sentence.yourdictionary.com

        Returns:
            [str]: return a example
        """
        response = self.session.get(f'https://sentence.yourdictionary.com/{self.keyword}')
        soup = BeautifulSoup(response.text, 'lxml')
        example_el = soup.select_one('.sentences-list .sentence-item__text')
        
        return example_el.text if example_el else None

    @logit
    def parse_laban(self):
        """Crawling vocabulary from laban.vn

        Returns:
            [str]: full vocabulary
        """
        response = self.session.get(f'https://dict.laban.vn/find?type=1&query={self.keyword}')
        soup = BeautifulSoup(response.text, 'lxml')
        content = soup.select_one('li.slide_content div#content_selectable')
        if content:
            for a in content.find_all('a'):
                a['href'] = ""
            return content.prettify()
        

    def note_template(self, deck_name, model_name, keyword, keyword_translate, transcription, suggestion, explanation, full_vi, sound_url, picture_url=None):
        """The note template insert to Anki

        Args:
            deck_name (str): The desk name of your Anki
            model_name (str): The model name of your Anki
            keyword (str): The word's en  of your Anki
            keyword_translate (str): The word's vi translate of your Anki
            transcription (str): International Phonetic Alphabet chart for English dialects
            full_vi (str): Vietnam dictionary
            sound_url (str): Sound for English
            picture_url (str, optional): The picture describe your word. Defaults to None.

        Returns:
            dict: The note list template
        """
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {
                "Keyword": keyword,
                "Suggestion": suggestion, # "a__ __ __ __d"
                "Short Vietnamese": keyword_translate,
                "Transcription": transcription,
                "Explanation": explanation, # "When someone is {{c1::afraid}}, they feel fear.\n \→  The woman was {{c1::afraid}} of what she saw."
                "Full Vietnamese": full_vi
            },
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": "Default",
                    "checkChildren": False
                }
            },
            "tags": [
                "auto_import"
            ],
            "audio": [{
                "url": sound_url,
                "filename": f"{keyword}.mp3",
                "fields": [
                    "Keyword_Sound"
                ]
            }],
            
        }
        if picture_url and self.image_allow:
            note.update({
                "picture": [{
                    "url": picture_url,
                    "filename": f"{keyword}.jpg",
                    "fields": [
                        "Image"
                    ]
                }]
            })

        return note

    def get_logger(self, logger_name, log_handler=None):
        """
        Handles the creation and retrieval of loggers to avoid
        re-instantiation.
        """
        # initialize and setup logging system for the InstaPy object
        logger = logging.getLogger(logger_name)
        if (logger.hasHandlers()):
            logger.handlers.clear()

        logger.setLevel(logging.DEBUG)
        # log name and format
        general_log = f"logs/{logger_name}.log"
        check_and_create_file(general_log)

        file_handler = logging.FileHandler(general_log)
        # log rotation, 5 logs with 10MB size each one
        file_handler = RotatingFileHandler(
            general_log, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        extra = {"App": logger_name}
        logger_formatter = logging.Formatter(
            "%(levelname)s [%(asctime)s] [%(App)s]  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(logger_formatter)
        logger.addHandler(file_handler)
        # otherwise root logger prints things again
        logger.propagate = False
        # add custom user handler if given
        if log_handler:
            logger.addHandler(log_handler)

        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logger_formatter)
        logger.addHandler(console_handler)

        logger = logging.LoggerAdapter(logger, extra)
        return logger
    






