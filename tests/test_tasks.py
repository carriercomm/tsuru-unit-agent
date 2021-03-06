# -*- coding: utf-8 -*-

from unittest import TestCase
import mock
import os
import sys

from tsuru_unit_agent.tasks import (
    execute_start_script,
    load_app_yaml,
    load_procfile,
    run_build_hooks,
    run_restart_hooks,
    save_apprc_file,
    parse_apprc_file,
    write_circus_conf,
)


class TestTasks(TestCase):

    @mock.patch("os.environ", {'env': 'var', 'env1': 'var1'})
    @mock.patch("subprocess.Popen")
    def test_execute(self, popen_mock):
        wait_mock = popen_mock.return_value.wait
        wait_mock.return_value = 0
        execute_start_script("my_command", envs={"env": "varrr"})
        self.assertEqual(popen_mock.call_args[0][0], 'my_command')
        self.assertEqual(popen_mock.call_args[1]['shell'], True)
        self.assertEqual(popen_mock.call_args[1]['cwd'], '/')
        self.assertDictEqual(popen_mock.call_args[1]['env'], {'env': 'varrr',
                                                              'env1': 'var1'})
        wait_mock.assert_called_once_with()

    @mock.patch("os.environ", {'myenv': 'var', 'env1': 'var1'})
    @mock.patch("sys.exit")
    @mock.patch("subprocess.Popen")
    def test_execute_failing(self, popen_mock, exit_mock):
        wait_mock = popen_mock.return_value.wait
        wait_mock.return_value = 10
        execute_start_script("my_command", envs={"myenv": "varrr"})
        self.assertEqual(popen_mock.call_args[0][0], 'my_command')
        self.assertEqual(popen_mock.call_args[1]['shell'], True)
        self.assertEqual(popen_mock.call_args[1]['cwd'], '/')
        self.assertDictEqual(popen_mock.call_args[1]['env'], {'myenv': 'varrr',
                                                              'env1': 'var1'})
        wait_mock.assert_called_once_with()
        exit_mock.assert_called_once_with(10)

    def test_save_apprc_file(self):
        environs = {"DATABASE_HOST": "localhost", "DATABASE_USER": "root"}
        with mock.patch("io.open", mock.mock_open()) as m:
            save_apprc_file(environs)
            m.assert_called_once_with("/home/application/apprc", "w")
            write_mock = m().write
            self.assertRegexpMatches(write_mock.mock_calls[0][1][0],
                                     '# generated by tsuru at .*\n')
            write_mock.assert_any_call('export DATABASE_HOST=\'localhost\'\n')
            write_mock.assert_any_call('export DATABASE_USER=\'root\'\n')
            self.assertEqual(len(write_mock.mock_calls), 3)

    def test_parse_apprc_file(self):
        path = os.path.join(os.path.dirname(__file__), "fixtures", "apprc")
        envs = parse_apprc_file(path)
        expected = {
            "A": "B",
            "C": "C D",
            "b": "888",
            "B": "9\"1",
            "D": "X=y",
            "F": "a(a",
            "MY_awesome_BIG_name": "something",
        }
        for k, v in envs.items():
            if k not in expected:
                envs.pop(k)
        self.assertDictEqual(envs, expected)

    def test_save_parse_apprc_escaping(self):
        expected = {
            "A": "B",
            "C": "C D",
            "b": "888",
            "B": "9\"1",
            "D": "X=y",
            "F": "a(a) + (",
            "MY_awesome_BIG_name": "some'thin'g'",
            "JSON": '[{"a": "b", "c": {"d": "f"}}]',
            "SLASHED": "a\\a escaped \\\" some \\\"",
            "EXEC": "a: `echo hey` b: $(echo again)",
            "MULTILINE": "my\nmulti\"line\", with ' quotes ' yay'\nvariable'\n'",
        }
        path = os.path.join(os.path.dirname(__file__), "fixtures", "written_apprc")
        try:
            save_apprc_file(expected, file_path=path)
            envs = parse_apprc_file(path)
            for k, v in envs.items():
                if k not in expected:
                    envs.pop(k)
            self.assertDictEqual(envs, expected)
        finally:
            os.remove(path)


