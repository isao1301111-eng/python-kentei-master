# -*- coding: utf-8 -*-
"""index.html に入っている問題と早見表のコードを、実際に Python で実行して確かめる。

使い方: python verify_questions.py
すべて合格なら最後に「不合格 0件」と表示される。
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 60
EXPECT_COUNTS = {1: 2, 2: 2, 3: 12, 4: 18, 5: 14, 6: 4, 7: 2, 8: 8,
                 9: 4, 10: 8, 11: 2, 12: 2, 14: 2}


def load_block(html, block_id):
    m = re.search(r'<script type="application/json" id="%s">(.*?)</script>' % block_id,
                  html, re.S)
    if not m:
        raise SystemExit('データが見つからない: ' + block_id)
    return json.loads(m.group(1))


def run(code):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'main.py')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
        r = subprocess.run([sys.executable, 'main.py'], cwd=d, env=env,
                           capture_output=True, encoding='utf-8', timeout=TIMEOUT)
    err = None
    if r.returncode != 0:
        lines = [x for x in r.stderr.strip().splitlines() if x.strip()]
        err = lines[-1].split(':')[0].strip() if lines else 'unknown'
    return r.stdout, err, r.stderr


def norm(text):
    return '\n'.join(line.rstrip() for line in text.strip().splitlines())


def check_question(q):
    """問題が正しければ空リスト、誤りがあれば理由のリストを返す。"""
    problems = []
    if len(q['choices']) != 4 or len(q['why']) != 4:
        problems.append('選択肢または解説が4つではない')
    if len(set(q['choices'])) != 4:
        problems.append('同じ選択肢がある')
    answer = q['choices'][q['a']]

    if q.get('check') == 'output':
        out, err, stderr = run(q['code'])
        if 'err' in q:
            if err != q['err']:
                problems.append('想定 %s / 実際 %s / 出力 %r' % (q['err'], err, out))
            if not answer.startswith(q['err']):
                problems.append('正解の選択肢が例外名と合わない')
            others = [c for i, c in enumerate(q['choices'])
                      if i != q['a'] and c.startswith(q['err'] + ' ')]
            if others:
                problems.append('同じ例外の選択肢が他にもある')
        else:
            if err:
                problems.append('想定外の例外 %s: %s' % (err, stderr[-200:]))
            expected = q['expect'] if 'expect' in q else answer
            if norm(out) != norm(expected):
                problems.append('想定 %r / 実際 %r' % (expected, out))
            if 'expect' not in q:
                for i, c in enumerate(q['choices']):
                    if i != q['a'] and norm(c) == norm(out):
                        problems.append('不正解の選択肢が実際の出力と同じ: %r' % c)
    elif 'verify' in q:
        out, err, stderr = run(q['verify'])
        if err:
            problems.append('検証コードが失敗 %s: %s' % (err, stderr[-300:]))
    return problems


def main():
    with open(os.path.join(HERE, 'index.html'), encoding='utf-8') as f:
        html = f.read()
    questions = load_block(html, 'qdata')
    cheats = load_block(html, 'cheatdata')

    failed = 0
    kinds = {'output': 0, 'verify': 0, 'none': []}
    counts = {}
    ids = set()
    for q in questions:
        counts[q['ch']] = counts.get(q['ch'], 0) + 1
        if q['id'] in ids:
            print('NG', q['id'], 'IDが重複')
            failed += 1
        ids.add(q['id'])
        if q.get('check') == 'output':
            kinds['output'] += 1
        elif 'verify' in q:
            kinds['verify'] += 1
        else:
            kinds['none'].append(q['id'])
        for p in check_question(q):
            print('NG', q['id'], p)
            failed += 1

    if counts != EXPECT_COUNTS:
        print('NG 章ごとの問題数が想定と違う', counts)
        failed += 1

    for i, c in enumerate(cheats):
        out, err, stderr = run(c['code'])
        if err:
            print('NG 早見表', c['t'], err, stderr[-200:])
            failed += 1
        elif norm(out) != norm(c.get('out', out)):
            print('NG 早見表の出力が違う', c['t'], repr(out), repr(c.get('out')))
            failed += 1

    print('Python', sys.version.split()[0])
    print('問題 %d問（出力・例外を実行で確認 %d／検証コードで確認 %d／実行では確かめられない知識問題 %d: %s）' % (
        len(questions), kinds['output'], kinds['verify'], len(kinds['none']),
        ', '.join(kinds['none'])))
    print('早見表 %d件' % len(cheats))
    print('不合格 %d件' % failed)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
