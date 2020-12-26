import json
import os
import pathlib
import sys
from shutil import copyfile

import click
import frontmatter
import mistune
import requests
from jinja2 import Environment, FileSystemLoader
import metadata_parser
from PIL import Image

@click.group()
def main():
    """click"""
    pass


def load_mds():
    glob = pathlib.Path('sources/articles').glob("*.md")
    results = []
    md = mistune.Markdown()
    for item in sorted(glob):
        matter = frontmatter.load(item)
        data = dict(matter)
        # how wil this be printable though ?
        data['body'] = md(matter.content)
        data['filename'] = pathlib.Path(item).stem
        results.append(data)

    return results


def fetch_metadata(article):
    md = {}
    try:
        # todo: didnt work with hisvoice a] fetch got 403 - maybe user agent issue ?
        # b] exception not caught ? - script stopped
        page = metadata_parser.MetadataParser(url=article['url'])
        md = page.metadata
        with open(f'data/meta/{article["filename"]}.json', 'w') as f:
            json.dump(md, f, sort_keys=True, indent=4)
    except:
        e = sys.exc_info()[0]
        click.echo(e)

    return md


def create_thumbnail(article):
    # check whether thumbnail exists
    thumb_file = f'data/thumb/{article["filename"]}.png'
    if not os.path.isfile(thumb_file):
        image_file = f'data/ogimg/{article["filename"]}.jpg'
        if not os.path.isfile(image_file):
            with open(image_file, 'wb') as ogf:
                r = requests.get(article['image'])
                ogf.write(r.content)
        ogimg = Image.open(image_file)
        ogimg.thumbnail((100, 100))
        ogimg.save(thumb_file)
    copyfile(thumb_file, f'public/img/thumb/{article["filename"]}.png')


def process_articles(articles):
    for a in articles:
        try:
            with open(f'data/meta/{a["filename"]}.json') as f:
                md = json.load(f)
        except FileNotFoundError:
            md = fetch_metadata(a)
        og = md.get('og', {})
        meta = md.get('meta', {})
        author = meta.get('author', '')
        if author != '':
            a['author'] = author
        a['title'] = og.get('title', '')
        a['description'] = og.get('description', '')
        a['image'] = og.get('image', '')
        if a['image'] != '':
            try:
                create_thumbnail(a)
            except Exception as e:
                print(e)
        # ['og', 'meta', 'dc', 'page', 'twitter', '_internal', '_v']
        # click.echo(md.keys())
    return articles


@click.command()
def publish():
    articles = load_mds()
    articles = process_articles(articles)
    env = Environment(
        loader=FileSystemLoader('templates'),
    )
    with open(f'public/index.html', 'w') as f:
        f.write(env.get_template('index.html').render(articles=articles))


@click.command()
@click.argument('filename', required=True)
@click.argument('url')
def add(filename, url):
    with open('TEMPLATE.md') as t:
        template = t.read()
        template = template.replace('url:', f'url: {url}')
    with open(f'sources/articles/{filename}.md', 'w') as f:
        f.write(template)


main.add_command(add)
main.add_command(publish)

if __name__ == "__main__":
    main()