class RunHooksTest(TestCase):

    @mock.patch("os.environ", {'env': 'var', 'env1': 'var1'})
    @mock.patch("subprocess.Popen")
    def test_execute_commands(self, popen_call):
        wait_mock = popen_call.return_value.wait
        wait_mock.return_value = 0
        data = {"hooks": {"build": ["ble"]}}
        run_build_hooks(data, envs={'env': 'varrr'})
        self.assertEqual(popen_call.call_args[0][0], 'ble')
        self.assertEqual(popen_call.call_args[1]['shell'], True)
        self.assertEqual(popen_call.call_args[1]['cwd'], '/')
        self.assertDictEqual(popen_call.call_args[1]['env'], {'env': 'varrr',
                                                              'env1': 'var1'})
        wait_mock.assert_called_once_with()

    @mock.patch("os.environ", {})
    @mock.patch("os.path.exists")
    @mock.patch("subprocess.Popen")
    def test_execute_commands_default_cwd_exists(self, popen_call, exists_mock):
        wait_mock = popen_call.return_value.wait
        wait_mock.return_value = 0
        exists_mock.return_value = True
        data = {"hooks": {"build": ["ble"]}}
        run_build_hooks(data)
        self.assertEqual(popen_call.call_args[0][0], 'ble')
        self.assertEqual(popen_call.call_args[1]['shell'], True)
        self.assertEqual(popen_call.call_args[1]['cwd'], '/home/application/current')
        self.assertDictEqual(popen_call.call_args[1]['env'], {})
        wait_mock.assert_called_once_with()
        exists_mock.assert_called_once_with("/home/application/current")

    @mock.patch("os.environ", {})
    @mock.patch("sys.exit")
    @mock.patch("subprocess.Popen")
    def test_execute_failing_commands(self, popen_call, exit_mock):
        wait_mock = popen_call.return_value.wait
        wait_mock.return_value = 5
        data = {"hooks": {"build": ["ble"]}}
        run_build_hooks(data)
        self.assertEqual(popen_call.call_args[0][0], 'ble')
        self.assertEqual(popen_call.call_args[1]['shell'], True)
        self.assertEqual(popen_call.call_args[1]['cwd'], '/')
        self.assertDictEqual(popen_call.call_args[1]['env'], {})
        wait_mock.assert_called_once_with()
        exit_mock.assert_called_once_with(5)

    @mock.patch("subprocess.Popen")
    def test_execute_commands_hooks_empty(self, subprocess_call):
        data = {}
        run_build_hooks(data)
        subprocess_call.assert_not_called()
        data = {"hooks": None}
        run_build_hooks(data)
        subprocess_call.assert_not_called()
        data = {"hooks": {"build": None}}
        run_build_hooks(data)
        subprocess_call.assert_not_called()
        data = {"hooks": {"build": []}}
        run_build_hooks(data)
        subprocess_call.assert_not_called()


