"""
Copyright 2020 EUROCONTROL
==========================================

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
   disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
   disclaimer in the documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

==========================================

Editorial note: this license is an instance of the BSD license template as provided by the Open Source Initiative:
http://opensource.org/licenses/BSD-3-Clause

Details on EUROCONTROL: http://www.eurocontrol.int
"""

__author__ = "EUROCONTROL (SWIM)"

import json
from collections import defaultdict
from functools import partial

from flask import Blueprint, send_from_directory, request, current_app as app

from aixm import cache
from aixm.graph import get_graph
from aixm.parser import process_aixm
from aixm.stats import get_stats
from aixm.utils import get_samples_filepath

aixm_blueprint = Blueprint('geofencing_viewer',
                           __name__,
                           template_folder='templates',
                           static_folder='static')

########
# STATIC
########


@aixm_blueprint.route("/")
def index():
    return send_from_directory('web_app/templates/', "index.html")


@aixm_blueprint.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('web_app/static/js', path)


@aixm_blueprint.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('web_app/static/css', path)


@aixm_blueprint.route('/img/<path:path>')
def send_img(path):
    return send_from_directory('web_app/static/img', path)


@aixm_blueprint.route('/favicon.ico')
def favicon():
    return send_from_directory('web_app/static/img', 'favicon.png', mimetype='image/png')


@aixm_blueprint.route('/load_aixm', methods=['POST'])
def load_aixm():
    data = request.get_json()

    process_aixm(filepath=data['filepath'], features_config=app.config['FEATURES'])

    stats = get_stats()

    return json.dumps({
        "stats": [
            {
                'name': key,
                'count': value['count'],
                'has_broken_xlinks': value['has_broken_xlinks']
            }
            for key, value in stats.items() if value['count'] > 0
        ]
    })


@aixm_blueprint.route('/graph/<feature_name>', methods=['GET'])
def load_graph(feature_name: str):
    nodes, links = get_graph(feature_name)

    return json.dumps({
        'graph': {
            'nodes': nodes,
            'links': links
        }
    })