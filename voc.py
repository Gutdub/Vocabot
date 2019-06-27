"""
Blocked Ips:
Netherlands #256
"""
from sys import argv
from playsound import playsound  # works on linux, osx, and window
from whaaaaat import prompt, Separator
from argparse import ArgumentParser as Parser
from colorama import init as colorama_init, Fore, Style
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, ElementNotVisibleException, StaleElementReferenceException
from unidecode import unidecode
from collections import OrderedDict
from anytree import Node, LevelOrderIter
from anytree.render import ContRoundStyle, RenderTree
from anytree.search import find as find_node
from anytree.importer import DictImporter
from anytree.exporter import DictExporter
from pathlib import Path
from requests import get
from json import load, dump
from bs4 import BeautifulSoup
from random import sample, choice, shuffle, randint
from linecache import getline
from time import time
from difflib import SequenceMatcher


def initialize():
    print("Creating directories...")
    Path("Vocabot").mkdir(exist_ok=True, parents=True)
    (Path("Vocabot") / "dictionaries").mkdir(exist_ok=True, parents=True)
    (Path("Vocabot") / "audio").mkdir(exist_ok=True, parents=True)
    print("Creating settings...")
    settings_create()
    print("Done.")
    print("Building vocabulary pool...")
    pool_build()
    print("Done.")
    print("Creating history...")
    dictionary_create("History", "Search history. Words will be looked up here first.")
    print("Done.")
    print("Finished.")


def confirm(message, default=False):
    question = [
        {
            'type': 'confirm',
            'name': 'answer',
            'message': message,
            'default': default
        }
    ]
    answer = prompt(question)["answer"]
    return answer


def replace_all(string, substrings):
    for substring in substrings.items():
        string = string.replace(substring[0], substring[1])
    return string


