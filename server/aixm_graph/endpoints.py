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

import logging
import os
from functools import wraps
from typing import Dict

from flask import Blueprint
from flask import request, current_app as app, send_file
from werkzeug.utils import secure_filename

from aixm_graph import cache

_logger = logging.getLogger(__name__)


aixm_blueprint = Blueprint('aixm_graph', __name__)


def handle_response(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        status_code = 200
        result = {}
        try:
            result['data'] = f(*args, **kwargs)
        except Exception as e:
            _logger.exception(str(e))
            result['error'] = str(e)
            status_code = 400

        return result, status_code
    return decorator


@aixm_blueprint.route('/datasets', methods=['GET'])
@handle_response
def get_datasets():
    datasets = cache.get_datasets()

    return [
        {
            "dataset_name": dataset.name,
            "dataset_id": dataset.id
        }
        for dataset in datasets
    ]


@aixm_blueprint.route('/datasets/<dataset_id>/process', methods=['PUT'])
@handle_response
def process_dataset(dataset_id: str):
    """

    :param dataset_id:
    :return:
    """
    dataset = cache.get_dataset_by_id(dataset_id)

    if not dataset.stats:
        dataset.process()

    feature_groups = [
        {
            'name': key,
            'size': value['size'],
            'has_broken_xlinks': value['has_broken_xlinks']
        }
        for key, value in dataset.stats.items() if value['size'] > 0
    ]
    feature_groups.sort(key=lambda item: item.get("name"))

    return {
        "feature_groups": feature_groups
    }


@aixm_blueprint.route('/datasets/<dataset_id>/feature_groups/<feature_group_name>/graph', methods=['GET'])
@handle_response
def get_graph_for_feature_group(dataset_id: str, feature_group_name: str):
    """

    :param dataset_id:
    :param feature_group_name:
    :return:
    """
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', app.config['PAGE_LIMIT']))
    filter_key = request.args.get('key')

    dataset = cache.get_dataset_by_id(dataset_id)

    graph = dataset.get_graph(feature_name=feature_group_name, offset=offset, limit=(limit + offset) - 1, key=filter_key)

    size = sum(1 for _ in dataset.get_features_by_name(name=feature_group_name, field_filter=filter_key))

    return {
        'offset': offset,
        'limit': limit,
        'size': size,
        'graph': graph.to_json(),
        'next_offset': _get_next_offset(offset, limit, size),
        'prev_offset': _get_prev_offset(offset, limit, size),
    }


def _get_next_offset(offset, limit, size):
    """

    :param offset:
    :param limit:
    :param size:
    :return:
    """
    next_offset = offset + limit
    if next_offset >= size or size <= limit :
        return

    return next_offset


def _get_prev_offset(offset, limit, size):
    """

    :param offset:
    :param limit:
    :param size:
    :return:
    """
    pref_offset = offset - limit

    if pref_offset >= 0:
        return pref_offset


@aixm_blueprint.route('/datasets/<dataset_id>/features/<feature_id>/graph', methods=['GET'])
@handle_response
def get_graph_for_feature_id(dataset_id: str, feature_id: str):
    """

    :param dataset_id:
    :param feature_id:
    :return:
    """
    dataset = cache.get_dataset_by_id(dataset_id)
    feature = dataset.get_feature_by_id(feature_id)

    graph = dataset.get_graph_for_feature(feature=feature)

    return {
        'graph': graph.to_json()
    }


@aixm_blueprint.route('/upload', methods=['POST'])
@handle_response
def upload_aixm():
    """

    :return:
    """
    file = _validate_file_form(request.files)

    if cache.get_dataset_by_name(file.filename) is not None:
        raise ValueError('Dataset already exists.')

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    dataset = cache.create_dataset(filepath)

    return {
        'dataset_name': dataset.name,
        'dataset_id': dataset.id
    }


@aixm_blueprint.route('/datasets/<dataset_id>/download', methods=['GET'])
def download(dataset_id: str):
    """

    :param dataset_id:
    :return:
    """
    dataset = cache.get_dataset_by_id(dataset_id)

    skeleton_filepath = dataset.generate_skeleton()

    return send_file(skeleton_filepath, as_attachment=True)


def _validate_file_form(file_form: Dict):
    """

    :param file_form:
    :return:
    """
    if 'file' not in file_form:
        raise ValueError('No file part')

    file = file_form['file']
    if file.filename == '':
        raise ValueError('No selected file')

    if not allowed_file(file.filename):
        raise ValueError('File is not allowed')

    return file


def allowed_file(filename):
    """

    :param filename:
    :return:
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'xml'