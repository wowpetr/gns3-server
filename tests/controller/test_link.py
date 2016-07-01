#!/usr/bin/env python
#
# Copyright (C) 2016 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import pytest
import asyncio
from unittest.mock import MagicMock


from gns3server.controller.link import Link
from gns3server.controller.node import Node
from gns3server.controller.compute import Compute
from gns3server.controller.project import Project

from tests.utils import AsyncioBytesIO, AsyncioMagicMock


@pytest.fixture
def project(controller):
    return Project(controller=controller)


@pytest.fixture
def compute():
    return Compute("example.com", controller=MagicMock())


@pytest.fixture
def link(async_run, project, compute):
    node1 = Node(project, compute, "node1")
    node2 = Node(project, compute, "node2")

    link = Link(project)
    async_run(link.add_node(node1, 0, 4))
    async_run(link.add_node(node2, 1, 3))
    return link


def test_add_node(async_run, project, compute):
    node1 = Node(project, compute, "node1")

    link = Link(project)
    link._project.controller.notification.emit = MagicMock()
    project.dump = AsyncioMagicMock()
    async_run(link.add_node(node1, 0, 4))
    assert link._nodes == [
        {
            "node": node1,
            "adapter_number": 0,
            "port_number": 4,
            'label': {
                'y': -10,
                'text': '0/4',
                'x': -10,
                'rotation': 0,
                'style': 'font-size: 10; font-style: Verdana'
            }
        }
    ]
    assert project.dump.called
    assert not link._project.controller.notification.emit.called

    # We call link.created only when both side are created
    node2 = Node(project, compute, "node2")
    async_run(link.add_node(node2, 0, 4))

    link._project.controller.notification.emit.assert_called_with("link.created", link.__json__())


def test_update_node(async_run, project, compute):
    node1 = Node(project, compute, "node1")

    link = Link(project)
    async_run(link.add_node(node1, 0, 4))
    label = {
        'y': -42,
        'text': '0/4',
        'x': -10,
        'rotation': 0,
        'style': 'font-size: 10; font-style: Verdana'
    }
    project.dump = AsyncioMagicMock()
    link._project.controller.notification.emit = MagicMock()
    async_run(link.update_node(node1, 0, 4, label=label))
    assert link._nodes[0]["label"]["y"] == -42
    assert project.dump.called
    link._project.controller.notification.emit.assert_called_with("link.updated", link.__json__())


def test_json(async_run, project, compute):
    node1 = Node(project, compute, "node1")
    node2 = Node(project, compute, "node2")

    link = Link(project)
    async_run(link.add_node(node1, 0, 4))
    async_run(link.add_node(node2, 1, 3))
    assert link.__json__() == {
        "link_id": link.id,
        "project_id": project.id,
        "nodes": [
            {
                "node_id": node1.id,
                "adapter_number": 0,
                "port_number": 4,
                'label': {
                    'y': -10,
                    'text': '0/4',
                    'x': -10,
                    'rotation': 0,
                    'style': 'font-size: 10; font-style: Verdana'
                }
            },
            {
                "node_id": node2.id,
                "adapter_number": 1,
                "port_number": 3,
                'label': {
                    'y': -10,
                    'text': '1/3',
                    'x': -10,
                    'rotation': 0,
                    'style': 'font-size: 10; font-style: Verdana'
                }
            }
        ],
        "capturing": False,
        "capture_file_name": None,
        "capture_file_path": None
    }
    assert link.__json__(topology_dump=True) == {
        "link_id": link.id,
        "nodes": [
            {
                "node_id": node1.id,
                "adapter_number": 0,
                "port_number": 4,
                'label': {
                    'y': -10,
                    'text': '0/4',
                    'x': -10,
                    'rotation': 0,
                    'style': 'font-size: 10; font-style: Verdana'
                }
            },
            {
                "node_id": node2.id,
                "adapter_number": 1,
                "port_number": 3,
                'label': {
                    'y': -10,
                    'text': '1/3',
                    'x': -10,
                    'rotation': 0,
                    'style': 'font-size: 10; font-style: Verdana'
                }
            }
        ]
    }


def test_start_streaming_pcap(link, async_run, tmpdir, project):
    @asyncio.coroutine
    def fake_reader():
        output = AsyncioBytesIO()
        yield from output.write(b"hello")
        output.seek(0)
        return output

    link._capture_file_name = "test.pcap"
    link._capturing = True
    link.read_pcap_from_source = fake_reader
    async_run(link._start_streaming_pcap())
    with open(os.path.join(project.captures_directory, "test.pcap"), "rb") as f:
        c = f.read()
        assert c == b"hello"


def test_default_capture_file_name(project, compute, async_run):
    node1 = Node(project, compute, "Hello@")
    node2 = Node(project, compute, "w0.rld")

    link = Link(project)
    async_run(link.add_node(node1, 0, 4))
    async_run(link.add_node(node2, 1, 3))
    assert link.default_capture_file_name() == "Hello_0-4_to_w0rld_1-3.pcap"


def test_start_capture(link, async_run, tmpdir, project, controller):
    @asyncio.coroutine
    def fake_reader():
        return AsyncioBytesIO()

    link.read_pcap_from_source = fake_reader
    controller._notification = MagicMock()
    async_run(link.start_capture(capture_file_name="test.pcap"))
    assert link._capturing
    assert link._capture_file_name == "test.pcap"
    controller._notification.emit.assert_called_with("link.updated", link.__json__())


def test_stop_capture(link, async_run, tmpdir, project, controller):
    link._capturing = True
    controller._notification = MagicMock()
    async_run(link.stop_capture())
    assert link._capturing is False
    controller._notification.emit.assert_called_with("link.updated", link.__json__())