def print_freq(word_str, freq):
    if freq != 0.0:
        return word_str.title() + ": once every " + str(int(-(-4000 / freq // 1))) + " pages"
    else:
        return word_str.title() + ": extremely rare"


def print_part_of_speech(title):
    if title == "adjective" or title == "adverb":
        return "an " + title
    elif title == "noun" or title == "verb":
        return "a " + title


def print_meaning(title):
    if title == "verb":
        return "means to"
    else:
        return "means"


def process_path(path):
    if path is not None:
        return (Path("Vocabot") / "dictionaries" / path_grammar(str(path))).with_suffix(".json")
    else:
        path = settings_check("default_dictionary")
        if path is None:
            path_error()
        else:
            return (Path("Vocabot") / "dictionaries" / path_grammar(str(path))).with_suffix(".json")


def path_grammar(path):
    return replace_all(path, {'\"': '\'', ">": "", "<": "", "|": "", "?": "", "*": "", ":": "", "/": ""})


def description_grammar(description):
    return unidecode(description).replace('\"', '\'')


def path_error():
    print(Fore.RED + "Invalid dictionary path." + Style.RESET_ALL)


def settings_configure():
    def print_value(value):
        if value is False:
            return "False"
        elif value is True:
            return "True"
        elif value is None:
            return "None"
        else:
            return str(value)

    def int_input(current):
        question = [
            {
                'type': 'input',
                'name': 'value_list',
                'message': "Current value is " + print_value(current) + ".\nEnter new integer value, enter -1 for inf"
            }
        ]
        answer = int(prompt(question)["value_list"])
        if answer == -1:
            answer = float("inf")
        return answer

    def bool_input(current):
        answer = confirm("Current value is " + print_value(current) + ". Enter new boolean value")
        return answer

    with open(settings_path) as file:
        settings = load(file)
    question = [
        {
            'type': 'checkbox',
            'message': 'Select options',
            'name': 'key_list',
            'choices': [
                Separator('= Verbosity ='),
                {'name': 'Word verbosity'},
                {'name': 'Dictionary verbosity'},
                {'name': 'Word scraping verbosity'},
                Separator('= Other ='),
                {'name': 'Default dictionary: ' + print_value(settings["default_dictionary"])},
                {'name': 'History capacity: ' + print_value(settings["history_capacity"])}
            ],
        }
    ]
    verbosity_translator = {"Short definition": ("short", "bool"),
                            "Long definition": ("long", "bool"),
                            "Play audio": ("audio", "bool"),
                            "Part of speech": ("title", "bool"),
                            "Definition": ("definition", "bool"),
                            "Example sentence": ("example", "bool"),
                            "Antonym": ("antonyms", "int"),
                            "Synonym": ("synonyms", "int"),
                            "Type of": ("type of", "int"),
                            "Type": ("types", "int"),
                            "Example": ("examples", "int"),
                            "Word family length": ("family", "int"),
                            "Word frequency": ("freq", "bool"),
                            "Usage length": ("usage", "int")}
    translator = {"Word scraping verbosity": 0,
                  "Word verbosity": 1,
                  "Dictionary verbosity": 2}
    key_list = prompt(question)["key_list"]
    for key in key_list:
        key = key.split(":")[0]
        if key == "Default dictionary":
            choices = [{"name": str(path), "disabled": "search history" if path.name == "History.json" else ""}
                       for path in (Path("Vocabot") / "dictionaries").rglob("*.json")]
            question = [
                {
                    "type": "checkbox",
                    "message": "Select default dictionary",
                    "name": "default_dictionary",
                    "choices": choices,
                    "validate": lambda ans: True if len(ans) == 1 else False
                }
            ]
            settings["default_dictionary"] = str(Path(prompt(question)["default_dictionary"][0])
                                                 .relative_to(Path("Vocabot") / "dictionaries"))
            with open(settings_path, "w") as file:
                dump(settings, file, indent=4, ensure_ascii=False)
        elif key == "History capacity":
            print("Change history capacity")
            new_value = int_input(settings["history_capacity"])
            settings["history_capacity"] = new_value
            with open(settings_path, "w") as file:
                dump(settings, file, indent=4, ensure_ascii=False)
        else:
            print(key + ":")
            subkey = translator[key]
            verbosity_settings = settings_check(subkey)
            question = [
                {
                    'type': 'checkbox',
                    'message': 'Select options',
                    'name': 'key_list',
                    "choices": [{"name": verbosity_key + ": " +
                                print_value(verbosity_settings[verbosity_translator[verbosity_key][0]])}
                                for verbosity_key in verbosity_translator]
                }
            ]
            verbosity_key_list = prompt(question)["key_list"]
            for verbosity_key in verbosity_key_list:
                verbosity_key = verbosity_key[:verbosity_key.find(":")]
                key_name, key_type = verbosity_translator[verbosity_key]
                print(verbosity_key + ":")
                key_value = print_value(verbosity_settings[verbosity_translator[verbosity_key][0]])
                if key_type == "int":
                    new_value = int_input(key_value)
                elif key_type == "bool":
                    new_value = bool_input(key_value)
                settings["verbosity"][key_name][subkey] = new_value
                with open(settings_path, "w") as file:
                    dump(settings, file, indent=4, ensure_ascii=False)
    print("Saved.")


def settings_create():
    with open(settings_path, "w") as file:
        settings = {
            "verbosity": {
                "short": [True, True, True],
                "long": [True, True, False],
                "audio": [True, True, True],
                "title": [True, True, True],
                "definition": [True, True, True],
                "example": [float("inf"), 1, 1],
                "antonyms": [10, 5, 3],
                "synonyms": [10, 5, 3],
                "type of": [10, 3, 3],
                "types": [10, 3, 3],
                "examples": [10, 5, 3],
                "family": [10, 5, 3],
                "freq": [True, True, True],
                "usage": [12, 4, 4]
            },
            "default_dictionary": None,
            "history_capacity": 10
        }
        dump(settings, file, indent=4)


def settings_check(key):
    with open(settings_path) as file:
        settings = load(file)
        if type(key) == int:  # verbosity key
            return {subkey: settings["verbosity"][subkey][key] for subkey in settings["verbosity"]}
        else:
            return settings[key]


def pool_build():
    with get("https://www.vocabulary.com/lists/128536") as page:  # 5000 GRE Words 1
        soup = BeautifulSoup(page.content, features="lxml")
    indexes = soup.find_all("li", class_="entry", lang="en")
    words = []
    definitions = []
    for index in indexes:
        words.append(index["word"])
        definitions.append(index.find("div", class_="definition").text)
    with open(Path("Vocabot") / "words.txt", "w") as word_pool:
        word_pool.write(str(len(words)) + "\n")
        for word in words:
            word_pool.write(word + "\n")
    with open(Path("Vocabot") / "definitions.txt", "w") as definition_pool:
        definition_pool.write(str(len(definitions)) + "\n")
        for definition in definitions:
            definition_pool.write(definition + "\n")


def pool_request(name, correct_choice):
    choices = []
    path = str((Path("Vocabot") / name).with_suffix(".txt"))
    with open(path, "r") as pool:
        length = int(pool.readline())
    line_numbers = sample(range(1, length), 3)  # linecache is 0-based
    for line_number in line_numbers:
        choices.append(getline(path, line_number).strip("\n"))
    correct_choice_index = randint(0, 3)
    choices.insert(correct_choice_index, correct_choice)
    return choices, correct_choice


def word_vocabot(word_strs):
    verbosity = settings_check(1)
    word_strs = word_strs.split(",")
    for word_str in range(len(word_strs)):
        print(Fore.LIGHTWHITE_EX + ">> " + word_strs[word_str] + Style.RESET_ALL)
        word = word_request(word_strs[word_str])
        word_strs[word_str] = list(word.keys())[0]
        word_print(word_strs[word_str], word[word_strs[word_str]], verbosity)
        word_create(word, None)
        print("\n\n\n")


def word_create(word, path):
    path = process_path(path)
    dictionary = dictionary_request(path)
    if path.name == "History.json":
        capacity = settings_check("history_capacity")
        if capacity != float("Inf"):
            for i in range(0, len(dictionary["contents"]) - capacity + 1):
                dictionary["contents"].popitem(last=False)
    dictionary["contents"].update(word)
    with open(path, "w") as file:
        dump(dictionary, file, indent=4, ensure_ascii=False)


def word_remove(word_strs, path):
    path = process_path(path)
    dictionary = dictionary_request(path)
    if dictionary is not None:
        for word_str in word_strs.split(","):
            if word_str in dictionary["contents"]:
                del dictionary["contents"][word_str]
            else:
                print(Fore.RED + "Invalid word." + Style.RESET_ALL)
        with open(path, "w") as file:
            dump(dictionary, file, indent=4, ensure_ascii=False)


def word_scrape(word):
    verbosity = settings_check(0)

    # request
    words = [word.split(" ")]
    for caps in range(len(words[0]) - 1):
        words.append(words[caps][:caps] + [words[caps][caps].title()] + words[caps][caps + 1:])
    url_base = "https://www.vocabulary.com/dictionary/"
    while True:
        url = url_base + "%20".join(words.pop(0))
        with get(url) as page:
            soup = BeautifulSoup(page.content, features="lxml")
        if soup is not None or words == []:
            break

    # word string
    save_word = soup.find("h1", class_="dynamictext")
    if save_word is None:
        print(Fore.RED + "The word is unavailable." + Style.RESET_ALL)
        return
    else:
        save_word = save_word.text

    # audio
    # how to scrape audio
    # audio extended url:
    # can be found easily by inspecting the element that contains the audio
    # audio database url:
    # 1.open the network tab in the browser, here you can see all the files your computer has received
    # 2.click the audio button, some new files will appear in the network tab
    # 3.find the audio file among those new files, on the right tab you can see its request url
    # find the pattern by yourself!
    if verbosity["audio"]:
        audio_url = "https://audio.vocab.com/1.0/us/" + soup.find("a", class_="audio")["data-audio"] + ".mp3"
        audio = get(audio_url).content
        with open((Path("Vocabot") / "audio" / save_word).with_suffix(".mp3"), 'wb') as file:
            file.write(audio)

    soup = soup.find("div", class_="definitionsContainer")
    # main text
    if verbosity["short"]:
        short_text = soup.find("p", class_="short")
        if short_text is not None:
            short_text = description_grammar(short_text.text)
    else:
        short_text = None
    if verbosity["long"]:
        long_text = soup.find("p", class_="long")
        if long_text is not None and verbosity["long"]:
            long_text = description_grammar(long_text.text)
    else:
        long_text = None

    # create definitions
    ordinals = []
    meanings = []
    for group in soup.find_all("div", class_="group"):
        ordinals.append(0)
        for ordinal in group.find_all("div", class_="ordinal"):  # this will also catch "ordinal first"
            meaning = {"example": [], "synonyms": {}, "antonyms": {}, "type of": {}, "types": {}, "examples": {}}
            # title and definition
            definition = ordinal.find("h3", class_="definition")
            if verbosity["title"]:
                meaning["title"] = description_grammar(definition.a["title"])
            if verbosity["definition"]:
                meaning["definition"] = description_grammar(definition.contents[-1].strip())
            # example and instances
            for instance in filter(lambda value: value != "\n", ordinal.find("div", class_="defContent").contents):
                instance_type = instance["class"][0]
                if instance_type == "example" and len(meaning["example"]) < verbosity["example"]:
                    meaning[instance_type].append(description_grammar(instance.text.replace("\n", "")[1:-1]))
                elif instance_type == "instances":
                    instance_type = instance.find("dt").string
                    if instance_type is not None:
                        save_instance_type = instance_type = instance_type[0].lower() + instance_type[1:-1]
                    else:
                        instance_type = save_instance_type
                    for words in instance.find_all("dd"):
                        definition = words.find("div", class_="definition")
                        if definition is not None:
                            definition = description_grammar(definition.string)
                        for word in words.find_all("a", class_="word"):
                            if len(meaning[instance_type]) < verbosity[instance_type]:
                                meaning[instance_type][word.string] = definition
            meanings.append(meaning)
            ordinals[-1] += 1

    # word family
    if verbosity["family"] > 0:
        data_str = soup.find("vcom:wordfamily")["data"].split("{")
        data_str[-1] = data_str[-1] + ","
        family = Node("Word Family:")
        word_freq = 0.0
        for word_str in data_str[1:]:
            word_parent = family
            for item in word_str[1:-2].split(","):
                key, value = item.replace('"', "").split(":")
                if key == "word":
                    word_name = value
                elif key == "freq":
                    word_freq = float(value)
                elif key == "parent":
                    word_parent = find_node(family, lambda node: node.name == value)
            element = Node(word_name, parent=word_parent,
                           freq=print_freq(word_name, word_freq) if verbosity["freq"] else word_name.title())
        for element in list(LevelOrderIter(family))[verbosity["family"] + 1:]:  # length control
            element.parent = None
        exporter = DictExporter()
        family = exporter.export(family)
    else:
        family = {}

    # usage
    # how to scrape usage
    # disguise your bot as firefox using selenium to retrieve so-called "non-robot content"
    examples = []
    if verbosity["usage"] > 0:
        try:
            options = Options()
            options.headless = True
            browser = webdriver.Firefox(options=options, executable_path="geckodriver.exe")
            browser.get(url)
        except WebDriverException:
            print(Fore.RED + "The web driver you requested is unavailable." + Style.RESET_ALL)
            return
        last = ""
        max_repetition = 100
        repetition = 0
        while True:
            try:
                next_ = WebDriverWait(browser, 10)\
                    .until(presence_of_element_located((By.CLASS_NAME, 'ss-navigateright')))
                try:
                    next_.click()
                except WebDriverException:
                    privacy_button = WebDriverWait(browser, 20) \
                        .until(presence_of_element_located((By.CLASS_NAME, "qc-cmp-button")))
                    privacy_button.click()
            except ElementNotVisibleException:  # last page reached...I guess?
                break
            while True:
                try:  # infinite loop!
                    example = WebDriverWait(browser, 10)\
                        .until(presence_of_element_located((By.CLASS_NAME, 'results')))
                except StaleElementReferenceException:  # happens when element is being changed
                    continue
                example_text = example.text
                if example_text == "no examples found" or example_text == "":
                    break
                elif example_text == "loading examples...":
                    continue
                #  Selenium Firefox's text seems to have some problems.
                #  Sometimes, text in <> brackets won't show up, but other times they show up,
                #  causing the direct compare between text and last_last to become unfunctional...
                elif SequenceMatcher(None, example_text, last).ratio() > 0.9:
                    repetition += 1
                    if repetition >= max_repetition:
                        break
                else:
                    example_soup = BeautifulSoup(example.get_attribute("innerHTML"), features="lxml")
                    for example in example_soup.find_all("li"):
                        sentence = description_grammar(example.find(class_="sentence").text)
                        date = example.find(class_="date")
                        if date is not None:
                            date = description_grammar(date.text)
                        title = example.find(class_="corpus")
                        if title is not None:
                            title = description_grammar(title.text)
                        else:
                            title = example.find(class_="title")
                            if title is not None:
                                title = description_grammar(title.text)
                        examples.append({"sentence": sentence,
                                         "title": title,
                                         "date": date})
                    last = example_text
                    repetition = 0
            if repetition == max_repetition or len(examples) >= verbosity["usage"]:
                examples = examples[:verbosity["usage"]]
                break
        browser.close()

    # make dict
    word = {save_word: {"short": short_text,
                        "long": long_text,
                        "ordinal": ordinals,
                        "meaning": meanings,
                        "usage": examples,
                        "family": family
                        }}
    word_create(word, "History")
    return word


def word_request(word_str):
    path = process_path("History")
    dictionary = dictionary_request(path)["contents"]
    if word_str in dictionary:
        return {word_str: dictionary[word_str]}
    else:
        return word_scrape(word_str)


def word_test_helper(word, word_str):
    success_reply = [["Nice Job!",
                      "Correct!"],
                     ["You got it!",
                      "Bingo!",
                      "We knew you'd figure it out!",
                      "We have a winner!"],
                     ["Third time's a charm, huh?"],
                     ["That's the one!",
                      "You're a genius!"]]

    failure_reply = [["Strike 1! Give it another try!",
                      "Um, no. What's your second guess?",
                      "Nope, that wasn't it. Take another look."],
                     ["Look at the bright side, now you have a 50/50 chance!",
                      "Survey says: you're wrong again.",
                      "That wasn't it either.",
                      "You're getting warmer..."],
                     ["You can't miss now.",
                      "Let me make this real easy for you.",
                      "See if you can spot the right answer now.",
                      "Well, it should be pretty easy now, take a wild guess.",
                      "I guess today isn't your lucky day."]]

    def word_instance_test(word, word_str):
        def word_random_instance(word, instance):
            if "meaning" in word:
                indexes = []
                meaning = word["meaning"]
                for i in range(len(meaning)):
                    if instance in meaning[i] and meaning[i][instance] is not None and not \
                            (type(meaning[i][instance]) == OrderedDict and not (meaning[i][instance])):
                        indexes.append(i)
                if len(indexes) != 0:
                    index = meaning[choice(indexes)]
                    return {"title": index["title"],
                            "definition": index["definition"],
                            "answer": choice(list(index[instance]))}
            return None

        instance_table = {"antonyms": "The opposite of " + word_str + " is:",
                          "synonyms": word_str.title() + " could best be described as which of the following?",
                          "type of": word_str.title() + " is a type of:",
                          "types": "Which of the following is a type of " + word_str + "?"
                          }
        instances = list(instance_table.keys())
        shuffle(instances)
        for instance in instances:
            result = word_random_instance(word, instance)
            if result is not None:
                start_question = instance_table[instance]
                choices, correct_answer = pool_request("words", result["answer"])
                end_question = "In this question, " + word_str + " is " + print_part_of_speech(result["title"]) +\
                               " that " + print_meaning(result["title"]) + " " + result["definition"] + ".\n"
                return start_question, choices, end_question, correct_answer
        return None

    def word_definition_test(word, word_str):
        meanings = word["meaning"]
        shuffle(meanings)
        for meaning in meanings:
            if "definition" in meaning:
                if "title" in meaning:
                    start_question = word_str.title() + " " + print_meaning(meaning["title"]) + ":"
                else:
                    start_question = "The correct definition of " + word_str + " is:"
                choices, correct_answer = pool_request("definitions", meaning["definition"])
                end_question = ""
                return start_question, choices, end_question, correct_answer
        return None

    def word_usage_test(word, word_str):
        if "usage" in word and word["usage"]:
            usage = choice(word["usage"])
            start_question = usage["sentence"].replace(word_str, "________") + "\n" + "Source: " + usage["title"]
            choices, correct_answer = pool_request("words", word_str)
            end_question = ""
            return start_question, choices, end_question, correct_answer
    question_types = [word_instance_test, word_definition_test, word_usage_test]
    shuffle(question_types)
    for question_type in question_types:
        result = question_type(word, word_str)
        if result is not None:
            start_question, choices, end_question, correct_answer = result[0], result[1], result[2], result[3]
            choices = [{"name": choice_} for choice_ in choices]
            failure = 0
            while True:
                print(start_question)
                question = [
                    {
                        'type': 'checkbox',
                        'message': "",
                        'name': 'answer',
                        'choices': choices,
                    }
                ]
                answer = prompt(question)["answer"]
                if type(answer) == list and len(answer) == 1:  # whaaaaat validate doesn't seem to work
                    answer = answer[0]
                    if answer != correct_answer:
                        for choice_ in choices:
                            if choice_["name"] == answer:
                                choice_["disabled"] = "wrong answer"
                        print(Fore.LIGHTRED_EX + choice(failure_reply[min(2, failure)]) + Style.RESET_ALL + "\n-----")
                        failure += 1
                    else:
                        print(Fore.LIGHTGREEN_EX + choice(success_reply[min(3, failure)]) +
                              "\n-----" + ("\n" + end_question if end_question != "" else "") + Style.RESET_ALL)
                        if "short" in word and word["short"] is not None:
                            print(Fore.GREEN + word["short"] + Style.RESET_ALL)
                        if "long" in word and word["long"] is not None:
                            print("\n" + Fore.GREEN + word["long"] + Style.RESET_ALL)
                        break
                else:
                    print(Fore.RED + "I'm so confused." + Style.RESET_ALL + "\n-----\n")
            break
    return failure == 0


def word_print(word_str, word, verbosity):
    # pretty print
    title_styles = {"noun": Fore.LIGHTRED_EX + "Noun" + Style.RESET_ALL,
                    "verb": Fore.LIGHTGREEN_EX + "Verb" + Style.RESET_ALL,
                    "adjective": Fore.LIGHTYELLOW_EX + "Adjective" + Style.RESET_ALL,
                    "adverb": Fore.LIGHTMAGENTA_EX + "Adverb" + Style.RESET_ALL}
    index = 0
    if verbosity["audio"]:
        audio_path = (Path("Vocabot") / "audio" / word_str).with_suffix(".mp3")
        if audio_path.exists():
            playsound(str(audio_path))
    if "ordinal" in word:  # a word that is scraped
        # print main text
        if word["short"] is not None and verbosity["short"]:
            print(Fore.LIGHTGREEN_EX + word["short"] + Style.RESET_ALL + "\n")
        if word["long"] is not None and verbosity["long"]:
            print(Fore.GREEN + word["long"] + Style.RESET_ALL + "\n")

        # print definitions
        print(Fore.LIGHTWHITE_EX + "Definitions:" + Style.RESET_ALL)
        for ordinal_index in range(len(word["ordinal"])):
            print(Fore.LIGHTWHITE_EX + ("\n" if ordinal_index != 0 else "")
                  + str(ordinal_index + 1) + "-----" + Style.RESET_ALL)
            for i in range(index, index + word["ordinal"][ordinal_index]):
                print(Fore.LIGHTWHITE_EX + str(i - index + 1) + Style.RESET_ALL)
                meaning = word["meaning"][i]
                if "title" in meaning and verbosity["title"]:
                    print(title_styles[meaning["title"]])
                if "definition" in verbosity and verbosity["definition"]:
                    print(Fore.LIGHTGREEN_EX + meaning["definition"] + Style.RESET_ALL)
                if "example" in meaning:
                    for example in meaning["example"][:verbosity["example"]]:
                        print(Fore.GREEN + '"' + example + '"' + Style.RESET_ALL)
                instances = {instance: dict(list(meaning[instance].items())[-verbosity[instance]:])
                             for instance in ["antonyms", "synonyms", "types", "type of", "examples"]
                             if instance in meaning and meaning[instance] != {}}
                for instance in instances:
                    str_list = []
                    for (word_str, definition) in instances[instance].items():
                        if definition is None:
                            str_list.append("|" + word_str)
                        else:
                            str_list.append("|" + word_str + " > " + definition)
                    print(Fore.LIGHTCYAN_EX + instance + Style.RESET_ALL + "\n" + Fore.CYAN +
                          "\n".join(str_list) + Style.RESET_ALL)
            index += word["ordinal"][ordinal_index]

        # print family
        print(Fore.LIGHTWHITE_EX + "\n\nWord Family:" + Style.RESET_ALL)
        importer = DictImporter()
        family = importer.import_(word["family"])
        family = RenderTree(family, style=ContRoundStyle()).by_attr("freq")
        family = "\n".join(family.split("\n")[1:verbosity["family"] + 1])
        family += "\n╰──────"
        print(Fore.LIGHTGREEN_EX + family + Style.RESET_ALL)

        # print usage
        if word["usage"] is not None:
            print(Fore.LIGHTWHITE_EX + "\n\nUsage:" + Style.RESET_ALL)
            for usage in word["usage"][:verbosity["usage"]]:
                print(Fore.LIGHTCYAN_EX + usage["sentence"] + Style.RESET_ALL + Fore.CYAN + "\n--" + usage["title"] +
                      " " + (usage["date"] if usage["date"] is not None else "") + Style.RESET_ALL)
    else:  # a word from a list
        word = word["meaning"][0]
        if "definition" in word:
            print(Fore.LIGHTGREEN_EX + word["definition"] + Style.RESET_ALL)
        if "example" in word:
            print(Fore.GREEN + word["example"] + Style.RESET_ALL)
        if "examples" in word:
            if "Example" in word["examples"]:
                print(word["examples"]["Example"])


def dictionary_news(count, words, pop_culture, full, save_count):
    url = "https://www.vocabulary.com/profiles/A0WR12FSY70TG4"  # Adam C. profile page
    with get(url) as page:
        soup = BeautifulSoup(page.content, features="lxml")
    soup = soup.find("ol", class_="hasmore")
    for list_ in soup.find_all("li")[:count * 2]:
        element_a = list_.div.h2.a
        if words and "Words" in element_a.text:
            dictionary_download(element_a["href"].split("/")[-1], full, save_count)
        if pop_culture and "Pop Culture" in element_a.text:
            dictionary_download(element_a["href"].split("/")[-1], full, save_count)


def dictionary_create(path, description):
    dictionary_save(OrderedDict({"title": Path(path).name,
                                 "description": description,
                                 "score": -1,
                                 "contents": {}}),
                    path)


def dictionary_download(list_id, full, save_count):
    # request
    url = "https://www.vocabulary.com/lists/" + str(list_id)
    with get(url) as page:
        soup = BeautifulSoup(page.content, features="lxml")
    if soup is None:
        return

    # metadata
    title = description_grammar(soup.head.title.string.split(" - Vocabulary List")[0])
    description = description_grammar(soup.head.find("meta", attrs={"name": "description"})["content"])
    indexes = soup.find_all("li", class_="entry", lang="en")
    count = save_count

    # check for existing download
    dictionary = dictionary_request(Path("lists") / title, return_error=False)
    if dictionary is None:
        dictionary = OrderedDict()
    else:
        dictionary = dictionary["contents"]
        indexes = indexes[len(dictionary):]
        print(indexes)

    # scrape
    for index in indexes:
        # get name
        word = index["word"]
        if not full:  # scrape only the information from the word list
            meaning = {}
            meaning["definition"] = index.find("div", class_="definition").text
            meaning["example"] = index.find("div", class_="example")
            if meaning["example"] is not None:
                meaning["example"] = description_grammar(meaning["example"].text.replace("\n", ""))
            description = index.find("div", class_="description")
            if description is not None:
                description = description_grammar(description.text.replace("\n", ""))
            meaning["examples"] = {"Example": description}
            dictionary.update({word: {"meaning":[meaning]}})
        else:  # scrape the word individually
            dictionary.update(word_scrape(word))
        count -= 1
        if count == 0 or index == indexes[-1]:
            count = save_count
            dictionary_save({"title": title,
                             "description": description,
                             "score": -1,
                             "contents": dictionary},
                            Path("lists") / title,
                            force=True)


def dictionary_remove(path):
    path = process_path(path)
    if Path.exists(path):
        Path.unlink(path)
    else:
        path_error()


def dictionary_save(dictionary, path, force=False):
    path = process_path(path)
    path.parents[0].mkdir(parents=True, exist_ok=True)
    if not force:
        if Path.exists(path):
            if confirm("Duplicates detected. Overwrite?"):
                Path.unlink(path)
                print("Overwrite successful")
            else:
                print("Aborting...")
                return
    with open(path, "w") as file:
        dump(dictionary, file, indent=4, ensure_ascii=False)


def dictionary_print(path, order, number):
    verbosity = settings_check(2)
    path = process_path(path)
    dictionary = dictionary_request(path)
    print(Fore.LIGHTGREEN_EX + dictionary["title"] + Style.RESET_ALL)
    print(Fore.GREEN + dictionary["description"] + "\n" + Style.RESET_ALL)
    if confirm("Start reviewing?", default=True):
        if number < 1 or number > len(dictionary["contents"]):
            number = len(dictionary["contents"])
        if order == 1:
            words = list(dictionary["contents"].items())[:number]
        elif order == -1:
            words = reversed(list(dictionary["contents"].items())[-number:])
        elif order == 0:
            words = sample(list(dictionary["contents"].items()), number)
        else:
            words = []
            number = 0
        for index in range(number):
            print(Fore.LIGHTWHITE_EX + str(index + 1) + ". " + words[index][0] + Style.RESET_ALL)
            word_print(words[index][0], words[index][1], verbosity)
            if not confirm("Next?", default=True):
                break
            print("\n\n\n", end="")
    print("Finished.")


def dictionary_request(path, return_error=True):
    if not Path.exists(path):
        for possible_path in (Path("Vocabot") / "dictionaries").rglob("*.json"):  # fuzzy match
            if path.name == possible_path.name:
                path = possible_path
    if Path.exists(path):
        with open(path) as file:
            return load(file, object_pairs_hook=OrderedDict)
    elif return_error:
        path_error()


def dictionary_test(path):
    compliments = [["Still has some space for improvement tho.",
                    "I have faith in you. Remember, practise makes perfect."],
                   ["Keep up the good work. You can get even better!"],
                   ["This is... Beyond godlike.",
                    "Unbelievable."],
                   ["Either you're hacking or my program is has some bugs.",
                    "Are you human? I need to run some recaptcha"]]
    path = process_path(path)
    dictionary = dictionary_request(path)
    print(Fore.LIGHTGREEN_EX + dictionary["title"] + Style.RESET_ALL)
    print(Fore.GREEN + dictionary["description"] + "\n" + Style.RESET_ALL)
    success = 0
    if confirm("Start the test?", default=True):
        words = list(dictionary["contents"].items())
        shuffle(words)
        length = len(words)
        test_time = 0
        for index in range(length):
            print(str(index + 1) + ".")
            start_time = time()
            correct = word_test_helper(words[index][1], words[index][0])
            test_time += (time() - start_time)
            if correct:
                success += 1
            print("\n\n", end="")
            if not confirm("Next?", default=True):
                print("Aborting...")
                print("Finished.")
                return
    else:
        return
    average_time = test_time / length * 100 // 1 / 100
    success_rate = success / length * 10000 // 1 / 100
    final_result = (100 / average_time) * (success_rate ** 2) * 100 // 1 / 100
    print(Fore.LIGHTGREEN_EX + "You've finished this round.\nLet the good times roll!\nLet's see..." + Style.RESET_ALL)
    print(Fore.LIGHTCYAN_EX + "Success Rate: " + Style.RESET_ALL + Fore.CYAN + str(success_rate) + Style.RESET_ALL)
    print(Fore.LIGHTCYAN_EX + "Average Time: " + Style.RESET_ALL + Fore.CYAN + str(average_time) + Style.RESET_ALL)
    print(Fore.LIGHTCYAN_EX + "Final Result: " + Style.RESET_ALL + Fore.CYAN + str(final_result) + Style.RESET_ALL)
    print(Fore.LIGHTCYAN_EX + "Highscore: " + Style.RESET_ALL + Fore.CYAN + str(dictionary["score"]) + Style.RESET_ALL)
    if final_result > dictionary["score"]:
        dictionary["score"] = final_result
        print(Fore.LIGHTGREEN_EX + "New Highscore. Congrats!" + Style.RESET_ALL)
        if final_result < 100000:
            print(Fore.GREEN + choice(compliments[0]) + Style.RESET_ALL)
        elif final_result < 250000:
            print(Fore.GREEN + choice(compliments[1]) + Style.RESET_ALL)
        elif final_result < 1000000:
            print(Fore.GREEN + choice(compliments[2]) + Style.RESET_ALL)
        else:
            print(Fore.GREEN + choice(compliments[3]) + Style.RESET_ALL)
        dictionary_save(dictionary, path, force=True)


colorama_init()
global settings_path
settings_path = Path("Vocabot") / "settings.json"

parser = Parser(prog="Vocabot", description="Vocabulary.com cli written in Python, pretty buggy and slow though.",
                epilog="Stupid argparse can't accept comma as separator in nargs option. Needs some manual splitting.")

subparsers = parser.add_subparsers()
parser_si = subparsers.add_parser("settings-initialize", aliases=["si"],
                                  help="Initialize the program. Download necessary files and create paths.")
parser_si.set_defaults(func=lambda a: initialize())
parser_sc = subparsers.add_parser("settings-configure", aliases=["sc"],
                                  help="Configure settings.")
parser_sc.set_defaults(func=lambda a: settings_configure())

parser_wv = subparsers.add_parser("word-vocabot", aliases=["wv"],
                                  help="Pretty print the word(s) given and add it into the default dictionary.")
parser_wv.set_defaults(func=lambda a: word_vocabot(a.word))
parser_wv.add_argument("word", help="String of word(s) separated by commas.")

parser_dp = subparsers.add_parser("dictionary-print", aliases=["dp"],
                                  help="Pretty print the dictionary entries.")
parser_dp.set_defaults(func=lambda a: dictionary_print(a.path, a.order, a.number))
parser_dp.add_argument("-p", "--path", default=None, help="Dictionary path.")
parser_dp.add_argument("-o", "--order", default=0, type=int, choices=[1, 0, -1],
                       help="Enter 0 to print randomly, 1 to print from the beginning, -1 to print from the end.")
parser_dp.add_argument("-n", "--number", default=float("inf"), type=int, help="Number of entries to be printed.")
parser_dc = subparsers.add_parser("dictionary-create", aliases=["dc"],
                                  help="Create dictionary from path, creating directories in the process if needed.")
parser_dc.set_defaults(func=lambda a: dictionary_create(a.path, a.description))
parser_dc.add_argument("path", help="Dictionary path. Must be specified.")
parser_dc.add_argument("description", help="Dictionary description.")
parser_dl = subparsers.add_parser("dictionary-download", aliases=["dl", "download-list"],
                                  help="Download the vocabulary list.")
parser_dl.set_defaults(func=lambda a: dictionary_download(a.id, a.not_full, a.save))
parser_dl.add_argument("id", type=int, help="Vocabulary list id.")
parser_dl.add_argument("-nf", "--not-full", action="store_false",
                       help="If specified, download each word's information directly from the list.")
parser_dl.add_argument("-s", "--save", default=5, type=int,
                       help="Save interval for downloading.")
parser_dt = subparsers.add_parser("dictionary-test", aliases=["dt"],
                                  help="Test the dictionary.")
parser_dt.set_defaults(func=lambda a: dictionary_test(a.path))
parser_dt.add_argument("-p", "--path", default=None, help="Dictionary path.")
parser_dn = subparsers.add_parser("dictionary-news", aliases=["dn"],
                                  help="Grab the news of this week's vocabulary from Adam C.'s profile page.")
parser_dn.set_defaults(func=lambda a: dictionary_news(a.number, a.words, a.pop, a.not_full, a.save))
parser_dn.add_argument("-n", "--number", default=1, type=int,
                       help="Starting from the latest list, the number of weeks of lists whose vocabulary is needed")
parser_dn.add_argument("-w", "--words", action="store_true",
                       help="If specified, download this week of words.")
parser_dn.add_argument("-p", "--pop", action="store_true",
                       help="If specified, download this week of pop culture.")
parser_dn.add_argument("-nf", "--not-full", action="store_false",
                       help="If specified, download each word's information directly from the list.")
parser_dn.add_argument("-s", "--save", default=5, type=int,
                       help="Save interval for downloading.")

if len(argv) > 2 or argv[1] in ["settings-initialize", "si", "settings-configure", "sc", "word-vocabot", "wv",
                                "word-print", "wp", "word-create", "wc", "word-remove", "wr", "dictionary-print",
                                "dp", "dictionary-create", "dc", "dictionary-download", "dl", "download-list",
                                "dictionary-test", "dt", "dictionary-news", "dn"]:
    args = parser.parse_args()
    args.func(args)
elif argv[1] in ["--help", "-h"]:
    args = parser.parse_args()
else:
    word_vocabot(argv[1])