class RunRestartHooksTest(TestCase):

    @mock.patch("tsuru_unit_agent.tasks.Stream")
    @mock.patch("os.environ", {'env': 'var', 'env1': 'var1'})
    @mock.patch("subprocess.Popen")
    def test_run_restart_hooks(self, popen_call, Stream):
        popen_call.return_value.stdout.readline.return_value = ''
        popen_call.return_value.stderr.readline.return_value = ''
        wait_mock = popen_call.return_value.wait
        wait_mock.return_value = 0
        data = {"hooks": {"restart": {
            "before": ["b1"],
            "before-each": ["b2"],
            "after": ["a1"],
            "after-each": ["a2"],
        }}}
        run_restart_hooks('before', data, envs={'env': 'varrr'})
        self.assertEqual(popen_call.call_count, 2)
        self.assertEqual(popen_call.call_args_list[0][0][0], 'b2')
        self.assertEqual(popen_call.call_args_list[0][1]['shell'], True)
        self.assertEqual(popen_call.call_args_list[0][1]['cwd'], '/')
        self.assertDictEqual(popen_call.call_args_list[0][1]['env'], {'env': 'varrr',
                                                                      'env1': 'var1'})
        self.assertEqual(popen_call.call_args_list[1][0][0], 'b1')
        wait_mock.assert_any_call()
        run_restart_hooks('after', data)
        self.assertEqual(popen_call.call_count, 4)
        self.assertEqual(popen_call.call_args_list[3][0][0], 'a1')
        self.assertEqual(popen_call.call_args_list[2][0][0], 'a2')

    @mock.patch("tsuru_unit_agent.tasks.Stream")
    @mock.patch("os.environ", {'env': 'var', 'env1': 'var1'})
    @mock.patch("subprocess.Popen")
    def test_run_restart_hooks_calls_stream(self, popen_call, stream_mock):
        out1 = ['stdout_out1', '']
        out2 = ['stderr_out1', '']
        popen_call.return_value.stdout.readline.side_effect = lambda: out1.pop(0)
        popen_call.return_value.stderr.readline.side_effect = lambda: out2.pop(0)
        wait_mock = popen_call.return_value.wait
        wait_mock.return_value = 0
        data = {"hooks": {"restart": {
            "before": ["b1"],
        }}}
        run_restart_hooks('before', data, envs={'env': 'varrr'})
        self.assertDictEqual(os.environ, {'env': 'var', 'env1': 'var1'})
        self.assertEqual(popen_call.call_count, 1)
        self.assertEqual(popen_call.call_args_list[0][0][0], 'b1')
        self.assertEqual(popen_call.call_args_list[0][1]['shell'], True)
        self.assertEqual(popen_call.call_args_list[0][1]['cwd'], '/')
        self.assertDictEqual(popen_call.call_args_list[0][1]['env'], {'env': 'varrr',
                                                                      'env1': 'var1'})
        wait_mock.assert_called_once_with()
        self.assertEqual(stream_mock.call_count, 2)
        self.assertEqual(stream_mock.call_args_list[0][1]['echo_output'], sys.stdout)
        self.assertEqual(stream_mock.call_args_list[0][1]['default_stream_name'], 'stdout')
        self.assertEqual(stream_mock.call_args_list[0][1]['watcher_name'], 'unit-agent')
        self.assertEqual(stream_mock.call_args_list[0][1]['envs'], {'env': 'varrr',
                                                                    'env1': 'var1'})
        self.assertEqual(stream_mock.call_args_list[1][1]['echo_output'], sys.stderr)
        self.assertEqual(stream_mock.call_args_list[1][1]['default_stream_name'], 'stderr')
        self.assertEqual(stream_mock.call_args_list[1][1]['watcher_name'], 'unit-agent')
        self.assertEqual(stream_mock.call_args_list[1][1]['envs'], {'env': 'varrr',
                                                                    'env1': 'var1'})
        write_mock = stream_mock.return_value.write
        write_mock.assert_any_call('stdout_out1')
        write_mock.assert_any_call('stderr_out1')
        stream_mock.return_value.flush.assert_any_call()
        stream_mock.return_value.close.assert_any_call()


class LoadAppYamlTest(TestCase):

    def setUp(self):
        self.working_dir = os.path.dirname(__file__)
        self.data = '''
hooks:
  build:
    - {0}_1
    - {0}_2'''

    def test_load_app_yaml(self):
        filenames = ["tsuru.yaml", "tsuru.yml", "app.yaml", "app.yml"]
        for name in filenames:
            with open(os.path.join(self.working_dir, name), "w") as f:
                f.write(self.data.format(name))

        for name in filenames:
            data = load_app_yaml(self.working_dir)
            self.assertEqual(data, {"hooks": {"build": ["{}_1".format(name),
                                                        "{}_2".format(name)]}})
            os.remove(os.path.join(self.working_dir, name))

    def test_load_without_app_files(self):
        data = load_app_yaml(self.working_dir)
        self.assertDictEqual(data, {})

    def test_load_with_empty_yaml(self):
        with open(os.path.join(self.working_dir, "tsuru.yaml"), "w") as f:
            f.write("")
        data = load_app_yaml(self.working_dir)
        self.assertDictEqual(data, {})
        os.remove(os.path.join(self.working_dir, "tsuru.yaml"))

    def test_load_yaml_encoding(self):
        data = load_app_yaml(os.path.join(self.working_dir, "fixtures/iso88591"))
        self.assertDictEqual(data, {"key": "x"})
        data = load_app_yaml(os.path.join(self.working_dir, "fixtures/utf-8"))
        self.assertDictEqual(data, {"key": u"áéíãôüx"})

    def test_load_broken_yaml(self):
        broken_yaml = '''
hooks:
\tbuild:
\t\t- foo_1
\t\t- bar_2
        '''
        with open(os.path.join(self.working_dir, "tsuru.yaml"), "w") as f:
            f.write(broken_yaml)
        data = load_app_yaml(self.working_dir)
        self.assertDictEqual(data, {})
        os.remove(os.path.join(self.working_dir, "tsuru.yaml"))


class LoadProcfileTest(TestCase):

    def setUp(self):
        self.working_dir = os.path.join(os.path.dirname(__file__),
                                        "fixtures")

    def test_load_procfile(self):
        content = load_procfile(self.working_dir)
        expected = r"""web: python run_my_app.py -p $PORT -l $POORT
worker: python run_my_worker.py""" + "\n"
        self.assertEqual(expected, content)


