# Copyright (c) 2018, Novo Nordisk Foundation Center for Biosustainability,
# Technical University of Denmark.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configure the gunicorn server."""

import os

_config = os.environ["ENVIRONMENT"]

bind = "0.0.0.0:8000"
worker_class = "aiohttp.worker.GunicornWebWorker"
timeout = 12000
accesslog = "-"


if _config == "production":
    workers = os.cpu_count() * 2 + 1
    loglevel = "INFO"
else:
    workers = 1
    reload = True
    loglevel = "DEBUG"
