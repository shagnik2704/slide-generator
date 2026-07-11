"""Unit coverage for application-issued user identity tokens."""
import unittest

from jose import jwt

from src.api.auth import create_access_token, verify_token
from src.api.config import settings


class UserIdentityTokenTests(unittest.TestCase):
    def test_jwt_subject_is_the_application_user_id(self):
        user_id = "5b1f5555-32ec-4da2-8f5d-c95d20732fd5"
        token = create_access_token(
            subject=user_id,
            email="owner@example.com",
            name="Owner",
        )

        token_data = verify_token(token)

        self.assertIsNotNone(token_data)
        self.assertEqual(token_data.sub, user_id)
        self.assertEqual(token_data.email, "owner@example.com")

    def test_legacy_email_subject_requires_reauthentication(self):
        token = jwt.encode(
            {
                "sub": "owner@example.com",
                "email": "owner@example.com",
                "name": "Owner",
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        self.assertIsNone(verify_token(token))


if __name__ == "__main__":
    unittest.main()
