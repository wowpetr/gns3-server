# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 GNS3 Technologies Inc.
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

import pytest

from fastapi import FastAPI, status
from httpx import AsyncClient

from tests.utils import asyncio_patch

from gns3server.compute.project import Project

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def vm(app: FastAPI, client: AsyncClient, compute_project: Project, on_gns3vm) -> dict:

    with asyncio_patch("gns3server.compute.builtin.nodes.cloud.Cloud._start_ubridge"):
        response = await client.post(app.url_path_for("create_cloud", project_id=compute_project.id),
                                     json={"name": "Cloud 1"})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


async def test_cloud_create(app: FastAPI, client: AsyncClient, compute_project: Project) -> None:

    with asyncio_patch("gns3server.compute.builtin.nodes.cloud.Cloud._start_ubridge"):
        response = await client.post(app.url_path_for("create_cloud", project_id=compute_project.id),
                                     json={"name": "Cloud 1"})
    assert response.status_code == 201
    assert response.json()["name"] == "Cloud 1"
    assert response.json()["project_id"] == compute_project.id


async def test_get_cloud(app: FastAPI, client: AsyncClient, compute_project: Project, vm: dict) -> None:

    response = await client.get(app.url_path_for("get_cloud", project_id=vm["project_id"], node_id=vm["node_id"]))
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Cloud 1"
    assert response.json()["project_id"] == compute_project.id
    assert response.json()["status"] == "started"


async def test_cloud_nio_create_udp(app: FastAPI, client: AsyncClient, compute_project: Project, vm: dict) -> None:

    params = {"type": "nio_udp",
              "lport": 4242,
              "rport": 4343,
              "rhost": "127.0.0.1"}

    url = app.url_path_for("create_cloud_nio",
                           project_id=vm["project_id"],
                           node_id=vm["node_id"],
                           adapter_number="0",
                           port_number="0")
    response = await client.post(url, json=params)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["type"] == "nio_udp"


async def test_cloud_nio_update_udp(app: FastAPI, client: AsyncClient, compute_project: Project, vm: dict) -> None:

    params = {"type": "nio_udp",
              "lport": 4242,
              "rport": 4343,
              "rhost": "127.0.0.1"}

    url = app.url_path_for("create_cloud_nio",
                           project_id=vm["project_id"],
                           node_id=vm["node_id"],
                           adapter_number="0",
                           port_number="0")
    await client.post(url, json=params)

    params["filters"] = {}
    url = app.url_path_for("create_cloud_nio",
                           project_id=vm["project_id"],
                           node_id=vm["node_id"],
                           adapter_number="0",
                           port_number="0")
    response = await client.put(url, json=params)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["type"] == "nio_udp"


async def test_cloud_delete_nio(app: FastAPI, client: AsyncClient, compute_project: Project, vm: dict) -> None:

    params = {"type": "nio_udp",
              "lport": 4242,
              "rport": 4343,
              "rhost": "127.0.0.1"}

    url = app.url_path_for("create_cloud_nio",
                           project_id=vm["project_id"],
                           node_id=vm["node_id"],
                           adapter_number="0",
                           port_number="0")
    await client.post(url, json=params)

    url = app.url_path_for("delete_cloud_nio",
                           project_id=vm["project_id"],
                           node_id=vm["node_id"],
                           adapter_number="0",
                           port_number="0")
    with asyncio_patch("gns3server.compute.builtin.nodes.cloud.Cloud._start_ubridge"):
        response = await client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT


async def test_cloud_delete(app: FastAPI, client: AsyncClient, compute_project: Project, vm: dict) -> None:

    response = await client.delete(app.url_path_for("delete_cloud", project_id=vm["project_id"], node_id=vm["node_id"]))
    assert response.status_code == status.HTTP_204_NO_CONTENT


async def test_cloud_update(app: FastAPI, client: AsyncClient, vm: dict) -> None:

    response = await client.put(app.url_path_for("update_cloud", project_id=vm["project_id"], node_id=vm["node_id"]),
                                json={"name": "test"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "test"


async def test_cloud_start_capture(app: FastAPI, client: AsyncClient, vm: dict) -> None:

    params = {
        "capture_file_name": "test.pcap",
        "data_link_type": "DLT_EN10MB"
    }

    with asyncio_patch("gns3server.compute.builtin.nodes.cloud.Cloud.start_capture") as mock:
        response = await client.post(app.url_path_for("start_cloud_capture",
                                                      project_id=vm["project_id"],
                                                      node_id=vm["node_id"],
                                                      adapter_number="0",
                                                      port_number="0"),
                                     json=params)
        assert response.status_code == status.HTTP_200_OK
        assert mock.called
        assert "test.pcap" in response.json()["pcap_file_path"]


async def test_cloud_stop_capture(app: FastAPI, client: AsyncClient, vm: dict) -> None:

    with asyncio_patch("gns3server.compute.builtin.nodes.cloud.Cloud.stop_capture") as mock:
        response = await client.post(app.url_path_for("stop_cloud_capture",
                                                      project_id=vm["project_id"],
                                                      node_id=vm["node_id"],
                                                      adapter_number="0",
                                                      port_number="0"))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert mock.called


# @pytest.mark.asyncio
# async def test_cloud_pcap(compute_api, vm, compute_project):
#
#     from itertools import repeat
#     stream = repeat(42, times=10)
#
#     with asyncio_patch("gns3server.compute.builtin.nodes.cloud.Cloud.get_nio"):
#         with asyncio_patch("gns3server.compute.builtin.Builtin.stream_pcap_file", return_value=stream):
#             response = await compute_api.get("/projects/{project_id}/cloud/nodes/{node_id}/adapters/0/ports/0/pcap".format(project_id=compute_project.id, node_id=vm["node_id"]))
#             assert response.status_code == 200
#