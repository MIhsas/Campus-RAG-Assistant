import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from captcha_collect import import_record
import captcha_collect
from captcha_trial import eligible_urls


class ImportTests(unittest.TestCase):
    def test_failure_report_uses_latest_download_status(self):
        old=json.dumps({'http_status':200,'reason':'captcha_required','source_page':'source'})
        row=captcha_collect.unresolved_record('xxgc.sicau.edu.cn','url','captcha_required',old,
                                             {'http_status':404,'reason':'http_404'})
        self.assertEqual(row['http_status'],404)
        self.assertEqual(row['reason'],'http_404')
        self.assertEqual(row['source_page'],'source')

    def test_saved_scope_limits_restart_and_rejects_expansion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'collection_scope.json').write_text(json.dumps({'allowed_hosts':['xxgc.sicau.edu.cn','xsc.sicau.edu.cn']}))
            self.assertEqual(captcha_collect.load_hosts(root),['xsc.sicau.edu.cn','xxgc.sicau.edu.cn'])
            with self.assertRaises(ValueError):captcha_collect.load_hosts(root,['dky.sicau.edu.cn'])

    def test_remaining_work_excludes_other_sites_and_exhausted_failures(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE urls(url TEXT,host TEXT,status TEXT);')
        db.executemany('INSERT INTO urls VALUES(?,?,?)',[
            ('a','xxgc.sicau.edu.cn','captcha_required'),('b','dky.sicau.edu.cn','captcha_required'),
            ('c','xxgc.sicau.edu.cn','captcha_required'),('d','xxgc.sicau.edu.cn','captcha_required')])
        records=[dict(url='a',success=False),dict(url='c',success=False),dict(url='c',success=False)]
        self.assertEqual(captcha_collect.remaining_urls(db,records,['xxgc.sicau.edu.cn'],2),['d','a'])
        db.close()

    def test_retry_limit_keeps_successes_and_failed_attempt_history(self):
        records=[dict(url='a',success=False),dict(url='b',success=False),dict(url='b',success=True),
                 dict(url='c',success=False),dict(url='c',success=False)]
        self.assertEqual(eligible_urls(['a','b','c','d'],records,2),['d','a'])

    def test_import_deduplicates_and_resumes_without_losing_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            db=sqlite3.connect(root/'crawl.sqlite')
            db.executescript('CREATE TABLE urls(url TEXT PRIMARY KEY,site TEXT,status TEXT,result TEXT); CREATE TABLE objects(sha256 TEXT PRIMARY KEY,path TEXT,bytes INTEGER,name TEXT);')
            for url in ('a','b'):
                db.execute('INSERT INTO urls VALUES(?,?,?,?)',(url,'example.sicau.edu.cn','captcha_required','{}'))
            db.commit();db.close()
            data=b'%PDF-1.4\npublic document';(root/'sample.pdf').write_bytes(data)
            record=dict(url='a',success=True,path='sample.pdf',sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),name='sample.pdf',finished_at='now')
            self.assertTrue(import_record(root,record))
            self.assertFalse(import_record(root,record))
            self.assertTrue(import_record(root,dict(record,url='b')))
            self.assertFalse(import_record(root,dict(record,success=False)))
            db=sqlite3.connect(root/'crawl.sqlite')
            self.assertEqual(db.execute('SELECT count(*) FROM objects').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM urls WHERE status='file'").fetchone()[0],2)
            db.close()
            self.assertEqual(len((root/'manifest.jsonl').read_text().splitlines()),2)

    def test_invalid_content_cannot_enter_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=b'<html>captcha</html>';(root/'bad.pdf').write_bytes(data)
            record=dict(url='a',success=True,path='bad.pdf',sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),name='bad.pdf')
            with self.assertRaises(ValueError):import_record(root,record)
