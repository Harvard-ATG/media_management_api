import unittest

from media_management_api.media_service.models import UserProfile

from ..models import Application, Token, generate_random_access_token

MIN_TOKEN_KEY_LENGTH = 25 # sha1 hash with token PK, base 64 encoded; should be at least this long
CLIENT_SECRET_LENGTH = 40 # sha1 hex digest; should be exactly this long


class TestTokenGenerator(unittest.TestCase):
    def test_create_nonempty_token(self):
        pk = 1
        token = generate_random_access_token(pk)
        self.assertTrue(token is not None)
        self.assertTrue(token != "")
        self.assertTrue(len(token) > MIN_TOKEN_KEY_LENGTH)

    def test_create_unique_tokens(self):
        tokens = set()
        total_tokens = 100
        for i in range(total_tokens):
            random_token = generate_random_access_token(i)
            tokens.add(random_token)
        self.assertEqual(total_tokens, len(tokens))


class TestSignals(unittest.TestCase):
    def test_client_secret_created_post_save(self):
        application = Application(client_id="test_client_secret_created_post_save")
        self.assertFalse(application.client_secret)
        application.save()
        self.assertTrue(application.client_secret)
        self.assertEqual(len(application.client_secret), CLIENT_SECRET_LENGTH)
        application.delete()

    def test_token_key_created_post_save(self):
        application = Application(client_id="test_token_key_created_post_save", client_secret="secret123")
        application.save()
        user_profile = UserProfile(sis_user_id="testuser1")
        user_profile.save()

        token = Token(application=application, user_profile=user_profile)
        self.assertFalse(token.key)
        token.save()
        self.assertTrue(token.key)
        self.assertTrue(len(token.key) >= MIN_TOKEN_KEY_LENGTH)

        application.delete()
        user_profile.delete()


