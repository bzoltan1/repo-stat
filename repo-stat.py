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
from argparse import ArgumentParser
from git import Repo
from datetime import timedelta
from os.path import isfile
from shutil import which

plot_template = """
set title "Number of commits from the team to the repositories"
set terminal png
set output "NAME.png"
set xtics nomirror rotate by -45
set terminal png font "/usr/share/fonts/truetype/freefont/FreeSans.ttf" \
10 size 1800,900
set rmargin 5
set linetype 1 lc rgb '#183693'
set yrange [0:*]
set ytics YTICS
set grid
TICS
$dataset << EOD
DATA
EOD
f(x) = a + b*x
set fit quiet
set fit logfile '/dev/null'
fit f(x) $dataset using 1:2 via a, b
plot [0:X_MAX] $dataset using 1:2 title "Number of UNIT by the team" \
with lines lw 5, f(x) with lines lw 5"""

plot_all_template = """,\\
               $dataset using 1:3 title "Number of UNIT by all \
contributors" with lines lw 5
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
    except Exception:
        raise argparse.ArgumentTypeError('Not a valid json file: %s' % value)
    return value


def check_measure_type(value):
    measure = ["commits", "size", "kudos"]
    if value not in measure:
        raise argparse.ArgumentTypeError("Can not measre by %s. Must be \
                                         [commits|size|kudos]")
    return value


def parse_args():
    example_json = '''example input json:
    {
        "repos": [ "user/repo",
                   "user_2/repo_2" ],
        "team": [ "username_1",
                  "username_2",
                  "username_3"],
        "kudos": ".*"
    }
    '''
    p = ArgumentParser(prog='repo-stat.py',
                       description='Generates stats of git' +
                       'repositories based on' +
                       'json input.',
                       epilog=example_json,
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('-d', '--debug', default=False, action='store_true',
                   dest='debug', help='debug mode')
    p.add_argument("-i", "--input-json", dest="json",
                   type=check_valid_input_json, default=None,
                   help="File with repos and team \
                              members in json format.")
    p.add_argument("-m", "--measure", dest="measure",
                   type=check_measure_type, default="size",
                   help="Create statistics bases on number of commits, \
                         size of commits or new files matching the kudos \
                         regexp [commits|size|kudos].")

    p.add_argument("-w", "--weeks", dest="weeks", type=int, default=52,
                   help="Length of period in weeks")
    p.add_argument("-a", "--all",
                   dest="all", default=False, action='store_true',
                   help="Show the graph of all contributions")

    if len(sys.argv[1:]) == 0:
        p.print_help()
        p.exit()
    return p


def convert(text):
    return int(text) if text.isdigit() else text


def alphanum_key(key):
    return [convert(c) for c in re.split('([0-9]+)', key)]


def sorted_alphanumerically(l):
    """ Sort the given iterable in the way that humans expect."""
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
            if args.debug:
                print("Cloning %s" % r)
            g = git.Git(dir_path)
            g.clone("git://github.com/%s" % r)
        else:
            if args.debug:
                print("Updating %s" % repo_directory)
            g = git.cmd.Git("%s" % repo_directory)
            g.pull()
        repo = Repo(repo_directory)
        if not repo.bare:
            commits = list(repo.iter_commits('master'))

            for commit in commits:
                if commit.message.startswith("Merge pull request "):
                    continue
                if args.measure in ["size", "kudos"]:
                    increase = 0
                    if args.measure == "size":
                        for changed in commit.stats.files:
                            increase += commit.stats.files[changed]['lines']
                    else:
                        if commit.parents:
                            for change_diff in commit.diff(commit.parents[0]):
                                if change_diff.b_blob is None:
                                    m = re.match(r"%s" % kudos,
                                                 change_diff.a_blob.path)
                                    if m:
                                        for changed in commit.stats.files:
                                            m_stats = re.match(r"%s" % kudos,
                                                               changed)
                                            if m_stats:
                                                increase += commit.stats.files[changed]['lines']
                                        if args.debug:
                                            print("new: %s - %s" % (increase,
                                                                    change_diff.a_blob.path))
                                            print("\t%s - %s - %s" % (datetime.datetime.fromtimestamp(commit.committed_date), commit.author.name, commit.message.partition('\n')[0]))
                                        break
                else:
                    increase = 1
                d = datetime.datetime.fromtimestamp(commit.committed_date)
                if d < from_date:
                    break
                week = "%s - %s" % (d.year, d.isocalendar()[1])
                if week in repo_data:
                    if commit.author.name in team:
                        repo_data[week]['team'] += int(increase)
                        repo_data[week]['all'] += int(increase)
                        if args.debug:
                            print("size: %s " % (increase))
                            print("\t%s - %s - %s" % (datetime.datetime.fromtimestamp(commit.committed_date), commit.author.name, commit.message.partition('\n')[0]))
                    else:
                        repo_data[week]['all'] += int(increase)
                else:
                    if commit.author.name in team:
                        repo_data.update({'%s' % week: {'team': increase,
                                                        'all': increase}})
                        if args.debug:
                            print("size: %s " % (increase))
                            print("\t%s - %s - %s" % (datetime.datetime.fromtimestamp(commit.committed_date), commit.author.name, commit.message.partition('\n')[0]))

                    else:
                        repo_data.update({'%s' % week: {'team': 0,
                                                        'all': increase}})
                pass
        else:
            print('Could not load repository at {}'.format(repo_directory))


if __name__ == "__main__":
    if which("gnuplot") is None:
        print("The gnuplot is not available.\n" +
              "This tool is using gnuplot to create png images from the" +
              "statistics about the local git repositories.\n" +
              "Install it with `sudo zypper install gnuplot` command.")
        sys.exit(0)
    if which("git") is None:
        print("The git is not available.")
        sys.exit(0)
    parser = parse_args()
    args = parser.parse_args(sys.argv[1:])
    if args.debug:
        print('\nargs: ' + str(sys.argv))
    try:
        with open(args.json) as f:
            data = json.load(f)
        if args.debug:
            print("input json " + args.json + ":")
            print(json.dumps(data, sort_keys=True, indent=4))
        try:
            repos = data['repos']
            team = data['team']
            if args.measure == "kudos":
                kudos = data['kudos']
        except KeyError as e:
            print("\nMissing json key: " + str(e))
            exit(1)
    except (IOError, json.JSONDecodeError) as e:
        print(e)
        exit(1)
    repo_template = '{}'
    repo_data = json.loads(repo_template)
    update_repos(repos)
    if args.all:
        plot = plot_template + plot_all_template
    else:
        plot = plot_template
    data_index = 0
    data_table = ""
    ticsline = ""
    separator = ""
    newline = ""
    max_y = 0
    for week in sorted_alphanumerically(repo_data):
        max_y = max(repo_data[week]['team'],
                    repo_data[week]['all'] if args.all else 0,
                    max_y)
        data_table += ("%s%s\t%s\t%s" % (newline,
                       data_index,
                       repo_data[week]['team'],
                       repo_data[week]['all']))
        ticsline += ("%s\"%s\" %s" % (separator, week, data_index))
        data_index += 1
        separator = ","
        newline = "\n"

    plot = re.sub(r"YTICS", "%s" % min((10, 50, 100, 500, 1000, 5000),
                                       key=lambda x: abs(x-int(max_y/20))),
                  plot)
    plot = re.sub(r"X_MAX", "%s" % data_index, plot)
    plot = re.sub(r"DATA", "%s" % data_table, plot)
    plot = re.sub(r"PNG", "%s" % "weekly.png", plot)
    plot = re.sub(r"TICS", "set xtics (%s)" % ticsline, plot)
    plot = re.sub(r"NAME", "%s-%s-weeks" % (os.path.splitext(args.json)[0],
                                            args.weeks), plot)
    if args.measure == "size":
        plot = re.sub(r"UNIT", "lines in commits", plot)
    if args.measure == "commits":
        plot = re.sub(r"UNIT", "commits", plot)
    if args.measure == "kudos":
        plot = re.sub(r"UNIT",
                      "lines in commits for \\\"%s\\\" files" % kudos,
                      plot)
    print(plot)
    gnuplot(plot)
    file = open("%s-%s-weeks.plot" % (os.path.splitext(args.json)[0],
                                      args.weeks), "w")
    file.write(plot)
    file.close()
    with open("%s-%s-weeks.json" % (os.path.splitext(args.json)[0],
                                    args.weeks), 'wt') as json_file:
        json.dump(repo_data, json_file, indent=4)
