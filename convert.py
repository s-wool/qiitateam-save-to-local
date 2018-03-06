#! /usr/bin/env python
# coding: utf-8

import zipfile
import os
import pathlib
import re
import json
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import shutil
import sys
import argparse


qiita_api_key = ''
team_domain = ''
global_image_domain = 'qiita-image-store.s3.amazonaws.com'


def replace_image(markdown, html):
    headers = {'Authorization': 'Bearer ' + qiita_api_key}
    sp = BeautifulSoup(html, 'html.parser')
    for img in sp.findAll('img'):
        url = img.get('src')
        parse_result = urlparse(url)

        if parse_result.hostname == team_domain or parse_result.hostname == global_image_domain:
            filename = os.path.basename(parse_result.path)
            save_path = "./output/images/" + filename
            if not os.path.exists(save_path):
                res = requests.get(url, headers=headers)            
                with open(save_path, "wb") as image:
                    image.write(res.content)

            replaced_name = "../../../images/" + filename
            markdown = markdown.replace(url, replaced_name)

    return markdown


def create_comments(comments):
    text = ''
    for comment in comments:
        text = text + "\n\n" + replace_image(comment['body'], comment['rendered_body'])
        text = text + "Comment posted by {}\n\n".format(comment['user']['id'])
    return text


def create_md(content):
    url = urlparse(content['url'])
    path = './output/articles' + url.path + '.md'
    markdown = content['body']
    html = content['rendered_body']
    text = "# {}\n\n".format(content['title'])
    text = text + replace_image(markdown, html)
    text = text + "\n\nPosted at {} by {}\n\n".format(content['created_at'], content['user']['id'])
    if 'comments_count' in content and content['comments_count'] > 0:
        text = text + create_comments(content['comments'])

    pathlib.Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as md:
        md.write(text)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--team', help='team name', required=True)
    parser.add_argument('-f', '--file', help='backup filepath', required=True)
    parser.add_argument('-k', '--key', help='apikey', required=True)
    args = parser.parse_args(argv)
    global qiita_api_key
    qiita_api_key = args.key
    global team_domain
    team_domain = args.team + ".qiita.com"

    if os.path.exists("./output"):
        shutil.rmtree("./output")

    pathlib.Path('./output/articles').mkdir(parents=True, exist_ok=True)
    pathlib.Path('./output/images').mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(args.file, 'r') as z:
        filelist = z.infolist()
        articles = [x for x in filelist if re.match('.+\/articles\/.+', x.filename)]
        for article in articles:
            content = json.load(z.open(article.filename))
            create_md(content)


if __name__ == '__main__':
    main()