class WriteCircusConfTest(TestCase):

    def setUp(self):
        self.procfile_path = os.path.join(os.path.dirname(__file__), "fixtures",
                                          "Procfile")
        self.conf_path = os.path.join(os.path.dirname(__file__), "fixtures",
                                      "circus.ini")
        self.original_conf = open(self.conf_path).read()
        os.environ["PORT"] = "9090"
        os.environ["POORT"] = "8989"

    def tearDown(self):
        open(self.conf_path, "w").write(self.original_conf)
        del os.environ["PORT"]
        del os.environ["POORT"]

    def test_write_file(self):
        expected_file = open(self.conf_path).read()
        expected_file += u"""
[watcher:web]
cmd = python run_my_app.py -p 8888 -l 8989
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = web
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = web

[watcher:worker]
cmd = python run_my_worker.py
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = worker
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = worker
"""
        write_circus_conf(procfile_path=self.procfile_path, conf_path=self.conf_path,
                          envs={"PORT": "8888"})
        got_file = open(self.conf_path).read()
        self.assertEqual(expected_file, got_file)

    def test_write_file_multiple_times(self):
        expected_file = open(self.conf_path).read()
        expected_file += u"""
[watcher:web]
cmd = python run_my_app.py -p 8888 -l 8989
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = web
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = web

[watcher:worker]
cmd = python run_my_worker.py
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = worker
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = worker
"""
        write_circus_conf(procfile_path=self.procfile_path, conf_path=self.conf_path,
                          envs={"PORT": "8888"})
        write_circus_conf(procfile_path=self.procfile_path, conf_path=self.conf_path,
                          envs={"PORT": "8888"})
        write_circus_conf(procfile_path=self.procfile_path, conf_path=self.conf_path,
                          envs={"PORT": "8888"})
        got_file = open(self.conf_path).read()
        self.assertEqual(expected_file, got_file)

    def test_write_file_no_watchers(self):
        expected_file = open(self.conf_path).read()
        write_circus_conf(procfile_path=self.procfile_path + ".empty",
                          conf_path=self.conf_path)
        got_file = open(self.conf_path).read()
        self.assertEqual(expected_file, got_file)

    def test_write_new_file(self):
        expected_file = u"""
[watcher:web]
cmd = python run_my_app.py -p 8888 -l 8989
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = web
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = web

[watcher:worker]
cmd = python run_my_worker.py
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = worker
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = worker
"""
        conf_path = self.conf_path + ".new"
        write_circus_conf(procfile_path=self.procfile_path,
                          conf_path=conf_path, envs={"PORT": "8888"})
        self.addCleanup(os.remove, conf_path)
        got_file = open(conf_path).read()
        self.assertEqual(expected_file, got_file)

    def test_write_new_file_env_working_dir(self):
        os.environ["APP_WORKING_DIR"] = "/tmp/app"

        def clean():
            del os.environ["APP_WORKING_DIR"]
        self.addCleanup(clean)
        expected_file = u"""
[watcher:web]
cmd = python run_my_app.py -p 8888 -l 8989
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /tmp/app
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = web
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = web

[watcher:worker]
cmd = python run_my_worker.py
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /tmp/app
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = worker
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = worker
"""
        conf_path = self.conf_path + ".new"
        write_circus_conf(procfile_path=self.procfile_path,
                          conf_path=conf_path, envs={"PORT": "8888"})
        self.addCleanup(os.remove, conf_path)
        got_file = open(conf_path).read()
        self.assertEqual(expected_file, got_file)

    def test_write_new_file_env_procfile_path(self):
        os.environ["PROCFILE_PATH"] = self.procfile_path + "2"

        def clean():
            del os.environ["PROCFILE_PATH"]
        expected_file = u"""
[watcher:web]
cmd = python run_their_app.py -p 8888
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = web
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = web

[watcher:worker]
cmd = python run_their_worker.py
copy_env = True
uid = ubuntu
gid = ubuntu
working_dir = /home/application/current
stdout_stream.class = tsuru.stream.Stream
stdout_stream.watcher_name = worker
stderr_stream.class = tsuru.stream.Stream
stderr_stream.watcher_name = worker
"""
        conf_path = self.conf_path + ".new"
        write_circus_conf(conf_path=conf_path, envs={"PORT": "8888"})
        self.addCleanup(os.remove, conf_path)
        got_file = open(conf_path).read()
        self.assertEqual(expected_file, got_file)
