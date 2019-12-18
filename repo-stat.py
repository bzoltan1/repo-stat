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
from git import Repo
from datetime import date
from os.path import isfile


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
        "repos": [ "user/repo", "user_2/repo_2" ],
        "team": [ "github_username_1", "github_username_2", "github_username_3"]
    }

    '''
    parser = argparse.ArgumentParser(prog='repo-stat.py',
                                     description='Generates stats of git repositories based on json input.',
                                     epilog=example_json,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        dest='debug', help='debug mode')
    parser.add_argument("-i", "--input-json", dest="json",
                        type=check_valid_input_json, default=None,
                        help="File with repos and team members in json format.")
#    parser.add_argument("-w", "--weeks", dest="weeks", type=int, default=None,
#                            help="Length of period in weeks")
#    parser.add_argument("-p", "--periods", dest="periods", type=int, default=None,
#                            help="Number of periods")
    # print help & exit if no argument given
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()
    return parser


def update_repos(repos):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    for r in repos:
        m = re.match(r"(.*)(\/+)(.*)", r)
        repo_directory=r
        if m:
            repo_directory=m.group(3)
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
                week="%s - %s" % (d.year, d.isocalendar()[1])
                if week in repo_data:
                    if commit.author.name in team:
                        repo_data[week]['team'] += 1
                        repo_data[week]['all'] += 1
                    else:
                        repo_data[week]['all'] += 1
                else:
                     repo_data.update({'%s' % week: 1})
                     repo_data.update({'%s' % week: {'team': 1, 'all':1}})

                pass
        else:
            print('Could not load repository at {} :('.format(repo_path))


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
    print(json.dumps(repo_data, indent=4, sort_keys=True))
