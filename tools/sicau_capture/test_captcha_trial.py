import unittest
from captcha_trial import valid_answer, validate_download


class CaptchaTrialTests(unittest.TestCase):
    def test_uncertain_or_malformed_reading_is_not_submitted(self):
        for value in ('123','12O4','12345','12 34','１２３４',''):
            self.assertFalse(valid_answer(value))
        self.assertTrue(valid_answer('1536'))

    def test_http_200_challenge_is_not_a_download(self):
        self.assertFalse(validate_download(200,b'<html><title>captcha</title></html>','text/html','attachment.pdf')[0])

    def test_blocked_response_is_not_saved_as_success(self):
        self.assertFalse(validate_download(403,b'%PDF-1.5 fake','application/pdf','a.pdf')[0])

    def test_damaged_zip_is_not_accepted(self):
        self.assertFalse(validate_download(200,b'PK\x03\x04broken','application/octet-stream','a.xlsx')[0])
