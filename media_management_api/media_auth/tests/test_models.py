import unittest

from ..models import Application

CLIENT_SECRET_LENGTH = 40 # sha1 hex digest; should be exactly this long


class TestSignals(unittest.TestCase):
    def test_client_secret_created_post_save(self):
        application = Application(client_id="test_client_secret_created_post_save")
        self.assertFalse(application.client_secret)
        application.save()
        self.assertTrue(application.client_secret)
        self.assertEqual(len(application.client_secret), CLIENT_SECRET_LENGTH)
        application.delete()
