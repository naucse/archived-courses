"""
Archive all courses that ended 1 months or more ago
"""

import os
import sys
import json
import pathlib
import datetime
import subprocess

from ruamel.yaml import YAML

MY_URL = 'https://github.com/naucse/archived-courses'
TODAY = datetime.date.today()

PID = os.getpid()

yaml = YAML()

def run(*args, **kwargs):
    kwargs.setdefault('check', True)
    print(args)
    return subprocess.run(args, **kwargs)


def main(path):
    with path.open('rb') as f:
        data = yaml.load(f)
    for key, entry in data.items():
        print(key)
        if entry.get('canonical'):
            print('canonical, skipping')
            continue
        if entry['url'] == MY_URL:
            print('archived, skipping')
            continue
        if '.' in key:
            print('sus, skipping')
            continue

        print(key, entry)
        tmp_index_name = f'.{PID}.tmp.index'
        env = os.environ | {'GIT_INDEX_FILE': tmp_index_name}
        run('git', 'fetch', entry['url'], entry['branch'])
        entry_path = entry.get("path", "")
        treename = f'FETCH_HEAD:{entry_path}'
        try:
            proc = run(
                'git', 'show',
                f"FETCH_HEAD:{os.path.join(entry_path, 'course.json')}",
                stdout=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            print(e)
            continue
        course_data = json.loads(proc.stdout)
        dates = []
        for lesson in course_data['course']['sessions']:
            try:
                date = datetime.date.fromisoformat(lesson['date'])
            except KeyError:
                continue
            dates.append(date)
        print()
        print(key)
        print(course_data['course']['title'])
        print(min(dates), '-', max(dates))
        print()
        days_since = (TODAY - max(dates)).days
        print(f'{days_since} days since end')
        if days_since < 30:
            print('too new, skipping')
            continue
        run(
            'git', 'read-tree', treename,
            env=env,
        )
        run(
            'git', 'checkout-index', '-a', '-f', f'--prefix={key}/',
            env=env,
        )
        #run('git', 'add', key)
        entry.clear()
        entry['url'] = MY_URL
        entry['branch'] = 'main'
        entry['path'] = key
        os.unlink(tmp_index_name)
    with path.open('wb') as f:
        yaml.dump(data, f)



if __name__ == '__main__':
    try:
        [executable, pathname] = sys.argv
    except ValueError:
        exit(f"Usage: {sys.argv[0]} PATH_TO_COURSES_YAML\n" + __doc__)
    if pathname.startswith('-'):
        exit(f"Usage: {sys.argv[0]} PATH_TO_COURSES_YAML\n" + __doc__)
    main(pathlib.Path(pathname))
