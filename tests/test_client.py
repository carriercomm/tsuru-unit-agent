import unittest
import mock
from socket import gethostname
import os

from tsuru_unit_agent.client import Client


class TestClient(unittest.TestCase):
    def test_client(self):
        client = Client("http://localhost", "token")
        self.assertEqual(client.url, "http://localhost")
        self.assertEqual(client.token, "token")

    @mock.patch("requests.post")
    def test_register_unit(self, post_mock):
        response = post_mock.return_value
        response.status_code = 200
        response.json.return_value = [
            {'name': 'var1', 'value': 'var2'},
            {'name': 'var3', 'value': 'var4'},
        ]
        client = Client("http://localhost", "token")
        envs = client.register_unit(app="myapp")
        self.assertListEqual(envs, response.json.return_value)
        post_mock.assert_called_with(
            "{}/apps/myapp/units/register".format(client.url),
            data={"hostname": gethostname()},
            headers={"Authorization": "bearer token"})
        self.assertEqual(os.environ['var1'], 'var2')
        self.assertEqual(os.environ['var3'], 'var4')
        self.assertEqual(os.environ['port'], '8888')
        self.assertEqual(os.environ['PORT'], '8888')

    @mock.patch("requests.get")
    @mock.patch("requests.post")
    def test_register_unit_failing_register(self, post_mock, get_mock):
        response = post_mock.return_value
        response.status_code = 404
        response.json.return_value = None
        get_response = get_mock.return_value
        get_response.status_code = 200
        get_response.json.return_value = [
            {'name': 'var1', 'value': 'var2'},
            {'name': 'var3', 'value': 'var4'},
        ]
        client = Client("http://localhost", "token")
        envs = client.register_unit(app="myapp")
        self.assertListEqual(envs, get_response.json.return_value)
        post_mock.assert_called_once_with(
            "{}/apps/myapp/units/register".format(client.url),
            data={"hostname": gethostname()},
            headers={"Authorization": "bearer token"})
        get_mock.assert_called_once_with(
            "{}/apps/myapp/env".format(client.url),
            headers={"Authorization": "bearer token"})

    @mock.patch("requests.post")
    def test_post_app_yaml(self, post_mock):
        response = post_mock.return_value
        response.status_code = 200
        client = Client("http://localhost", "token")
        client.post_app_yaml(app="myapp", data=[{"x": "y"}])
        post_mock.assert_called_with(
            "{}/apps/myapp/customdata".format(client.url),
            data='[{"x": "y"}]',
            headers={
                "Authorization": "bearer token",
                "Content-Type": "application/json",
            })
