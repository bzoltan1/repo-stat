# Repository statistics
A tool to create statistics and a visual report on commits to multiply repositories by group of developers

## Dependencies
The tool is using git and gnuplot. On OpenSUSE Tumbleweed it requires python3-GitPython, git and gnplot packages.

## Howt to use
Create a json file what lists the repositories and the team members.
For example:
    {
        "repos": [ "user/repo",
                   "user_2/repo_2" ],
        "team": [ "username_1",
                  "username_2",
                  "username_3"]
    }

The usernames should be as used in the git commits what is not necessarily the same as the username on the hosting server.

Arguments:
  -h, --help            show this help message and exit
  -d, --debug           debug mode
  -i JSON, --input-json JSON
                        File with repos and team members in json format.
  -w WEEKS, --weeks WEEKS
                        Length of period in weeks
  -a, --all             Show the graph of all contributions


## How it works
The tool clones all the listed repositories from GitHub and lists all the commits. From the commits it filters out the author's name and the date.
If the repositories are already cloned then it simple updates the local repository.
