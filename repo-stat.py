#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import git
import argparse
import json
import sys
import datetime
import re
import subprocess
from git import Repo
from datetime import timedelta
from os.path import isfile

plot_template = """
set title "Number of commits from the team to the repositories"
set terminal png
set output "NAME.png"
set xtics nomirror rotate by -45
set terminal png font "/usr/share/fonts/truetype/freefont/FreeSans.ttf" 10 size 1800,900
set rmargin 5
set linetype 1 lc rgb '#183693'
set yrange [0:*]
set ytics 5
set grid
TICS
$dataset << EOD
DATA
EOD
f(x) = a + b*x
set fit quiet
set fit logfile '/dev/null'
fit f(x) $dataset using 1:2 via a, b
plot [0:X_MAX] $dataset title "Number of commits" with lines lw 5, f(x) with lines lw 5
"""


def gnuplot(data):
    try:
        gnuplot_process = subprocess.Popen(["gnuplot"],
                                           stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           encoding='utf8')
    except OSError as e:
        return False, "Could not execute gnuplot ({0}): {1}".format(e.errno,
                                                                    e.strerror)
    gnuplot_process.stdin.write("%s" % data)
    stdout_value, stderr_value = gnuplot_process.communicate()
    if stderr_value:
        return False, stderr_value.decode("utf-8")
    return True, 0


def check_valid_input_json(value):
    if not isfile(value):
        raise argparse.ArgumentTypeError("%s does not exist" % value)
    try:
        with open(value, "rt") as input_json_file:
            json.load(input_json_file)
    except:
        raise argparse.ArgumentTypeError('Not a valid json file: %s' % value)
    return value


def parse_args():
    example_json = '''example input json:
    {
        "repos": [ "user/repo",
                   "user_2/repo_2" ],
        "team": [ "github_username_1",
                  "github_username_2",
                  "github_username_3"]
    }
    '''
    parser = argparse.ArgumentParser(prog='repo-stat.py',
                                     description='Generates stats of git \
                                                  repositories based on \
                                                  json input.',
                                     epilog=example_json,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        dest='debug', help='debug mode')
    parser.add_argument("-i", "--input-json", dest="json",
                        type=check_valid_input_json, default=None,
                        help="File with repos and team members in json format.")
    parser.add_argument("-w", "--weeks", dest="weeks", type=int, default=None,
                        help="Length of period in weeks")
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()
    return parser


def sorted_alphanumerically(l):
    """ Sort the given iterable in the way that humans expect."""
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def update_repos(repos):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    from_date = datetime.datetime.today() - timedelta(days=7*args.weeks)

    for r in repos:
        m = re.match(r"(.*)(\/+)(.*)", r)
        repo_directory = r
        if m:
            repo_directory = m.group(3)
        if not os.path.isdir(repo_directory):
            print("Cloning %s" % r)
            g = git.Git(dir_path)
            g.clone("git://github.com/%s" % r)
        else:
            print("Updating %s" % repo_directory)
            g = git.cmd.Git("%s" % repo_directory)
            g.pull()
        repo = Repo(repo_directory)
        if not repo.bare:
            commits = list(repo.iter_commits('master'))
            for commit in commits:
                d = datetime.datetime.fromtimestamp(commit.authored_date)
                if d < from_date:
                    continue
                week = "%s - %s" % (d.year, d.isocalendar()[1])
                if week in repo_data:
                    if commit.author.name in team:
                        repo_data[week]['team'] += 1
                        repo_data[week]['all'] += 1
                    else:
                        repo_data[week]['all'] += 1
                else:
                    repo_data.update({'%s' % week: 1})
                    repo_data.update({'%s' % week: {'team': 1, 'all': 1}})
                pass
        else:
            print('Could not load repository at {}'.format(repo_path))


if __name__ == "__main__":
    parser = parse_args()
    args = parser.parse_args(sys.argv[1:])
    if args.debug:
        print('\nargs: ' + str(sys.argv))
    try:
        with open(args.json) as f:
            data = json.load(f)
        if args.debug:
            print("input json " + json_file + ":")
            print(json.dumps(data, sort_keys=True, indent=4))
        try:
            repos = data['repos']
            team = data['team']
        except KeyError as e:
            print("\nMissing json key: " + str(e))
            exit(1)
    except (IOError, json.JSONDecodeError) as e:
        print(e)
        exit(1)
    repo_template = '{}'
    repo_data = json.loads(repo_template)
    update_repos(repos)
    plot = plot_template
    data_index = 0
    data_table = ""
    ticsline = ""
    separator = ""
    newline = ""
    for week in sorted_alphanumerically(repo_data):
        data_table += ("%s%s\t%s" % (newline,
                                     data_index,
                                     repo_data[week]['team']))
        ticsline += ("%s\"%s\" %s" % (separator, week, data_index))
        data_index += 1
        separator = ","
        newline = "\n"
    plot = re.sub(r"X_MAX", "%s" % data_index, plot)
    plot = re.sub(r"DATA", "%s" % data_table, plot)
    plot = re.sub(r"PNG", "%s" % "weekly.png", plot)
    plot = re.sub(r"TICS", "set xtics (%s)" % ticsline, plot)
    plot = re.sub(r"NAME", "%s-%s-weeks" % (os.path.splitext(args.json)[0],
                                            args.weeks), plot)
    gnuplot(plot)
    file = open("repo-stat.plot", "w")
    file.write(plot)
    file.close()
    with open("repo-stat.json", 'wt') as json_file:
        json.dump(repo_data, json_file, indent=4)
